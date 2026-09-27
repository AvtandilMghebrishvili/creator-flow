from pathlib import Path
import xml.etree.ElementTree as E
import shutil
from fractions import Fraction
from .core import load,read,write,source,sources,rate,frames,seconds,digest,process,binary,probe,worker,state,fingerprint
from .plan import validate_plan
from .color import lut_filter

def verify_encoded_audio(video, tracks, duration, root, fps):
    import numpy as np
    import soundfile as sf
    from scipy.signal import resample_poly,correlate
    from .audio import measure
    from .core import extract_audio
    measured=measure([video],root/'encoded_audio.log')
    checks=[]
    span=min(6.,duration)
    for i,t in enumerate(sorted(set([0.,max(0,duration/2-span/2),max(0,duration-span)]))):
        wav=root/f'encoded_check_{i}.wav'
        extract_audio({'path':str(video)},wav,16000,t,span)
        y,_=sf.read(wav,dtype='float32')
        originals=[]
        for track in tracks:
            x,_=sf.read(track['path'],start=round(t*48000),frames=round(span*48000),dtype='float32')
            originals.append(x)
        ref=resample_poly(np.sum(originals,axis=0),1,3)
        n=min(len(y),len(ref));y=y[:n];ref=ref[:n]
        if np.sqrt(np.mean(ref**2))<1e-5:
            checks.append({'second':t,'silence':True});continue
        cc=correlate(y,ref,mode='full',method='fft');center=n-1;radius=min(4000,n-1)
        lag=int(np.argmax(cc[center-radius:center+radius+1])-radius)
        aligned_y=y[max(lag,0):min(n,n+lag)]
        aligned_ref=ref[max(-lag,0):min(n,n-lag)]
        correlation=float(np.corrcoef(aligned_y,aligned_ref)[0,1])
        checks.append({'second':t,'lag_ms':lag/16,'correlation':correlation})
        if abs(lag/16000)>seconds(1,fps) or correlation<.9:
            raise ValueError(f'Encoded audio timing/content mismatch at {t:.2f}s: {checks[-1]}')
    if not -20<=measured['integrated_lufs']<=-16 or measured['true_peak_db']>-.9:
        raise ValueError(f'Encoded AAC needs loudness/peak review: {measured}')
    return {'loudness':measured,'timing_checks':checks}

def delivery_inputs(project):
    p,root=load(project)
    plan=validate_plan(p,read(root/"edit_plan.json"))
    if not plan.get("approved") or not p["color"].get("approved"):
        raise ValueError("Edit plan and color choice must be reviewed before delivery.")
    audio=read(root/"audio_stems.json")
    if not audio.get("validated") or audio["plan_signature"] != digest(plan):
        raise ValueError("Audio is unvalidated or stale. Run podcut audio again.")
    if any(not Path(t["path"]).exists() for t in audio["tracks"]):
        raise ValueError("Missing microphone stem.")
    if any(t.get('fingerprint') != fingerprint(t['path']) for t in audio['tracks']):
        raise ValueError('Microphone stems changed after validation. Run podcut audio again.')
    return p,root,plan,audio

def element(parent,name,value):
    node=E.SubElement(parent,name);node.text=str(value);return node

def xml_rate(parent,fps):
    fps=rate(fps);ntsc=fps.denominator==1001
    nominal=round(float(fps)*1001/1000) if ntsc else round(float(fps))
    if fps != (Fraction(nominal*1000,1001) if ntsc else Fraction(nominal)):
        raise ValueError("FCP7 XML supports integer and standard NTSC frame rates; choose a supported timeline rate.")
    r=E.SubElement(parent,"rate");element(r,"timebase",nominal);element(r,"ntsc","TRUE" if ntsc else "FALSE")

def video_format(parent,width,height,fps):
    xml_rate(parent,fps)
    for k,v in [("width",width),("height",height),("anamorphic","FALSE"),("pixelaspectratio","square"),("fielddominance","none")]:element(parent,k,v)

