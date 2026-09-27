from __future__ import annotations
import contextlib
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
from fractions import Fraction

MEDIA = {".mp4", ".mov", ".mxf", ".mkv", ".avi", ".m4v", ".webm", ".wav", ".flac", ".mp3", ".m4a", ".aiff", ".aif", ".braw", ".r3d"}

def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))

def write(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp")
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temp, path)

def digest(data):
    return hashlib.sha256(json.dumps(data, sort_keys=True, ensure_ascii=False).encode()).hexdigest()

def fingerprint(path):
    p = Path(path).resolve()
    s = p.stat()
    return {"path": str(p), "size": s.st_size, "mtime_ns": s.st_mtime_ns}

def binary(name):
    result = os.environ.get("PODCUT_" + name.upper()) or shutil.which(name)
    if not result:
        raise ValueError(f"{name} was not found. See docs/SETUP.md; reopen the terminal after installation.")
    return result

def process(args, **kwargs):
    env = dict(os.environ, OMP_NUM_THREADS="2", OPENBLAS_NUM_THREADS="2", MKL_NUM_THREADS="2")
    if os.name == "nt":
        kwargs.setdefault("creationflags", subprocess.CREATE_NO_WINDOW | subprocess.BELOW_NORMAL_PRIORITY_CLASS)
    result = subprocess.run([str(x) for x in args], capture_output=True, env=env, **kwargs)
    if result.returncode:
        raise ValueError(result.stderr.decode("utf-8", errors="replace")[-6000:])
    return result

def ffmpeg(args):
    return process([binary("ffmpeg"), "-hide_banner", "-loglevel", "error", "-nostdin", "-threads", "2", "-filter_threads", "1", *args])

def probe(path):
    return json.loads(process([binary("ffprobe"), "-v", "error", "-show_format", "-show_streams", "-of", "json", str(path)]).stdout)

def rate(value):
    try:
        r = Fraction(str(value))
        if r <= 0:
            raise ValueError('Frame rate must be positive')
        return r
    except (ValueError, ZeroDivisionError):
        raise ValueError(f'Invalid frame rate {value!r}; confirm the source and timeline rates.')

def frames(seconds, fps):
    # Consistent half-up rounding, including fractional NTSC rates.
    return math.floor(float(Fraction(str(seconds)) * rate(fps)) + .5)

def seconds(frame, fps):
    return float(Fraction(frame) / rate(fps))

def load(path, check_sources=True):
    path = Path(path).resolve()
    data = read(path)
    if data.get("schema_version") != 1:
        raise ValueError("Unsupported project schema")
    if check_sources:
        for s in data["sources"]:
            if s.get("use") and fingerprint(s["path"]) != s["fingerprint"]:
                raise ValueError(f"Source changed or moved: {s['id']}. Re-inventory and revalidate sync; do not reuse stale outputs.")
        for ident, expected in data.get('color',{}).get('lut_fingerprints',{}).items():
            if fingerprint(data['color']['luts'][ident]) != expected:
                raise ValueError('An approved LUT changed. Prepare new previews and ask for a new color choice.')
    return data, path.parent

def sources(p, kind=None):
    return [s for s in p["sources"] if s.get("use") and (kind is None or s["kind"] == kind)]

def source(p, ident):
    return next(s for s in p["sources"] if s["id"] == ident)

def identity(p):
    return digest({k: p.get(k) for k in ("sources", "reference_id", "timeline", "sync", "color", "audio", "bounds")})

def state(root, phase, detail):
    write(root / "status.json", {"phase": phase, "detail": detail})
    (root / "WORK_STATUS.md").write_text(f"# {phase}\n\n{detail}\n", encoding="utf-8")

@contextlib.contextmanager
def worker(root):
    lock = Path(root) / "worker.lock"
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        raise ValueError(f"Another heavy job may be active. Inspect {lock}; remove only after confirming its process stopped.")
    try:
        os.write(fd, str(os.getpid()).encode())
        os.close(fd)
        yield
    finally:
        lock.unlink(missing_ok=True)

def init(folder):
    folder = Path(folder).expanduser().resolve()
    if not folder.is_dir():
        raise ValueError("Choose the episode's existing source folder first.")
    dest = folder / ".podcut"
    if (dest / "project.json").exists():
        raise ValueError(f"Project already exists: {dest / 'project.json'}. Resume it; do not overwrite decisions.")
    found = []
    errors = []
    for f in sorted(folder.rglob("*")):
        if not f.is_file() or f.suffix.lower() not in MEDIA:
            continue
        if any(x in {".podcut", "Video_Work", ".git", ".venv"} for x in f.relative_to(folder).parts):
            continue
        try:
            info = probe(f)
            videos = [s for s in info["streams"] if s["codec_type"] == "video" and not s.get("disposition", {}).get("attached_pic")]
            audios = [s for s in info["streams"] if s["codec_type"] == "audio"]
            if not videos and not audios:
                continue
            kind = "camera" if videos else "audio"
            found.append({"id": f"s{len(found)+1:02}", "path": str(f), "kind": kind, "role": None, "use": False,
                          "duration": float(info["format"].get("duration", 0)), "fingerprint": fingerprint(f),
                          "fps": videos[0].get("avg_frame_rate", "25/1") if videos else None,
                          "width": videos[0].get("width") if videos else None, "height": videos[0].get("height") if videos else None,
                          "audio_channels": audios[0].get("channels", 0) if audios else 0,
                          "audio_stream": 0, "channel": None, "color_space": "unknown", "input_lut": None,
                          "probe": info})
        except (ValueError, KeyError) as e:
            errors.append({"path": str(f), "error": str(e)})
    if not found:
        raise ValueError("No decodable media found. RAW codecs may need a supported NLE/transcode first. " + str(errors))
    dest.mkdir(exist_ok=True)
    p = {"schema_version": 1, "episode": folder.name, "source_folder": str(folder), "sources": found,
         "reference_id": None, "speakers": [], "layout": {}, "speaker_examples": [],
         "timeline": {"fps": "25/1", "width": 1920, "height": 1080}, "sync": {},
         "decisions": {"color_requested": None, "delivery": None, "language": None, "mapping_confirmed": False},
         "color": {"approved": None, "luts": {}}, "audio": {"tracks": []}, "bounds": None}
    write(dest / "project.json", p)
    write(dest / "inventory_errors.json", errors)
    state(dest, "intake", "Inventory complete. Ask only unresolved questions; record source roles before analysis.")
    return dest / "project.json"

