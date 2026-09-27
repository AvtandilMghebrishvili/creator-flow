import argparse
import importlib.util
import json
import shutil
import sys
from pathlib import Path
from . import __version__
from .core import init,load,read,write,questions,digest,source,state

def parser():
    ap=argparse.ArgumentParser(prog='podcut',description='Local podcast tools, guided by your AI editor. Start with START_HERE.md.')
    ap.add_argument('--version',action='version',version=__version__)
    sub=ap.add_subparsers(dest='command',required=True)
    sub.add_parser('doctor')
    q=sub.add_parser('init');q.add_argument('folder')
    for name in ['questions','status','sync','colors','audio','xml','render','validate']:
        q=sub.add_parser(name);q.add_argument('project')
    q=sub.add_parser('sync-anchors');q.add_argument('project');q.add_argument('source_id');q.add_argument('anchors')
    q=sub.add_parser('verify-sync');q.add_argument('project');q.add_argument('source_id');q.add_argument('--note',required=True)
    q=sub.add_parser('approve-color');q.add_argument('project');q.add_argument('look',choices=['original','natural','warm','contrast'])
    q=sub.add_parser('plan');q.add_argument('project');q.add_argument('--turns');q.add_argument('--keeps');q.add_argument('--static-camera')
    q=sub.add_parser('approve-plan');q.add_argument('project');q.add_argument('--note',required=True)
    for name in ['transcribe','compare-audio']:
        q=sub.add_parser(name);q.add_argument('project' if name=='transcribe' else 'audio')
        q.add_argument('--model',default='small',help='Whisper model name or local directory; Meta uses the pinned CTC 300M int8 model.')
        q.add_argument('--language');q.add_argument('--start',type=float,default=0)
        q.add_argument('--seconds',type=float,default=None if name=='transcribe' else 40)
        q.add_argument('--allow-download',action='store_true')
        q.add_argument('--device',choices=['cpu','cuda'],default='cpu',help='Whisper device; Meta uses CPU with two threads.')
        if name=='transcribe':q.add_argument('--engine',choices=['both','whisper'],default='both')
    q=sub.add_parser('retime-transcript');q.add_argument('project');q.add_argument('--transcript')
    q=sub.add_parser('premiere-luts');q.add_argument('project');q.add_argument('--native',required=True);q.add_argument('--preset',required=True);q.add_argument('--sequence-id',required=True);q.add_argument('--output',required=True);q.add_argument('--closed',action='store_true')
    return ap

def execute(a):
    if a.command=='doctor':
        import platform
        return {'version':__version__,'python':sys.version.split()[0],'platform':platform.platform(),'ffmpeg':shutil.which('ffmpeg'),'ffprobe':shutil.which('ffprobe'),
                'optional_transcription_installed':importlib.util.find_spec('faster_whisper') is not None,
                'optional_meta_transcription_installed':importlib.util.find_spec('sherpa_onnx') is not None,
                'transcription_default':'Whisper + Meta comparison; doctor does not certify model weights or accuracy.',
                'premiere':'Optional; cannot infer installation or native API compatibility from the OS.'}
    if a.command=='init':return str(init(a.folder))
    if a.command in ('questions','status'):
        p,root=load(a.project)
        return {'questions':questions(p),'status':read(root/'status.json') if (root/'status.json').exists() else None}
    if a.command=='sync':
        from .sync import run_sync
        return run_sync(a.project)
    if a.command=='sync-anchors':
        from .sync import fit
        p,_=load(a.project);source(p,a.source_id)
        p['sync'][a.source_id]=fit(read(a.anchors));write(a.project,p);return p['sync'][a.source_id]
    if a.command=='verify-sync':
        p,_=load(a.project);model=p['sync'][a.source_id]
        if 'rate' not in model or 'offset' not in model:raise ValueError('No clock model to verify')
        model.update(verified=True,verification_note=a.note);write(a.project,p);return model
    if a.command in ('colors','approve-color'):
        from .color import previews,approve
        return previews(a.project) if a.command=='colors' else approve(a.project,a.look)
    if a.command=='plan':
        from .plan import build
        return str(build(a.project,a.turns,a.static_camera,a.keeps))
    if a.command in ('approve-plan','validate'):
        from .plan import validate_plan
        p,root=load(a.project);plan=validate_plan(p,read(root/'edit_plan.json'))
        if a.command=='approve-plan':
            plan.update(approved=True,review_note=a.note);write(root/'edit_plan.json',plan)
        return {'frames':plan['total_frames'],'shots':len(plan['shots']),'approved':plan['approved'],'max_sync_error_ms':max(s['max_sync_error_ms'] for s in plan['shots'])}
    if a.command=='audio':
        from .audio import prepare
        return prepare(a.project)
    if a.command in ('xml','render'):
        from .export import xml,render
        return str(xml(a.project) if a.command=='xml' else render(a.project))
    if a.command=='transcribe':
        if a.engine=='both':
            from .dual_asr import compare_project
            return str(compare_project(a.project,a.model,a.language,a.start,a.seconds,a.allow_download,a.device))
        from .transcript import transcribe
        return str(transcribe(a.project,a.model,a.language,a.start,a.seconds,a.allow_download,a.device))
    if a.command=='compare-audio':
        from .dual_asr import compare_audio
        return str(compare_audio(a.audio,a.model,a.language,a.start,a.seconds,a.allow_download,a.device))
    if a.command=='retime-transcript':
        from .transcript import retime
        return str(retime(a.project,a.transcript))
    if a.command=='premiere-luts':
        from .premiere import patch_luts
        return str(patch_luts(a.project,a.native,a.preset,a.sequence_id,a.output,a.closed))

def main():
    a=parser().parse_args()
    try:
        result=execute(a)
        if result is not None:print(json.dumps(result,ensure_ascii=False,indent=2))
    except (ValueError,FileNotFoundError,KeyError,StopIteration,RuntimeError) as e:
        print(f'Podcut: {e}',file=sys.stderr)
        raise SystemExit(2)
