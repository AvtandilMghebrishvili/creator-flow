from fractions import Fraction
from pathlib import Path
import numpy as np
import pytest
from podcut.core import frames,seconds,identity
from podcut.sync import match,fit,SR
from podcut.transcript import retime_segments,stamp
from podcut.plan import validate_plan,camera_at

def test_fractional_rate_roundtrip():
    fps='30000/1001'
    for n in [0,1,1000,180000]:assert frames(seconds(n,fps),fps)==n
    assert stamp(3661.234)=='01:01:01.234'

def test_sync_recovers_an_unknown_offset():
    rng=np.random.default_rng(17)
    t=np.arange(SR*18)/SR
    noise=rng.normal(size=len(t))*.03
    envelope=.3+.7*np.sin(t*3.2)**2
    ref=(noise+np.sin(t*400*np.pi)*.02)*envelope
    start=3.714
    template=ref[round(start*SR):round((start+5)*SR)]*.4
    found=match(ref,template)
    assert abs(found['reference']-start)<.002
    # STFT hops need not align at a sub-hop source offset; waveform refinement should.
    assert found['spectral_score']>.6
    assert abs(found['wave_correlation'])>.99

def test_drift_fit_and_outlier_flag():
    points=[{'reference':x,'source':-19.4+1.00008*x} for x in [100,1800,5500]]
    model=fit(points)
    assert abs(model['offset']+19.4)<1e-8
    assert abs(model['rate']-1.00008)<1e-9
    assert not model['needs_attention']
    points[1]['source']+=1
    assert fit(points)['needs_attention']

def test_transcript_retimes_removed_and_reordered_passages():
    segments=[{'start':10,'end':14,'text':'one two','words':[{'start':10,'end':11,'word':'one '},{'start':13,'end':14,'word':'two'}]},
              {'start':30,'end':31,'text':'last','words':[{'start':30,'end':31,'word':'last'}]}]
    keeps=[{'reference_start':30,'reference_end':32,'start_frame':0,'end_frame':50},
           {'reference_start':12,'reference_end':15,'start_frame':50,'end_frame':125}]
    out=retime_segments(segments,keeps,'25')
    assert [s['text'] for s in out]==['last','two']
    assert [s['start'] for s in out]==[0,3]
    assert out[1]['words'][0]['end']==4

def project_fixture():
    p={'sources':[{'id':'g','role':'guest','use':True,'kind':'camera','duration':40},
                  {'id':'w','role':'wide','use':True,'kind':'camera','duration':80},
                  {'id':'a','role':'mix','use':True,'kind':'audio','duration':80}],
       'reference_id':'a','timeline':{'fps':'25'},'sync':{s:{'offset':0.,'rate':1.,'verified':True} for s in ['g','w','a']},
       'audio':{'tracks':[{'source_id':'a','speaker':'mix'}]},'color':{'approved':'original'},'bounds':[0,70]}
    return p

def test_camera_tail_falls_back_to_wide():
    p=project_fixture()
    assert camera_at(p,'guest',10)['id']=='g'
    assert camera_at(p,'guest',39.97)['id']=='g'
    assert camera_at(p,'guest',40)['id']=='w'
    assert camera_at(p,'guest',65)['id']=='w'
    with pytest.raises(ValueError):camera_at(p,'guest',90)

def test_plan_rejects_black_gaps_and_stale_data():
    p=project_fixture()
    plan={'project_signature':identity(p),'total_frames':250,'shots':[{'camera_id':'g','reference_start':0,'reference_end':10,'start_frame':0,'end_frame':250}],
          'segments':[{'reference_start':0,'reference_end':10,'start_frame':0,'end_frame':250}]}
    assert validate_plan(p,plan)['shots'][0]['max_sync_error_ms']==0
    plan['shots'][0]['start_frame']=1
    with pytest.raises(ValueError,match='gap'):validate_plan(p,plan)
    plan['shots'][0]['start_frame']=0;p['sync']['g']['offset']=2
    with pytest.raises(ValueError,match='stale'):validate_plan(p,plan)