def questions(p):
    q = []
    active = sources(p)
    if not p["decisions"].get("mapping_confirmed"):
        q.append("Which file(s) show the guest, host/speaker and optional wide shot? Which contain the guest mic, host mic or shared mix? Confirm sequential camera parts and recorder channels; mark unused files use=false.")
    if not p.get("reference_id"):
        q.append("Which recording should define the common clock? Prefer the uninterrupted external audio mix or a continuous microphone recording.")
    if not p["decisions"].get("language"):
        q.append("What language(s) are spoken, and how are participants' names spelled?")
    if p["decisions"].get("color_requested") is None:
        q.append("Are colors already finished? Keep them, or prepare several graded alternatives for you to choose?")
    if not p["decisions"].get("delivery"):
        q.append("Do you want a rendered video, or an editable Premiere project for you to review and render? If Premiere: is it installed, and on which OS/version?")
    camera_roles = {s.get('role') or s['id'] for s in active if s['kind'] == 'camera'}
    if len(camera_roles) == 1 and len(p.get("audio", {}).get("tracks", [])) <= 1:
        if not p.get("layout", {}).get("confirmed") or len(p.get("speaker_examples", [])) < 2:
            q.append("One camera plus one mixed audio track is ambiguous. Who sits on the left/right? Identify who speaks in two or three timestamped samples. Automatic speaker isolation is not reliable; keep the full frame unless a crop is requested and resolution permits it.")
    if not p.get("bounds"):
        q.append("Where should the episode begin/end? If you want the greeting through the farewell, I will locate them from the recording and ask only if ambiguous.")
    return q

def require_mapping(p):
    if not p["decisions"].get("mapping_confirmed") or not p.get("reference_id"):
        raise ValueError("Confirm source roles and reference_id in project.json first. Run podcut questions.")
    if not sources(p, "camera"):
        raise ValueError("At least one camera must be selected.")
    ref = source(p, p["reference_id"])
    if not ref.get('use') or not ref.get("audio_channels"):
        raise ValueError("The clock reference needs usable audio.")
    ids = [s['id'] for s in p['sources']]
    if len(ids) != len(set(ids)):
        raise ValueError('Source IDs must be unique, including split recorder channels.')
    for s in sources(p):
        if not isinstance(s.get('role'),str) or not s['role'].strip():
            raise ValueError(f"Confirm the role for {s['id']}.")
        streams = [a for a in s.get('probe',{}).get('streams',[]) if a.get('codec_type') == 'audio']
        index = s.get('audio_stream',0)
        if streams and (not isinstance(index,int) or not 0 <= index < len(streams)):
            raise ValueError(f"Invalid audio stream for {s['id']}.")
        channels = streams[index]['channels'] if streams else s.get('audio_channels',0)
        channel = s.get('channel')
        if channel is not None and (not isinstance(channel,int) or not 0 <= channel < channels):
            raise ValueError(f"Invalid recorder channel for {s['id']}.")
    recordings = set()
    for t in p.get('audio',{}).get('tracks',[]):
        s = source(p,t['source_id'])
        if not s.get('use') or not s.get('audio_channels') or not t.get('speaker'):
            raise ValueError('Each delivery microphone needs a selected audio source and an identified speaker/mix label.')
        key=(str(Path(s['path']).resolve()),s.get('audio_stream',0),s.get('channel'))
        if key in recordings:
            raise ValueError('The same recording/channel is listed twice. A shared mix is one lane, not isolated microphones.')
        recordings.add(key)

def extract_audio(s, output, sr=8000, start=0, duration=None):
    output = Path(output)
    temp = output.with_name(output.stem + '.partial.wav')
    args = ["-ss", str(start), "-i", s["path"]]
    if duration is not None:
        args += ["-t", str(duration)]
    args += ["-map", f"0:a:{s.get('audio_stream', 0)}", "-vn"]
    if s.get("channel") is not None:
        args += ["-af", f"pan=mono|c0=c{int(s['channel'])}"]
    args += ["-ac", "1", "-ar", str(sr), "-c:a", "pcm_s16le", "-y", str(temp)]
    Path(output).parent.mkdir(parents=True, exist_ok=True)
    ffmpeg(args)
    temp.replace(output)
