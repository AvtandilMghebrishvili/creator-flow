import contextlib
from pathlib import Path
import numpy as np
import soundfile as sf
from .core import load,read,write,source,extract_audio,digest,worker,seconds,state
from .sync import require_sync
from .plan import validate_plan

def stamp(t, comma=False):
    n=max(0,round(float(t)*1000));h,n=divmod(n,3600000);m,n=divmod(n,60000);s,ms=divmod(n,1000)
    return f"{h:02}:{m:02}:{s:02}{',' if comma else '.'}{ms:03}"

def save_formats(base, segments, metadata):
    base=Path(base);base.parent.mkdir(parents=True,exist_ok=True)
    write(base.with_suffix('.json'),dict(metadata,segments=segments))
    txt=[];srt=[];vtt=['WEBVTT\n']
    for i,s in enumerate(segments,1):
        text=s['text'].strip();speaker=s.get('speaker')
        if speaker:text=f"[{speaker}] {text}"
        txt.append(f"[{stamp(s['start'])} --> {stamp(s['end'])}] {text}")
        srt.append(f"{i}\n{stamp(s['start'],True)} --> {stamp(s['end'],True)}\n{text}\n")
        vtt.append(f"{stamp(s['start'])} --> {stamp(s['end'])}\n{text}\n")
    base.with_suffix('.txt').write_text('\n'.join(txt)+'\n',encoding='utf-8')
    base.with_suffix('.srt').write_text('\n'.join(srt),encoding='utf-8')
    base.with_suffix('.vtt').write_text('\n'.join(vtt),encoding='utf-8')

def asr_signature(p):
    tracks=p['audio']['tracks'] or [{'source_id':p['reference_id']}]
    ids=list(dict.fromkeys(t['source_id'] for t in tracks))
    return digest([p['reference_id'], source(p,p['reference_id'])['fingerprint'], [(source(p,i)['fingerprint'],p['sync'][i],source(p,i).get('channel'),source(p,i).get('audio_stream',0)) for i in ids]])

def asr_audio(p,root):
    tracks=p['audio']['tracks'] or [{'source_id':p['reference_id']}]
    ids=list(dict.fromkeys(t['source_id'] for t in tracks))
    require_sync(p,ids)
    signature=asr_signature(p)
    dest=root/'transcripts'/f'asr_{signature[:12]}.wav';dest.parent.mkdir(parents=True,exist_ok=True)
    if dest.exists():return dest
    paths=[]
    for ident in ids:
        path=dest.parent/f'{signature[:12]}_{ident}.wav'
        if not path.exists():extract_audio(source(p,ident),path,16000)
        paths.append(path)
    n=round(source(p,p['reference_id'])['duration']*16000)
    temp=dest.with_name(dest.stem+'.partial.wav')
    with contextlib.ExitStack() as stack:
        files=[stack.enter_context(sf.SoundFile(x)) for x in paths]
        output=stack.enter_context(sf.SoundFile(temp,'w',samplerate=16000,channels=1,subtype='PCM_16'))
        for pos in range(0,n,16000*30):
            count=min(16000*30,n-pos);clock=(np.arange(count)+pos)/16000;mix=np.zeros(count)
            for ident,f in zip(ids,files):
                m=p['sync'][ident];idx=(m['offset']+m['rate']*clock)*16000
                lo=max(0,int(np.floor(idx[0])));hi=min(len(f),int(np.ceil(idx[-1]))+2)
                if hi<=lo:continue
                f.seek(lo);x=f.read(hi-lo,dtype='float32');mix+=np.interp(idx,np.arange(lo,hi),x,left=0,right=0)
            mix/=len(files)
            peak=np.max(abs(mix));mix*=min(5.,.9/max(peak,1e-9))
            output.write(mix)
    temp.replace(dest)
    return dest

