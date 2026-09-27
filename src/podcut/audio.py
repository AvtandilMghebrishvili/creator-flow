"""Keep identified microphone tracks separate, on the final edit's exact clock."""
import re
from pathlib import Path
import numpy as np
import soundfile as sf
from scipy.ndimage import minimum_filter1d
from .core import load, read, write, ffmpeg, source, digest, worker, seconds, state, process, binary, fingerprint
from .plan import validate_plan

SR = 48000
BLOCK = SR*20

def measure(paths, log):
    args = [binary("ffmpeg"),"-hide_banner","-nostats","-nostdin","-threads","2"]
    for p in paths:
        args += ["-i",str(p)]
    graph = "".join(f"[{i}:a]" for i in range(len(paths)))
    graph += f"amix=inputs={len(paths)}:normalize=0,pan=stereo|c0=c0|c1=c0,ebur128=peak=true[m]"
    result = process([*args,"-filter_complex_threads","1","-filter_complex",graph,"-map","[m]","-f","null","-"])
    Path(log).write_bytes(result.stderr)
    summary = result.stderr.decode(errors="replace").rsplit("Summary:",1)[-1]
    return {"integrated_lufs":float(re.search(r"I:\s*([-\d.]+) LUFS",summary).group(1)),
            "true_peak_db":float(re.search(r"Peak:\s*([-\d.inf]+) dBFS",summary).group(1))}

def clean_source(s, dest):
    args=["-i",s["path"],"-map",f"0:a:{s.get('audio_stream',0)}","-vn"]
    filters=[]
    if s.get("channel") is not None:
        filters.append(f"pan=mono|c0=c{int(s['channel'])}")
    filters += ["highpass=f=70","acompressor=threshold=0.125:ratio=2:attack=15:release=180:makeup=1"]
    ffmpeg([*args,"-af",",".join(filters),"-ac","1","-ar",str(SR),"-c:a","pcm_s24le","-y",str(dest)])

def align_stem(p, plan, track, clean, dest):
    model=p["sync"][track["source_id"]]
    gain=10**(float(track.get("gain_db",0))/20)
    with sf.SoundFile(clean) as src, sf.SoundFile(dest,"w",samplerate=SR,channels=1,subtype="PCM_24") as out:
        for seg in plan["segments"]:
            n=round(seconds(seg["end_frame"],plan["fps"])*SR)-round(seconds(seg["start_frame"],plan["fps"])*SR)
            for pos in range(0,n,BLOCK):
                count=min(BLOCK,n-pos)
                clock=seg["reference_start"]+(np.arange(count,dtype=np.float64)+pos)/SR
                indices=(model["offset"]+model["rate"]*clock)*SR
                lo=int(np.floor(indices[0]));hi=int(np.ceil(indices[-1]))+2
                if lo < 0 or hi > len(src)+2:
                    raise ValueError("Microphone source does not cover the chosen interval.")
                src.seek(lo)
                raw=src.read(min(hi-lo,len(src)-lo),dtype="float32")
                # Clock correction, not speech time-stretching. Exact sample positions are retained.
                y=np.interp(indices,np.arange(lo,lo+len(raw)),raw)*gain
                if np.max(abs(y))>=1:
                    raise ValueError("Per-microphone gain clips. Reduce gain_db before normalization.")
                out.write(y)

