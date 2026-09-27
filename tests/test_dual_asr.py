"""Synthetic contracts, not recognition accuracy benchmarks."""
from pathlib import Path
import sys
from types import SimpleNamespace

import numpy as np
import pytest
import soundfile as sf

from podcut import dual_asr as dual
from podcut.core import fingerprint, read, write
from podcut.cli import parser


def test_georgian_comparison_does_not_confuse_agreement_with_accuracy():
    same = dual.compare_texts('გამარჯობა, მსოფლიო!', 'გამარჯობა მსოფლიო')
    assert same['normalized_match'] and same['word_disagreement'] == 0
    change = dual.compare_texts('ერთი ორი სამი', 'ერთი ოთხი სამი')
    assert change['word_edits'] == 1
    assert change['word_disagreement'] == pytest.approx(1/3)
    assert change['differences'] == [{'kind': 'replace', 'whisper': 'ორი', 'meta': 'ოთხი'}]
    assert dual.compare_texts('', '')['review_required']
    assert dual.compare_texts('hello', '')['word_disagreement'] == 1
    assert dual.compare_texts('ერთი 20', 'ერთი 30')['review_required']


def test_ctc_words_preserve_unicode_and_do_not_claim_long_silence_as_speech():
    tokens = list('მე ვარ')
    words = dual.token_words(tokens, [.1, .2, .25, 2., 2.1, 2.2], 3)
    assert [w['word'] for w in words] == ['მე', 'ვარ']
    assert words[0]['end'] == pytest.approx(.22)
    assert words[1]['start'] == 2
    with pytest.raises(ValueError, match='inconsistent'):
        dual.token_words(['a'], [], 3)
    with pytest.raises(ValueError, match='unordered'):
        dual.token_words(['a', 'b'], [2, 1], 3)
    with pytest.raises(ValueError, match='invalid'):
        dual.token_words(['a'], [float('nan')], 3)


def test_overlapping_context_is_owned_once_on_reference_clock():
    words = [{'word': 'before', 'start': 0, 'end': .4},
             {'word': 'kept', 'start': 1, 'end': 2},
             {'word': 'next', 'start': 20.9, 'end': 21.5}]
    segment = dual.make_segment(words, 19, 20, 40)[0]
    assert segment['text'] == 'kept'
    assert segment['words'][0]['start'] == 20
    assert dual.windows(10, 51) == [(10, 30), (30, 50), (50, 51)]


def test_zero_duration_words_are_preserved_with_a_timing_warning():
    words = [{'word': 'ერთი', 'start': 1, 'end': 1}, {'word': ' ორი', 'start': 2, 'end': 3}]
    row = dual.make_segment(words, 0, 0, 20)[0]
    assert row['text'] == 'ერთი ორი'
    assert len(row['words']) == 2 and row['timing_issue']
    row = dual.make_segment(words[:1], 0, 0, 20)[0]
    assert row['text'] == 'ერთი' and row['end'] > row['start']
    assert row['words'] == []


@pytest.mark.parametrize('start,duration', [(-1, 2), (0, 0), (0, float('inf')), (float('nan'), 3), (9, 1)])
def test_invalid_sample_intervals(start, duration):
    with pytest.raises(ValueError):
        dual.interval(start, duration, 8)


@pytest.fixture
def setup(tmp_path, monkeypatch):
    audio = tmp_path / 'synthetic.wav'
    sf.write(audio, np.zeros(16000 * 45, dtype=np.float32), 16000)
    models = {name: {'name': name + '-synthetic', 'timing': 'test timing'} for name in ['whisper', 'meta']}
    loads, calls = [], []

    def open_engine(name, config):
        loads.append(name)
        return object()

    def decode(name, engine, samples, language):
        calls.append((name, len(samples), language))
        text = 'სინთეზური' if name == 'whisper' else 'სატესტო'
        return {'text': text, 'words': [{'word': text, 'start': 1.2, 'end': 1.8}]}

    monkeypatch.setattr(dual, 'open_engine', open_engine)
    monkeypatch.setattr(dual, 'decode', decode)
    return audio, models, loads, calls


def test_two_engines_use_identical_samples_sequentially_and_resume_without_loading(setup, tmp_path):
    audio, models, loads, calls = setup
    out = tmp_path / 'run'
    args = (audio, 10, 10, 55, out, models, 'ka', 'audio-v1', 80, 'reference recording seconds')
    report = read(dual.run_engines(*args))
    assert loads == ['whisper', 'meta']
    assert [c[0] for c in calls] == ['whisper'] * 3 + ['meta'] * 3
    assert [c[1] for c in calls[:3]] == [c[1] for c in calls[3:]]
    assert not report['complete']
    assert report['automatic_winner'] is None
    assert report['summary']['review_windows'] == 3
    for name in models:
        data = read(out / name / 'reference.json')
        assert data['range'] == [10, 55]
        assert data['segments'][0]['start'] == pytest.approx(11.2)
        for ext in ['txt', 'srt', 'vtt', 'json']:
            assert (out / name / ('reference.' + ext)).exists()
    dual.run_engines(*args)
    assert loads == ['whisper', 'meta'] and len(calls) == 6


