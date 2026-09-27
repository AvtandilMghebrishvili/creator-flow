import math
import numpy as np
import soundfile as sf
from scipy.ndimage import uniform_filter1d
from .core import load, write, source, sources, rate, frames, seconds, identity, require_mapping, state, read
from .sync import coverage, require_sync, analysis_audio

def speaker_turns(p, root, start, end):
    tracks = p["audio"]["tracks"]
    if len(tracks) < 2 or len({t["speaker"] for t in tracks}) != len(tracks):
        raise ValueError("Speaker-aware switching needs distinct identified microphones, or a reviewed --turns JSON. A shared mix does not identify speakers.")
    times = np.arange(start, end, .02)
    levels = []
    for t in tracks:
        s = source(p, t["source_id"])
        x, sr = sf.read(analysis_audio(s, root), dtype="float32")
        hop = round(sr*.02)
        n = len(x)//hop
        db = 20*np.log10(np.maximum(np.sqrt(np.mean(x[:n*hop].reshape(-1, hop)**2, axis=1)), 1e-8))
        m = p["sync"][s["id"]]
        sample_times = (m["offset"] + m["rate"]*times)/.02
        levels.append(uniform_filter1d(np.interp(sample_times, np.arange(n), db, left=-160, right=-160), size=25))
    levels = np.array(levels)
    current = int(np.argmax(levels[:, 0]))
    pending = None
    begin = start
    turns = []
    for i, time in enumerate(times):
        order = np.argsort(levels[:, i])
        choice = int(order[-1])
        if levels[choice, i] < -43 or levels[choice, i]-levels[order[-2], i] < 7:
            choice = current
        if choice == current:
            pending = None
        elif pending is None or pending[0] != choice:
            pending = (choice, time)
        elif time-pending[1] >= 1.1:
            boundary = max(begin, pending[1]-.12)
            turns.append({"start": begin, "end": boundary, "speaker": tracks[current]["speaker"]})
            current, begin, pending = choice, boundary, None
    turns.append({"start": begin, "end": end, "speaker": tracks[current]["speaker"]})
    # Retain the principal shot over brief acknowledgements.
    i = 1
    while i < len(turns)-1:
        if turns[i]["end"]-turns[i]["start"] < 4 and turns[i-1]["speaker"] == turns[i+1]["speaker"]:
            turns[i-1]["end"] = turns[i+1]["end"]
            del turns[i:i+2]
            i = max(1, i-1)
        else:
            i += 1
    return turns

def camera_at(p, role, at, fallback=True):
    cameras = sources(p, "camera")
    fps = float(rate(p["timeline"]["fps"]))
    available = [s for s in cameras if coverage(s, p["sync"][s["id"]])[0]-.001 <= at < math.floor((coverage(s, p["sync"][s["id"]])[1]-.04)*fps)/fps]
    for desired in ([role, "wide"] if fallback else [role]):
        selected = next((s for s in available if s["role"] == desired or s["id"] == desired), None)
        if selected:
            return selected
    if len(cameras) == 1 and available:
        return available[0]
    raise ValueError(f"No {role} or wide camera covers reference time {at:.2f}s. Supply a reviewed cutaway or adjust the edit; do not invent coverage.")

def validate_plan(p, plan):
    fps = rate(p["timeline"]["fps"])
    if plan["project_signature"] != identity(p):
        raise ValueError("Plan is stale: sources, sync, output format, audio or colors changed. Rebuild/review the plan.")
    if not plan['shots'] or not plan['segments'] or plan['total_frames'] <= 0:
        raise ValueError('Edit contains no usable video/content.')
    last = 0
    for s in plan["shots"]:
        if s["start_frame"] != last or s["end_frame"] <= last:
            raise ValueError("Video timeline has a gap, overlap or empty shot.")
        cam = source(p, s["camera_id"])
        m = p["sync"][cam["id"]]
        n = s["end_frame"]-s["start_frame"]
        segment = next((g for g in plan['segments'] if g['start_frame'] <= s['start_frame'] and s['end_frame'] <= g['end_frame']),None)
        if segment is None:
            raise ValueError('A video shot crosses an audio/content cut boundary.')
        expected_reference = segment['reference_start'] + seconds(s['start_frame']-segment['start_frame'],fps)
        if abs(s['reference_start']-expected_reference) > .001 or abs(s['reference_end']-s['reference_start']-seconds(n,fps)) > .001:
            raise ValueError('Video and audio/content reference clocks disagree.')
        mid = s["reference_start"] + seconds(n, fps)/2
        source_in = frames(m["offset"]+m["rate"]*mid-seconds(n, fps)/2, fps)
        if source_in < 0 or seconds(source_in+n, fps) > cam["duration"]+.0001:
            raise ValueError(f"Shot exceeds camera coverage: {s}")
        err = max(abs(seconds(source_in, fps)+(x-s["reference_start"])-m["offset"]-m["rate"]*x) for x in [s["reference_start"], s["reference_end"]])
        if err > seconds(1, fps):
            raise ValueError("Within-shot drift exceeds one timeline frame. Split the long shot or use explicit speed correction.")
        s["source_in_frame"] = source_in
        s["max_sync_error_ms"] = err*1000
        last = s["end_frame"]
    if last != plan["total_frames"]:
        raise ValueError("Timeline endpoint mismatch.")
    last = 0
    for seg in plan["segments"]:
        if seg["start_frame"] != last or seg["end_frame"] <= last:
            raise ValueError("Audio/content segments contain gaps or overlaps.")
        if abs(seg['reference_end']-seg['reference_start']-seconds(seg['end_frame']-seg['start_frame'],fps)) > .001:
            raise ValueError('Audio/content segment duration disagrees with its reference clock.')
        for t in p["audio"]["tracks"]:
            a, b = coverage(source(p, t["source_id"]), p["sync"][t["source_id"]])
            if seg["reference_start"] < a-.001 or seg["reference_end"] > b+.001:
                raise ValueError("An external microphone does not cover the edit. Resolve missing audio explicitly.")
        last = seg["end_frame"]
    if last != plan["total_frames"]:
        raise ValueError("Audio endpoint mismatch.")
    return plan