def normalize_linked(paths, outputs, measured, target=-18.):
    import contextlib
    amp=10**((target-measured["integrated_lufs"])/20)
    ceiling=10**(-2.5/20)
    peaks=[]
    with contextlib.ExitStack() as stack:
        files=[stack.enter_context(sf.SoundFile(p)) for p in paths]
        while True:
            chunks=[f.read(BLOCK,dtype="float32") for f in files]
            if not len(chunks[0]): break
            # Protect each independent PCM stem as well as their sum, including cancellation.
            z=np.maximum(abs(np.sum(chunks,axis=0)),np.max(abs(np.array(chunks)),axis=0))*amp
            z=np.pad(z,(0,(-len(z))%48))
            peaks.append(np.max(abs(z.reshape(-1,48)),axis=1))
    peak=np.concatenate(peaks)
    attenuation=minimum_filter1d(np.minimum(0,20*np.log10(ceiling/np.maximum(peak,1e-12))),size=11)
    env=np.empty_like(attenuation);prev=0.
    for i,value in enumerate(attenuation):
        prev=min(float(value),prev+.06);env[i]=prev
    env=10**(env/20)
    with contextlib.ExitStack() as stack:
        files=[stack.enter_context(sf.SoundFile(p)) for p in paths]
        dests=[stack.enter_context(sf.SoundFile(p,"w",samplerate=SR,channels=1,subtype="PCM_24")) for p in outputs]
        pos=0
        while True:
            chunks=[f.read(BLOCK,dtype="float32") for f in files]
            if not len(chunks[0]):break
            ids=(np.arange(len(chunks[0]))+pos)/48
            left=np.minimum(np.floor(ids).astype(np.int64),len(env)-1)
            right=np.minimum(left+1,len(env)-1)
            gain=(env[left]+(env[right]-env[left])*(ids-np.floor(ids)))*amp
            for x,out in zip(chunks,dests):out.write(x*gain)
            pos+=len(chunks[0])
    return {"common_gain_db":target-measured["integrated_lufs"],"peak_control_max_db":float(-attenuation.min()),"peak_control_percent":float(np.mean(attenuation<-.1)*100)}

def prepare(project):
    p,root=load(project)
    plan=validate_plan(p,read(root/"edit_plan.json"))
    if not plan.get("approved"):
        raise ValueError("Review the edit plan and mark approved=true first.")
    signature=digest([plan,p["audio"],"audio-v1"])
    out=root/"audio"/signature[:12]
    out.mkdir(parents=True,exist_ok=True)
    receipt=root/"audio_stems.json"
    if receipt.exists():
        old=read(receipt)
        if old.get("signature")==signature and old.get("validated") and all(Path(t["path"]).exists() and t.get('fingerprint') == fingerprint(t['path']) for t in old["tracks"]):
            return old
    with worker(root):
        stages=[];outputs=[];tracks=[]
        for i,track in enumerate(p["audio"]["tracks"]):
            s=source(p,track["source_id"])
            clean=out/f"source_{i}.wav";stage=out/f"stage_{i}.wav";dest=out/f"{i+1:02}_microphone.wav"
            clean_source(s,clean)
            align_stem(p,plan,track,clean,stage)
            stages.append(stage);outputs.append(dest)
            tracks.append({"speaker":track["speaker"],"source_id":s["id"],"path":str(dest)})
        before=measure(stages,out/"before.log")
        if before["integrated_lufs"] < -65:
            raise ValueError("Audio is nearly silent; inspect the mapping before normalization.")
        normalization=normalize_linked(stages,outputs,before)
        after=measure(outputs,out/"after.log")
        expected=round(seconds(plan["total_frames"],plan["fps"])*SR)
        for f in outputs:
            info=sf.info(f)
            if info.frames != expected or info.samplerate != SR or info.channels != 1:
                raise ValueError("Stem timing/format mismatch")
        validated=after["true_peak_db"] <= -1.49 and -20 <= after["integrated_lufs"] <= -16
        for track in tracks:
            track['fingerprint'] = fingerprint(track['path'])
        result={"signature":signature,"plan_signature":digest(plan),"tracks":tracks,"frames":expected,"sample_rate":SR,"before":before,"after":after,"normalization":normalization,"validated":validated,
                "notes":"Identified microphones remain separate. Shared mixes remain one track. No source-separation claim. Tiny recorder-clock corrections use linear sample interpolation; inspect sync at separated points."}
        write(receipt,result)
        if not validated:
            raise ValueError("Audio output needs loudness/peak review; see audio_stems.json. Do not export yet.")
        state(root,"audio_ready","Separate final-clock microphone stems prepared; exact sample counts and mix loudness/true peak checked.")
    return result