def transcribe(project, model='small', language=None, start=0., duration=None, allow_download=False, device='cpu'):
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        raise ValueError('Install the optional transcription dependency: python -m pip install -e ".[transcribe]"')
    p,root=load(project)
    language=language or p['decisions'].get('language')
    if not language:raise ValueError('Specify the spoken language; test a representative sample before a long transcription.')
    with worker(root):
        audio=asr_audio(p,root)
        info=sf.info(audio);end=min(info.duration,start+duration if duration is not None else info.duration)
        if not 0<=start<end:raise ValueError('Invalid transcription interval')
        signature=digest([str(audio),model,language,start,end,device,'asr-v1'])
        out=root/'transcripts'/signature[:12];out.mkdir(parents=True,exist_ok=True)
        engine=WhisperModel(model,device=device,compute_type='int8' if device=='cpu' else 'float16',cpu_threads=2,num_workers=1,local_files_only=not allow_download)
        receipts=[]
        for st in np.arange(start,end,60.):
            en=min(end,st+60);lo=max(start,st-2);hi=min(end,en+2)
            receipt=out/f'chunk_{st:010.3f}.json'
            if not receipt.exists():
                x,_=sf.read(audio,start=round(lo*16000),stop=round(hi*16000),dtype='float32')
                segments,_=engine.transcribe(x,language=language,beam_size=5,word_timestamps=True,condition_on_previous_text=False,vad_filter=True)
                rows=[]
                for segment in segments:
                    words=[{'start':w.start+lo,'end':w.end+lo,'word':w.word,'confidence':w.probability} for w in (segment.words or []) if st<=(w.start+w.end)/2+lo<en]
                    if words:rows.append({'start':words[0]['start'],'end':words[-1]['end'],'text':''.join(w['word'] for w in words).strip(),'words':words,'speaker':None})
                write(receipt,rows)
            receipts.extend(read(receipt))
            save_formats(out/'reference',receipts,{'clock':'reference recording seconds','language':language,'model':model,'machine_draft':True,'complete':bool(start==0 and en>=info.duration-.001),'range':[start,float(en)],'audio_signature':asr_signature(p)})
            print(f'Transcript {en-start:.0f}/{end-start:.0f}s',flush=True)
        write(root/'transcript_latest.json',{'path':str(out/'reference.json'),'complete':start==0 and end>=info.duration-.001,'signature':signature})
        state(root,'transcript_review','Timestamped JSON/TXT/SRT/VTT saved on the reference clock. Review names, speaker identity and greeting/farewell. Machine timing is not a caption authority.')
    return out/'reference.json'

def retime_segments(segments, kept, fps):
    output=[]
    for keep in kept:
        a,b=keep['reference_start'],keep['reference_end'];shift=seconds(keep['start_frame'],fps)-a
        for s in segments:
            if s['end']<=a or s['start']>=b:continue
            words=[w for w in s.get('words',[]) if a<=(w['start']+w['end'])/2<b]
            if s.get('words') and not words:continue
            start=max(a,words[0]['start'] if words else s['start'])
            end=min(b,words[-1]['end'] if words else s['end'])
            if end<=start:continue
            output.append({'start':start+shift,'end':end+shift,'text':''.join(w['word'] for w in words).strip() if words else s['text'],
                           'speaker':s.get('speaker'),'reference_start':start,'reference_end':end,
                           'words':[dict(w,start=max(a,w['start'])+shift,end=min(b,w['end'])+shift) for w in words],
                           'boundary_review_required':not bool(words) and (s['start']<a or s['end']>b)})
    return output

def retime(project,transcript=None):
    p,root=load(project);plan=validate_plan(p,read(root/'edit_plan.json'))
    path=Path(transcript) if transcript else Path(read(root/'transcript_latest.json')['path'])
    data=read(path)
    if data.get('audio_signature') != asr_signature(p):
        raise ValueError('Transcript is stale or lacks reference-clock provenance. Re-transcribe or explicitly verify/import its clock metadata.')
    a,b=data.get('range',[0,0])
    if any(s['reference_start'] < a-.001 or s['reference_end'] > b+.001 for s in plan['segments']):
        raise ValueError('Transcript does not cover the kept episode. A short ASR sample is not a full transcript.')
    rows=retime_segments(data['segments'],plan['segments'],plan['fps'])
    base=root/'transcripts'/('final_'+digest([plan,data])[:12])/'episode'
    save_formats(base,rows,{'clock':'final timeline seconds','machine_draft':data.get('machine_draft',True),'source_transcript':str(path),'plan_signature':digest(plan),'complete':True})
    return base.with_suffix('.json')