def test_failed_second_engine_is_not_success_or_silent_fallback_and_can_resume(setup, tmp_path, monkeypatch):
    audio, models, loads, calls = setup
    good_decode = dual.decode

    def fail_meta(name, *args):
        if name == 'meta':
            raise RuntimeError('synthetic failure')
        return good_decode(name, *args)

    monkeypatch.setattr(dual, 'decode', fail_meta)
    out = tmp_path / 'run'
    args = (audio, 0, 0, 45, out, models, 'ka', 'v1', 45, 'reference recording seconds')
    with pytest.raises(RuntimeError, match='synthetic failure'):
        dual.run_engines(*args)
    assert read(out / 'run_status.json')['status'] == 'failed'
    assert (out / 'whisper' / 'reference.json').exists()
    assert not (out / 'comparison.json').exists()
    monkeypatch.setattr(dual, 'decode', good_decode)
    assert read(dual.run_engines(*args))['complete']
    assert loads == ['whisper', 'meta', 'meta']


def test_different_clock_cannot_be_compared(setup, tmp_path):
    audio, models, _, _ = setup
    out = tmp_path / 'run'
    dual.run_engines(audio, 0, 0, 45, out, models, 'ka', 'v1', 45, 'reference recording seconds')
    transcripts = {n: read(out / n / 'reference.json') for n in models}
    transcripts['meta']['audio_signature'] = 'v2'
    with pytest.raises(ValueError, match='different audio'):
        dual.build_comparison(out, transcripts, [(0, 20)])


def test_html_escapes_transcript_markup_and_preserves_playback_offset(setup, tmp_path, monkeypatch):
    audio, models, _, _ = setup
    monkeypatch.setattr(dual, 'decode', lambda *a: {'text': '<script>alert(1)</script>',
                       'words': [{'word': '<script>alert(1)</script>', 'start': .2, 'end': .6}]})
    out = tmp_path / 'run'
    dual.run_engines(audio, 50, 50, 70, out, models, 'ka', 'v1', 90, 'source file seconds')
    page = (out / 'comparison.html').read_text(encoding='utf-8')
    assert '<script>alert(1)</script>' not in page
    assert '&lt;script&gt;' in page
    assert 'data-seek="0.000"' in page


def test_project_provenance_changes_when_audio_mapping_or_model_changes(setup, tmp_path, monkeypatch):
    audio, models, _, _ = setup
    project = tmp_path / 'project.json'
    p = {'schema_version': 1, 'sources': [{'id': 'a', 'path': str(audio), 'fingerprint': fingerprint(audio),
                                         'kind': 'audio', 'use': True, 'duration': 45}],
         'reference_id': 'a', 'sync': {'a': {'offset': 0, 'rate': 1, 'verified': True}},
         'audio': {'tracks': [{'source_id': 'a'}]}, 'decisions': {'language': 'ka'}}
    write(project, p)
    monkeypatch.setattr(dual, 'resolve_models', lambda *a: models)
    monkeypatch.setattr(dual, 'asr_audio', lambda *a: audio)
    first = dual.compare_project(project)
    assert read(tmp_path / 'transcript_latest.json')['complete']
    p['sources'][0]['channel'] = 0
    write(project, p)
    second = dual.compare_project(project)
    assert first != second
    models['meta']['name'] += '-revision2'
    third = dual.compare_project(project)
    assert third != second
    assert Path(read(tmp_path / 'transcript_latest.json')['path']).parent.name == 'whisper'
    assert not (tmp_path / 'worker.lock').exists()


def test_default_cli_runs_both_with_explicit_whisper_escape_hatch():
    assert parser().parse_args(['transcribe', 'episode.json']).engine == 'both'
    assert parser().parse_args(['transcribe', 'episode.json', '--engine', 'whisper']).engine == 'whisper'
    assert parser().parse_args(['compare-audio', 'audio.wav', '--language', 'ka']).seconds == 40


def test_pinned_meta_assets_reject_corruption_and_do_not_download_without_flag(tmp_path, monkeypatch):
    from podcut import asr_models
    model = tmp_path / 'model'
    model.mkdir()
    (model / 'model.bin').write_bytes(b'synthetic')
    bad = tmp_path / 'bad.onnx'
    bad.write_bytes(b'corrupt')
    calls = []

    def fetch(repo, name, **kwargs):
        calls.append(kwargs)
        return str(bad)

    monkeypatch.setitem(sys.modules, 'sherpa_onnx', SimpleNamespace(
        OfflineRecognizer=SimpleNamespace(from_omnilingual_asr_ctc=True)))
    monkeypatch.setitem(sys.modules, 'faster_whisper.utils', SimpleNamespace(download_model=lambda *a, **kw: str(model)))
    monkeypatch.setitem(sys.modules, 'huggingface_hub', SimpleNamespace(hf_hub_download=fetch))
    with pytest.raises(ValueError, match='checksum mismatch'):
        asr_models.resolve_models(str(model))
    assert calls[0]['local_files_only'] is True
    assert calls[0]['revision'] == asr_models.OMNI_REVISION