def xml(project):
    p,root,plan,audio=delivery_inputs(project)
    fps=plan["fps"];N=plan["total_frames"];settings=p["timeline"]
    doc=E.Element("xmeml",version="5");sq=E.SubElement(doc,"sequence",id="podcut-final")
    element(sq,"name",p["episode"]+" - FINAL / Podcut Flow");element(sq,"duration",N);xml_rate(sq,fps)
    tc=E.SubElement(sq,"timecode");xml_rate(tc,fps);element(tc,"string","00:00:00:00");element(tc,"frame",0);element(tc,"displayformat","NDF")
    media=E.SubElement(sq,"media");video=E.SubElement(media,"video")
    video_format(E.SubElement(E.SubElement(video,"format"),"samplecharacteristics"),settings["width"],settings["height"],fps)
    cameras=sources(p,"camera")
    roles=list(dict.fromkeys(s["role"] for s in sorted(cameras,key=lambda s:s["role"]!="wide")))
    seen=set()
    for role in roles:
        tr=E.SubElement(video,"track");element(tr,"name",role);element(tr,"enabled","TRUE");element(tr,"locked","FALSE")
        for i,shot in enumerate(plan["shots"]):
            s=source(p,shot["camera_id"])
            if s["role"]!=role:continue
            ci=E.SubElement(tr,"clipitem",id=f"shot-{i}");element(ci,"name",f"{s['id']} | {role} | {i+1:04}")
            element(ci,"enabled","TRUE");element(ci,"duration",frames(s["duration"],fps));xml_rate(ci,fps)
            n=shot["end_frame"]-shot["start_frame"]
            for k,v in [("start",shot["start_frame"]),("end",shot["end_frame"]),("in",shot["source_in_frame"]),("out",shot["source_in_frame"]+n)]:element(ci,k,v)
            f=E.SubElement(ci,"file",id="file-"+s["id"])
            if s["id"] not in seen:
                seen.add(s["id"]);element(f,"name",Path(s["path"]).name);element(f,"pathurl",Path(s["path"]).as_uri());xml_rate(f,s["fps"]);element(f,"duration",frames(s["duration"],s["fps"]))
                video_format(E.SubElement(E.SubElement(E.SubElement(f,"media"),"video"),"samplecharacteristics"),s["width"],s["height"],s["fps"])
            st=E.SubElement(ci,"sourcetrack");element(st,"mediatype","video");element(st,"trackindex",1)
            scale=min(settings["width"]/s["width"],settings["height"]/s["height"])*100
            if abs(scale-100)>.001:
                fx=E.SubElement(E.SubElement(ci,"filter"),"effect");element(fx,"name","Basic Motion");element(fx,"effectid","basic");element(fx,"effecttype","motion");element(fx,"mediatype","video")
                par=E.SubElement(fx,"parameter");element(par,"parameterid","scale");element(par,"name","Scale");element(par,"value",scale)
    aud=E.SubElement(media,"audio");element(aud,"numOutputChannels",2)
    for i,t in enumerate(audio["tracks"]):
        tr=E.SubElement(aud,"track");element(tr,"name",t["speaker"]+" microphone");element(tr,"enabled","TRUE");element(tr,"locked","FALSE");element(tr,"outputchannelindex",1)
        ci=E.SubElement(tr,"clipitem",id=f"audio-{i}");element(ci,"name",t["speaker"]+" - external microphone");element(ci,"enabled","TRUE");element(ci,"duration",N);xml_rate(ci,fps)
        for k,v in [("start",0),("end",N),("in",0),("out",N)]:element(ci,k,v)
        f=E.SubElement(ci,"file",id=f"audio-file-{i}");element(f,"name",Path(t["path"]).name);element(f,"pathurl",Path(t["path"]).as_uri());xml_rate(f,fps);element(f,"duration",N)
        a=E.SubElement(E.SubElement(f,"media"),"audio");element(a,"channelcount",1);char=E.SubElement(a,"samplecharacteristics");element(char,"depth",24);element(char,"samplerate",48000)
        st=E.SubElement(ci,"sourcetrack");element(st,"mediatype","audio");element(st,"trackindex",1)
        for effect,param,value in [("audiolevels","level",1),("audiopan","pan",0)]:
            fx=E.SubElement(E.SubElement(ci,"filter"),"effect");element(fx,"name",effect);element(fx,"effectid",effect);element(fx,"effecttype","audio");element(fx,"mediatype","audio")
            par=E.SubElement(fx,"parameter");element(par,"parameterid",param);element(par,"value",value)
    out=root/"exchange"/digest(plan)[:12];out.mkdir(parents=True,exist_ok=True)
    E.indent(doc,space="  ");E.ElementTree(doc).write(out/"Podcut_FINAL.xml",encoding="utf-8",xml_declaration=True)
    write(out/"color_handoff.json",{"applied_in_xml":False,"approved":p["color"],"clip_prefix_to_lut":p["color"]["luts"],"instructions":"Original-media XML does not carry Lumetri reliably. Import, apply matching camera LUTs once, save a native .prproj, reopen and verify. See docs/PREMIERE.md."})
    state(root,"premiere_handoff","Original-media XML + separate audio prepared. XML is not a native Premiere project. Apply approved colors in Premiere, save .prproj and verify before declaring completion.")
    return out/"Podcut_FINAL.xml"

