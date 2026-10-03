import argparse
import importlib.util
import json
import shutil
import sys
from pathlib import Path
from . import __version__
from .core import init,load,read,write,questions,digest,source,state

def parser():
    ap=argparse.ArgumentParser(prog=Path(sys.argv[0]).stem if Path(sys.argv[0]).stem in ('podcut','creator-flow') else 'creator-flow',description='Creator Flow: podcasts, Shorts, Reels and archive tools. Start with START_HERE.md.')
    ap.add_argument('--version',action='version',version=__version__)
    sub=ap.add_subparsers(dest='command',required=True)
    sub.add_parser('doctor')
    q=sub.add_parser('studio-serve',help='Shared-memory Studio with subscription connectors and local editing.')
    q.add_argument('--workspace',required=True);q.add_argument('--extension-id',action='append',default=[],dest='extension_ids');q.add_argument('--port',type=int,default=8772)
    q=sub.add_parser('extension-serve',help='Optional loopback bridge for the YouTube browser extension.')
    q.add_argument('--workspace',required=True);q.add_argument('--extension-id',action='append',required=True,dest='extension_ids')
    q.add_argument('--port',type=int,default=8772);q.add_argument('--provider',choices=['none','openai','ollama'],default='none');q.add_argument('--model')
    from .archive import COMMANDS
    q=sub.add_parser('archive',help='Bundled YouTube archive tools (optional Node/yt-dlp).')
    q.add_argument('tool',choices=COMMANDS)
    q.add_argument('args',nargs=argparse.REMAINDER)
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
        if name=='transcribe':q.add_argument('--engine',choices=['meta','both','whisper'],default='meta')
    q=sub.add_parser('retime-transcript');q.add_argument('project');q.add_argument('--transcript')
    q=sub.add_parser('clips-init',help='Start a review only after the user agrees count/duration.');q.add_argument('video');q.add_argument('transcript');q.add_argument('folder')
    q.add_argument('--count',type=int,required=True);q.add_argument('--min-seconds',type=float,required=True);q.add_argument('--max-seconds',type=float,required=True);q.add_argument('--note',required=True)
    for name in ['clips-propose','clips-review','clips-render']:
        q=sub.add_parser(name);q.add_argument('review')
    q=sub.add_parser('clips-import');q.add_argument('review');q.add_argument('corrections')
    q=sub.add_parser('clips-font');q.add_argument('review');q.add_argument('font');q.add_argument('--origin',required=True)
    q=sub.add_parser('clips-approve');q.add_argument('review');q.add_argument('--note',required=True);q.add_argument('--matching-video-note',required=True)
    q=sub.add_parser('clips-brief');q.add_argument('review');q.add_argument('--count',type=int,required=True);q.add_argument('--min-seconds',type=float,required=True);q.add_argument('--max-seconds',type=float,required=True);q.add_argument('--note',required=True)
    q=sub.add_parser('premiere-luts');q.add_argument('project');q.add_argument('--native',required=True);q.add_argument('--preset',required=True);q.add_argument('--sequence-id',required=True);q.add_argument('--output',required=True);q.add_argument('--closed',action='store_true')
    return ap

def execute(a):
    if a.command=='studio-serve':
        from .extension import serve
        return serve(a.workspace,a.extension_ids,a.port,studio_enabled=True)
    if a.command=='extension-serve':
        from .extension import serve
        return serve(a.workspace,a.extension_ids,a.port,a.provider,a.model)
    if a.command=='archive':
        from .archive import run
        raise SystemExit(run(a.tool,a.args))
    if a.command.startswith('clips-'):
        from . import clips
        if a.command=='clips-init':return str(clips.init(a.video,a.transcript,a.folder,a.count,a.min_seconds,a.max_seconds,a.note))
        if a.command=='clips-brief':return str(clips.set_brief(a.review,a.count,a.min_seconds,a.max_seconds,a.note))
        if a.command=='clips-propose':return str(clips.propose(a.review))
        if a.command=='clips-review':return str(clips.page(a.review))
        if a.command=='clips-font':return str(clips.add_font(a.review,a.font,a.origin))
        if a.command=='clips-import':return str(clips.import_review(a.review,a.corrections))
        if a.command=='clips-approve':return str(clips.approve(a.review,a.note,a.matching_video_note))
        if a.command=='clips-render':return str(clips.render(a.review))
    if a.command=='doctor':
        import platform
        return {'version':__version__,'python':sys.version.split()[0],'platform':platform.platform(),'ffmpeg':shutil.which('ffmpeg'),'ffprobe':shutil.which('ffprobe'),
                'optional_transcription_installed':importlib.util.find_spec('sherpa_onnx') is not None,
                'optional_whisper_installed':importlib.util.find_spec('faster_whisper') is not None,
                'optional_meta_transcription_installed':importlib.util.find_spec('sherpa_onnx') is not None,
                'transcription_default':'Meta Omnilingual ASR; Whisper comparison is opt-in. Doctor does not certify weights or accuracy.',
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
        if a.engine in ('meta','both'):
            from .dual_asr import transcribe_project
            return str(transcribe_project(a.project,a.model,a.language,a.start,a.seconds,a.allow_download,a.device,a.engine))
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
        print(f'Creator Flow: {e}',file=sys.stderr)
        raise SystemExit(2)