def build(project, turns_path=None, static_camera=None, keeps_path=None):
    p, root = load(project)
    require_mapping(p)
    require_sync(p)
    if not p.get("bounds") and not keeps_path:
        raise ValueError("Set bounds=[greeting_start, farewell_end] in reference-clock seconds after reviewing the transcript/media.")
    if not p["audio"]["tracks"]:
        raise ValueError("Select the delivery microphone(s), including a shared mix if that is the only usable recording.")
    keeps = read(keeps_path) if keeps_path else [p["bounds"]]
    fps = rate(p["timeline"]["fps"])
    supplied = read(turns_path) if turns_path else None
    plan = {"schema_version": 1, "project_signature": identity(p), "fps": str(fps), "shots": [], "segments": [], "approved": False}
    cursor = 0
    for raw_start, raw_end in keeps:
        start, end = seconds(frames(raw_start, fps), fps), seconds(frames(raw_end, fps), fps)
        if not (math.isfinite(start) and math.isfinite(end) and 0 <= start < end):
            raise ValueError("Invalid kept interval")
        n = frames(end-start, fps)
        plan["segments"].append({"reference_start": start, "reference_end": end, "start_frame": cursor, "end_frame": cursor+n})
        single = len(sources(p, "camera")) == 1
        if static_camera or single:
            turns = [{"start": start, "end": end, "speaker": static_camera or sources(p, "camera")[0]["id"]}]
        else:
            turns = supplied if supplied is not None else speaker_turns(p, root, start, end)
        valid = sorted([dict(t, start=max(start,t["start"]), end=min(end,t["end"])) for t in turns if t["start"] < end and t["end"] > start], key=lambda t:t["start"])
        turn_cursor = start
        for t in valid:
            if abs(t["start"]-turn_cursor) > .001:
                raise ValueError("Reviewed speaker turns must cover the kept interval exactly, without gaps/overlaps.")
            at = seconds(frames(t["start"], fps), fps)
            turn_end = seconds(frames(t["end"], fps), fps)
            wide_next = False
            while at < turn_end-.001:
                desired = "wide" if wide_next else t["speaker"]
                if wide_next:
                    try:
                        camera_at(p,'wide',at+.001,fallback=False)
                    except ValueError:
                        desired=t['speaker'];wide_next=False
                cam = camera_at(p, desired, at+.001)
                max_end = coverage(cam, p["sync"][cam["id"]])[1]
                limit = 7. if wide_next else 38.
                stop = min(turn_end, at+limit, math.floor((max_end-.04)*float(fps))/float(fps))
                if stop <= at:
                    raise ValueError("Camera tail is too short to use safely; adjust the last shot manually.")
                s = {"camera_id": cam["id"], "reference_start": at, "reference_end": stop,
                     "start_frame": cursor+frames(at-start, fps), "end_frame": cursor+frames(stop-start, fps)}
                plan["shots"].append(s)
                at = stop
                has_wide = any(c["role"] == "wide" and coverage(c,p["sync"][c["id"]])[0] <= at < coverage(c,p["sync"][c["id"]])[1] for c in sources(p,"camera"))
                wide_next = not wide_next and has_wide and not static_camera and not single
            turn_cursor = t["end"]
        if abs(turn_cursor-end) > .001:
            raise ValueError("Speaker turns do not cover the ending.")
        cursor += n
    plan["total_frames"] = cursor
    validate_plan(p, plan)
    write(root / "edit_plan.json", plan)
    state(root, "edit_review", "Candidate shot plan ready. Review greeting/farewell, speaker changes, camera availability and pacing. Set approved=true only after review. No video rendered.")
    return root / "edit_plan.json"