def render(project):
    p,root,plan,audio=delivery_inputs(project)
    if p["decisions"].get("delivery") not in ("render","both"):
        raise ValueError("Final rendering was not requested. Choose render/both explicitly; Premiere-only mode never renders video.")
    out=root/"exports"/digest([plan,p["color"],"render-v1"])[:12];out.mkdir(parents=True,exist_ok=True)
    final=out/"episode.mp4"
    if final.exists():
        raise ValueError(f"Delivery already exists: {final}. Verify it or make a new reviewed version.")
    with worker(root):
        for i,shot in enumerate(plan["shots"]):
            dest=out/f"shot_{i:05}.mp4"
            n=shot["end_frame"]-shot["start_frame"]
            if dest.exists():
                info=probe(dest)
                if int(info["streams"][0].get("nb_frames",-1))==n:continue
                dest.unlink()
            s=source(p,shot["camera_id"]);vf=[]
            lut=p["color"]["luts"].get(s["id"])
            if lut:
                local=f"lut_{s['id']}.cube";shutil.copy2(lut,out/local);vf.append(lut_filter(local))
            w,h=p["timeline"]["width"],p["timeline"]["height"]
            vf += [f"fps={plan['fps']}",f"scale={w}:{h}:force_original_aspect_ratio=decrease",f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2","setsar=1"]
            temp=out/f"shot_{i:05}.partial.mp4"
            process([binary("ffmpeg"),"-hide_banner","-loglevel","error","-nostdin","-threads","2","-filter_threads","1","-ss",str(seconds(shot["source_in_frame"],plan["fps"])),"-i",s["path"],"-an","-vf",",".join(vf),"-frames:v",str(n),"-c:v","libx264","-threads","2","-preset","medium","-crf","18","-pix_fmt","yuv420p","-color_primaries","bt709","-color_trc","bt709","-colorspace","bt709","-y",str(temp)],cwd=out)
            temp.replace(dest)
            print(f"Shot {i+1}/{len(plan['shots'])}",flush=True)
        listing=out/"join.txt";listing.write_text("".join(f"file 'shot_{i:05}.mp4'\n" for i in range(len(plan["shots"]))),encoding="ascii")
        args=[binary("ffmpeg"),"-hide_banner","-loglevel","error","-nostdin","-threads","2","-f","concat","-safe","1","-i",str(listing)]
        for t in audio["tracks"]:args += ["-i",t["path"]]
        graph="".join(f"[{i+1}:a]" for i in range(len(audio["tracks"])))+f"amix=inputs={len(audio['tracks'])}:normalize=0,pan=stereo|c0=c0|c1=c0[a]"
        temp=out/"episode.partial.mp4"
        process([*args,"-filter_complex_threads","1","-filter_complex",graph,"-map","0:v","-map","[a]","-c:v","copy","-c:a","aac","-b:a","320k","-ar","48000","-movflags","+faststart","-y",str(temp)])
        info=probe(temp);v=next(s for s in info["streams"] if s["codec_type"]=="video")
        if int(v.get("nb_frames",-1)) != plan["total_frames"] or abs(float(info["format"]["duration"])-seconds(plan["total_frames"],plan["fps"]))>.1:
            raise ValueError("Encoded delivery duration/frame count failed validation. Partial output retained for diagnosis.")
        process([binary("ffmpeg"),"-hide_banner","-loglevel","error","-nostdin","-threads","2","-i",str(temp),"-f","null","-"])
        encoded_audio=verify_encoded_audio(temp,audio['tracks'],seconds(plan['total_frames'],plan['fps']),out,plan['fps'])
        temp.replace(final)
        write(out/"validation.json",{"decoded":True,"frames":plan["total_frames"],"probe":info,"audio_stems":audio["after"],"encoded_audio":encoded_audio,"remaining_review":"Agent/user visual and listening review: camera identity, natural cut points, color and lip sync. Numerical checks are not a full-duration editorial review."})
        state(root,"render_review","Video encoded and decoded successfully. Review exported audio sync, colors, cuts and loudness before final delivery.")
    return final
