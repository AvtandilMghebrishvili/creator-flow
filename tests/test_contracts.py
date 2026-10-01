from pathlib import Path
from types import SimpleNamespace
import sys
import numpy as np
import soundfile as sf
import pytest
import yaml

from podcut.core import rate, require_mapping, fingerprint, write, read, identity
from podcut.plan import validate_plan,build
from podcut.sync import fit
from podcut.transcript import transcribe


def test_skill_metadata_and_links():
    root = Path(__file__).resolve().parents[1]
    for folder in ['.agents', '.claude']:
        skill = root / folder / 'skills' / 'creator-flow' / 'SKILL.md'
        metadata = yaml.safe_load(skill.read_text(encoding='utf-8').split('---', 2)[1])
        assert metadata['name'] == 'creator-flow'
        assert len(metadata['description']) < 1024
        assert (skill.parent / '../../../START_HERE.md').resolve().is_file()


@pytest.mark.parametrize('value', ['0/0', 'no-rate', '-25', '0'])
def test_unknown_rate_cannot_silently_reinterpret_media(value):
    with pytest.raises(ValueError, match='Invalid frame rate'):
        rate(value)


def test_split_recorder_channels_are_valid_but_duplicated_mix_is_not(tmp_path):
    recording = str(tmp_path / 'recorder.wav')
    audio = dict(kind='audio', use=True, path=recording, audio_channels=2, audio_stream=0,
                 probe={'streams': [{'codec_type': 'audio', 'channels': 2}]})
    p = {'decisions': {'mapping_confirmed': True}, 'reference_id': 'g',
         'sources': [dict(id='c', kind='camera', role='wide', use=True, audio_channels=0),
                     dict(audio, id='g', role='guest', channel=0), dict(audio, id='h', role='host', channel=1)],
         'audio': {'tracks': [{'source_id': 'g', 'speaker': 'guest'}, {'source_id': 'h', 'speaker': 'host'}]}}
    require_mapping(p)
    p['sources'][2]['channel'] = 2
    with pytest.raises(ValueError, match='Invalid recorder channel'):
        require_mapping(p)
    p['sources'][2]['channel'] = 0
    with pytest.raises(ValueError, match='same recording/channel'):
        require_mapping(p)


def test_video_cannot_drift_onto_different_content_than_audio():
    p = {'timeline': {'fps': '25'}, 'sources': [{'id': 'c', 'duration': 100}],
         'sync': {'c': {'offset': 0, 'rate': 1}}, 'audio': {'tracks': []}}
    plan = {'project_signature': identity(p), 'total_frames': 250,
            'segments': [{'reference_start': 10, 'reference_end': 20, 'start_frame': 0, 'end_frame': 250}],
            'shots': [{'camera_id': 'c', 'reference_start': 11, 'reference_end': 21, 'start_frame': 0, 'end_frame': 250}]}
    with pytest.raises(ValueError, match='reference clocks disagree'):
        validate_plan(p, plan)


def test_clock_anchors_must_be_finite_and_forward():
    with pytest.raises(ValueError, match='finite'):
        fit([{'reference': 0, 'source': 0}, {'reference': 10, 'source': float('nan')}])
    with pytest.raises(ValueError, match='same direction'):
        fit([{'reference': 0, 'source': 10}, {'reference': 10, 'source': 0}])


def test_sequential_files_are_one_angle_without_a_false_gap(tmp_path):
    entries=[]
    for ident,kind,duration in [('c1','camera',10),('c2','camera',10),('a','audio',20)]:
        path=tmp_path/(ident+'.synthetic');path.write_text('fixture',encoding='utf-8')
        entries.append(dict(id=ident,kind=kind,role='wide' if kind=='camera' else 'mix',use=True,
                            duration=duration,path=str(path),fingerprint=fingerprint(path),audio_channels=1))
    p={'schema_version':1,'sources':entries,'reference_id':'a','decisions':{'mapping_confirmed':True},
       'timeline':{'fps':'25'},'audio':{'tracks':[{'source_id':'a','speaker':'mix'}]},
       'bounds':[0,20], 'sync':{ident:{'offset':offset,'rate':1,'verified':True} for ident,offset in [('c1',0),('c2',-10),('a',0)]}}
    project=tmp_path/'project.json';write(project,p)
    plan=read(build(project))
    assert plan['total_frames']==500
    assert [s['camera_id'] for s in plan['shots']]==['c1','c2']
    assert [s['source_in_frame'] for s in plan['shots']]==[0,0]
    assert plan['shots'][0]['end_frame']==plan['shots'][1]['start_frame']==250


def test_asr_adapter_records_full_vs_sample_and_resumes_without_model_download(tmp_path, monkeypatch):
    # Tests orchestration/provenance only. This deliberately makes no ASR accuracy claim.
    import podcut.transcript as transcript_module
    wav = tmp_path / 'reference.wav'
    sf.write(wav, np.sin(np.arange(16000 * 8) * .02) * .1, 16000)
    config = tmp_path / 'project.json'
    p = {'schema_version': 1, 'sources': [{'id': 'a', 'path': str(wav), 'fingerprint': fingerprint(wav),
                                          'kind': 'audio', 'use': True, 'duration': 8}],
         'reference_id': 'a', 'sync': {'a': {'offset': 0, 'rate': 1, 'verified': True}},
         'audio': {'tracks': [{'source_id': 'a'}]}, 'decisions': {'language': 'en'}}
    write(config, p)
    calls = []

    class FakeWhisper:
        def __init__(self, model, **kwargs):
            assert kwargs['local_files_only'] is True
            assert kwargs['cpu_threads'] == 2

        def transcribe(self, x, **kwargs):
            calls.append(len(x))
            word = SimpleNamespace(start=.2, end=.8, word=' synthetic', probability=.9)
            return [SimpleNamespace(words=[word])], None

    monkeypatch.setitem(sys.modules, 'faster_whisper', SimpleNamespace(WhisperModel=FakeWhisper))
    monkeypatch.setattr(transcript_module, 'asr_audio', lambda project, root: wav)
    sample = transcribe(config, start=1, duration=2)
    assert not read(sample)['complete']
    assert not read(tmp_path / 'transcript_latest.json')['complete']
    full = transcribe(config)
    assert read(full)['complete']
    assert read(full)['range'] == [0, 8]
    assert read(tmp_path / 'transcript_latest.json')['complete']
    assert read(full)['audio_signature']
    transcribe(config)
    assert len(calls) == 2  # Existing chunk was reused rather than retranscribed.
