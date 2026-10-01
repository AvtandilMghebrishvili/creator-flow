import json
from pathlib import Path
import shutil
import numpy as np
import soundfile as sf
import pytest
from podcut.core import init,load,write,read,ffmpeg,questions,identity,digest
from podcut.color import make_cube,read_cube,apply_cube,previews,approve
from podcut.plan import build
from podcut.audio import prepare
from podcut.export import xml,render
from podcut.transcript import save_formats,asr_signature,retime

def test_cube_identity(tmp_path):
    path=tmp_path/'test.cube';make_cube(path,'natural',size=9)
    rng=np.random.default_rng(4);x=rng.random((30,3))
    assert np.max(abs(apply_cube(x,read_cube(path))-x))<1e-6

def test_intake_single_camera_mixed_audio_is_ambiguous():
    p={'sources':[{'id':'c','kind':'camera','role':'wide','use':True},{'id':'c2','kind':'camera','role':'wide','use':True}], 'decisions':{'mapping_confirmed':True,'language':'en','color_requested':False,'delivery':'premiere','thumbnail_requested':False},
       'reference_id':'a','audio':{'tracks':[{'speaker':'mix'}]},'bounds':[0,10],'layout':{},'speaker_examples':[]}
    assert any('left/right' in q for q in questions(p))
    p['layout']={'confirmed':True};p['speaker_examples']=[{'speaker':'guest','time':2},{'speaker':'host','time':5}]
    assert not questions(p)

@pytest.mark.skipif(not shutil.which('ffmpeg') or not shutil.which('ffprobe'),reason='FFmpeg integration prerequisites absent')
def test_real_media_pipeline_unicode_folder(tmp_path):
    folder=tmp_path/'ეპიზოდი space';folder.mkdir()
    sr=48000;n=sr*14;t=np.arange(n)/sr;rng=np.random.default_rng(9)
    # A speech-like broadband signal, never a real person's recording.
    x=(.1*np.sin(2*np.pi*211*t)+.06*np.sin(2*np.pi*417*t)+rng.normal(0,.012,n))*(.35+.65*np.sin(t*2)**2)
    sf.write(folder/'microphone.wav',x,sr,subtype='PCM_24')
    y=.12*np.sin(2*np.pi*337*t)*(.4+.6*np.cos(t*1.3)**2)+rng.normal(0,.008,n)
    sf.write(folder/'host.wav',y,sr,subtype='PCM_24')
    ffmpeg(['-f','lavfi','-i','testsrc2=size=320x180:rate=30','-i',str(folder/'microphone.wav'),'-t','14','-c:v','libx264','-threads','2','-preset','ultrafast','-c:a','aac','-y',str(folder/'camera.mov')])
    config=init(folder);p,root=load(config)
    assert p['decisions']['thumbnail_requested'] is None
    cam=next(s for s in p['sources'] if s['kind']=='camera')
    mic=next(s for s in p['sources'] if Path(s['path']).name=='microphone.wav')
    host=next(s for s in p['sources'] if Path(s['path']).name=='host.wav')
    for s in p['sources']:s['use']=True
    cam.update(role='wide',color_space='rec709',review_times=[2]);mic['role']='guest';host['role']='host'
    p['reference_id']=mic['id'];p['audio']['tracks']=[{'source_id':mic['id'],'speaker':'guest'},{'source_id':host['id'],'speaker':'host'}]
    p['sync']={s['id']:{'offset':0.,'rate':1.,'verified':True,'note':'Synthetic same-clock test'} for s in p['sources']}
    p['bounds']=[1,10];p['timeline']={'fps':'25','width':320,'height':180}
    p['decisions'].update(mapping_confirmed=True,language='en',color_requested=True,delivery='premiere')
    write(config,p)
    looks=previews(config);assert len(looks['looks'])==3 and Path(looks['samples'][0]).exists()
    approve(config,'natural')
    saved,_=load(config);lut_fingerprints=saved['color']['lut_fingerprints']
    assert previews(config)==looks
    assert load(config)[0]['color']['lut_fingerprints']==lut_fingerprints
    plan_path=build(config);plan=read(plan_path);plan['approved']=True;write(plan_path,plan)
    stems=prepare(config);assert stems['frames']==9*48000 and stems['validated']
    assert len(stems['tracks'])==2
    guest_audio,_=sf.read(stems['tracks'][0]['path']);host_audio,_=sf.read(stems['tracks'][1]['path'])
    assert abs(np.corrcoef(guest_audio,host_audio)[0,1])<.2
    p,_=load(config)
    transcript=root/'transcripts'/'verified_fixture'
    metadata={'clock':'reference recording seconds','machine_draft':True,'audio_signature':asr_signature(p),'range':[0,14]}
    save_formats(transcript,[{'start':2,'end':3,'text':'synthetic example','words':[{'start':2,'end':3,'word':'synthetic example'}]}],metadata)
    final_text=retime(config,transcript.with_suffix('.json'))
    assert read(final_text)['segments'][0]['start']==1
    assert all(final_text.with_suffix(ext).exists() for ext in ['.txt','.srt','.vtt'])
    short=read(transcript.with_suffix('.json'));short['range']=[0,3];write(transcript.with_suffix('.json'),short)
    with pytest.raises(ValueError,match='does not cover'):retime(config,transcript.with_suffix('.json'))
    exchange=xml(config)
    import xml.etree.ElementTree as E
    tree=E.parse(exchange)
    assert len(tree.findall('.//sequence/media/audio/track'))==2
    assert not tree.findall('.//sequence/media/video/track/clipitem/file/media/audio')
    assert tree.findtext('.//sequence/media/video/track/clipitem/file/rate/timebase')=='30'
    assert tree.findtext('.//sequence/rate/timebase')=='25'
    with pytest.raises(ValueError,match='not requested'):render(config)
    p,_=load(config);p['decisions']['delivery']='render';write(config,p)
    video=render(config);assert video.exists()
    report=read(video.parent/'validation.json');assert report['decoded'] and report['frames']==225
    assert all(abs(c.get('lag_ms',0))<5 for c in report['encoded_audio']['timing_checks'])
    # Guard against rerunning into an already-delivered file.
    with pytest.raises(ValueError,match='already exists'):render(config)
    p,_=load(config);next(s for s in p['sources'] if s['kind']=='camera')['color_correction']={'exposure':.3};write(config,p)
    with pytest.raises(ValueError,match='stale'):approve(config,'warm')


def test_thumbnail_offer_resumes_without_repeating_answer():
    p = {'sources': [], 'decisions': {'mapping_confirmed': True, 'language': 'en',
         'color_requested': False, 'delivery': 'premiere'}, 'reference_id': 'audio', 'bounds': [0, 10]}
    initial = questions(p)
    assert len(initial) == 1  # Older manifests also receive the optional offer.
    for answer in (True, False):
        p['decisions']['thumbnail_requested'] = answer
        assert questions(p) == []
    p['decisions']['thumbnail_requested'] = None
    assert questions(p) == initial
