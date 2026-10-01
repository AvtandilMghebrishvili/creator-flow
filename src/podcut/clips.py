"""Local clips with explicit scope, transcript/style review, and real-footage hooks.

The shortlist and inset layout adapt the YOUTUBETECHCRUSH workflow; see
THIRD_PARTY_NOTICES.md. No recognition, downloads or uploads happen here.
"""
from __future__ import annotations

import hashlib
from itertools import islice
import math
from pathlib import Path
import re
import shutil

from .core import binary, digest, fingerprint, probe, process, read, worker, write
from .transcript import save_formats

SCHEMA = "podcut-clips-v1"
PALETTES = {
    "white": {"color": "#FFFFFF", "outline_color": "#101820"},
    "yellow": {"color": "#FFE55C", "outline_color": "#111827"},
    "mint": {"color": "#77F2CE", "outline_color": "#10252B"},
}
# Unicode word boundaries: JavaScript's ASCII \\b skipped Georgian in the original.
SIGNALS = [
    ("story", 2.5, r"(?<!\w)(მახსოვს|პირველად|იმ დღეს|გამიკვირდა|i remember|the first time)"),
    ("conflict", 2.5, r"(?<!\w)(შეცდომ|ჩავარდ|უარი|საშიშ|რისკ|refused|failed|risk)"),
    ("specific number", 1.5, r"\b\d{2,}\b"),
    ("question", 1.0, r"\?|წარმოიდგინე|imagine|did you know"),
]


def number(value, label):
    if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value):
        raise ValueError(f"{label} must be a finite number")
    return float(value)


def note(value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("Record the user's actual confirmation, not an assumed approval.")
    return value.strip()


def file_hash(path):
    with Path(path).open("rb") as f:
        h = hashlib.sha256()
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def validate_cues(cues, duration):
    if not isinstance(cues, list) or not cues:
        raise ValueError("A full timestamped transcript is required, including when captions are off.")
    previous = 0.0
    for cue in cues:
        a, b = number(cue["start"], "cue start"), number(cue["end"], "cue end")
        if not 0 <= a < b <= duration + .001 or a < previous - .001:
            raise ValueError("Transcript cues must be ordered, non-overlapping and within the video.")
        if not isinstance(cue["text"], str) or not cue["text"].strip():
            raise ValueError("Every cue needs text; remove unwanted cues explicitly.")
        previous = b


def normalize_transcript(data, duration):
    if data.get("complete") is not True:
        raise ValueError("Use a complete transcript, not a partial ASR sample.")
    if data.get("clock") not in {"final timeline seconds", "media seconds"}:
        raise ValueError("Retime Meta's source transcript first; clips require the video's own clock.")
    cues = []
    for segment in data["segments"]:
        words = segment.get("words") or []
        # Never silently replace corrected text with stale word hypotheses.
        text = segment["text"].strip()
        joined = " ".join(w["word"].strip() for w in words)
        if words and " ".join(text.split()) == " ".join(joined.split()):
            for i in range(0, len(words), 4):
                group = words[i:i + 4]
                cues.append({"start": group[0]["start"], "end": group[-1]["end"],
                             "text": " ".join(w["word"].strip() for w in group)})
        else:
            cues.append({"start": segment["start"], "end": segment["end"], "text": text})
    validate_cues(cues, duration)
    return cues


def _brief(count, minimum, maximum):
    if isinstance(count, bool) or not isinstance(count, int) or not 1 <= count <= 100:
        raise ValueError("Confirm a clip count between 1 and 100.")
    if not 0 < number(minimum, "minimum duration") <= number(maximum, "maximum duration"):
        raise ValueError("Confirm a positive duration range.")
    return {"count": count, "min_seconds": minimum, "max_seconds": maximum}


def init(video, transcript, folder, count, minimum, maximum, confirmation):
    brief = _brief(count, minimum, maximum)
    confirmation = note(confirmation)
    folder = Path(folder).resolve()
    dest = folder / "review.json"
    if dest.exists():
        raise ValueError("Review already exists. Resume it instead of overwriting corrections.")
    video, transcript = Path(video).resolve(), Path(transcript).resolve()
    info = probe(video)
    streams = info["streams"]
    if not any(s["codec_type"] == "video" for s in streams) or not any(s["codec_type"] == "audio" for s in streams):
        raise ValueError("Provide the edited video with its matching final audio.")
    duration = float(info["format"]["duration"])
    original = read(transcript)
    data = {"schema": SCHEMA, "video": fingerprint(video), "duration": duration,
            "transcript_source": {"path": str(transcript), "sha256": file_hash(transcript)},
            "brief": brief, "brief_approval": {"signature": digest(brief), "note": confirmation},
            "cues": normalize_transcript(original, duration), "fonts": [], "clips": [],
            "style": {"font_id": None, "size": 64, "color": "#FFFFFF",
                      "outline_color": "#101820", "outline": 4},
            "layout": "blur", "approval": None}
    write(dest, data)
    page(dest)
    return dest


def load_review(path):
    path = Path(path).resolve()
    data = read(path)
    if data.get("schema") != SCHEMA:
        raise ValueError("Unsupported clips review schema")
    if fingerprint(data["video"]["path"]) != data["video"]:
        raise ValueError("Video changed; create a new review with the matching transcript.")
    if file_hash(data["transcript_source"]["path"]) != data["transcript_source"]["sha256"]:
        raise ValueError("Original transcript changed; re-import and review its corrections.")
    validate_cues(data["cues"], data["duration"])
    return data, path.parent


def require_brief(data):
    brief = data["brief"]
    _brief(brief["count"], brief["min_seconds"], brief["max_seconds"])
    if data.get("brief_approval", {}).get("signature") != digest(brief):
        raise ValueError("Count/duration changed. Ask the user and confirm the new brief first.")


def set_brief(path, count, minimum, maximum, confirmation):
    data, _ = load_review(path)
    data["brief"] = _brief(count, minimum, maximum)
    data["brief_approval"] = {"signature": digest(data["brief"]), "note": note(confirmation)}
    data["approval"] = None
    write(path, data)
    return page(path)


def candidates(cues, minimum, maximum):
    found = []
    for i, first in enumerate(cues):
        rows = []
        for cue in islice(cues, i, None):
            if cue["end"] - first["start"] > maximum:
                break
            rows.append(cue)
        if not rows or rows[-1]["end"] - first["start"] < minimum:
            continue
        text = " ".join(c["text"] for c in rows)
        hits = [(name, weight, len(re.findall(pattern, text, re.I))) for name, weight, pattern in SIGNALS]
        score = sum(weight * (1 + .35 * (min(n, 3) - 1)) for _, weight, n in hits if n)
        found.append({"start": first["start"], "end": rows[-1]["end"], "score": round(score, 2),
                      "signals": [name for name, _, n in hits if n], "text": text})
    return sorted(found, key=lambda c: (-c["score"], c["start"]))


def propose(path):
    data, root = load_review(path)
    require_brief(data)
    brief = data["brief"]
    shortlist = candidates(data["cues"], brief["min_seconds"], brief["max_seconds"])
    write(root / "candidates.json", {"method": "Heuristic shortlist, not a quality prediction or learned channel model",
                                      "candidates": shortlist[:max(30, brief["count"] * 5)]})
    if data["clips"]:
        raise ValueError("Existing selections preserved. Read candidates.json; edit the review deliberately.")
    chosen = []
    for row in shortlist:
        if any(row["start"] < c["end"] and row["end"] > c["start"] for c in chosen):
            continue
        chosen.append({"id": f"clip-{len(chosen) + 1:02}", "start": row["start"], "end": row["end"],
                       "hook": None, "captions": None, "thumbnail": {"requested": None, "text": ""}})
        if len(chosen) == brief["count"]:
            break
    data["clips"] = chosen
    data["approval"] = None
    write(path, data)
    return page(path)


def font_info(path):
    from fontTools.ttLib import TTFont
    path = Path(path).resolve()
    if path.suffix.lower() not in {".ttf", ".otf"}:
        raise ValueError("Choose an original static TTF or OTF font file.")
    with TTFont(path) as font:
        if "fvar" in font:
            raise ValueError("Choose the publisher's static font file for predictable video rendering.")
        name = font["name"].getDebugName(4) or font["name"].getBestFamilyName()
        if not name or any(c in name for c in ",\n\r\\{}"):
            raise ValueError("Unsupported font name")
        return name, set((font.getBestCmap() or {}).keys())


def add_font(path, font_file, origin):
    data, _ = load_review(path)
    family, _ = font_info(font_file)
    h = file_hash(font_file)
    entry = {"id": h[:16], "path": str(Path(font_file).resolve()), "family": family,
             "sha256": h, "origin": note(origin)}
    if not any(f["id"] == entry["id"] for f in data["fonts"]):
        data["fonts"].append(entry)
    data["approval"] = None
    write(path, data)
    return page(path)


def clip_ranges(clip, duration):
    a, b = number(clip["start"], "clip start"), number(clip["end"], "clip end")
    if not 0 <= a < b <= duration:
        raise ValueError("Clip range is outside the source video.")
    hook = clip.get("hook")
    if not isinstance(hook, dict):
        raise ValueError("Choose an actual spoken hook range for each clip and show it to the user.")
    h0, h1 = number(hook["start"], "hook start"), number(hook["end"], "hook end")
    if not a <= h0 < h1 <= b:
        raise ValueError("The hook must be a real passage inside this clip.")
    if hook.get("mode") not in {"move", "repeat"}:
        raise ValueError("Confirm whether the opening hook is moved or repeated.")
    if hook["mode"] == "repeat":
        return [(h0, h1), (a, b)]
    return [(x, y) for x, y in [(h0, h1), (a, h0), (h1, b)] if y - x > .00001]


def retime_cues(cues, ranges):
    result, cursor = [], 0.0
    for a, b in ranges:
        for cue in cues:
            if cue["end"] <= a + .00001 or cue["start"] >= b - .00001:
                continue
            if cue["start"] < a - .001 or cue["end"] > b + .001:
                raise ValueError("A cut crosses a subtitle cue. Refine the cue/boundary by listening before approval.")
            result.append({"start": max(0., cue["start"] - a) + cursor,
                           "end": min(b, cue["end"]) - a + cursor, "text": cue["text"]})
        cursor += b - a
    return result


def payload(data):
    return {k: v for k, v in data.items() if k != "approval"}


def validate_style(data):
    style = data["style"]
    for key in ("color", "outline_color"):
        if not re.fullmatch(r"#[0-9a-fA-F]{6}", style[key]):
            raise ValueError("Use #RRGGBB caption colors.")
    if not 24 <= number(style["size"], "font size") <= 110 or not 0 <= number(style["outline"], "outline") <= 10:
        raise ValueError("Unsupported caption size/outline")
    font = next((f for f in data["fonts"] if f["id"] == style["font_id"]), None)
    if not font or file_hash(font["path"]) != font["sha256"]:
        raise ValueError("Select an unchanged original font file; generated/fallback lettering is not accepted.")
    family, glyphs = font_info(font["path"])
    if family != font["family"]:
        raise ValueError("Font metadata changed")
    selected = [cue for clip in data["clips"] if clip["captions"]
                for cue in retime_cues(data["cues"], clip_ranges(clip, data["duration"]))]
    text = "".join(c["text"] for c in selected)
    missing = sorted({c for c in text if not c.isspace() and ord(c) not in glyphs})
    if missing:
        raise ValueError("This font lacks transcript characters: " + " ".join(missing[:20]))
    # Fail before rendering text that cannot fit two readable caption lines.
    for cue in selected:
        wrap_text(cue["text"], font["path"], style["size"], 940)
    return font


def thumbnail_request(value):
    """Only an optional cover request and exact copy, never a generation receipt."""
    if not isinstance(value, dict):
        raise ValueError("Thumbnail preference must contain requested and text fields.")
    requested = value.get("requested")
    if requested is not None and not isinstance(requested, bool):
        raise ValueError("Thumbnail requested must be true, false or null.")
    text = value.get("text", "")
    if not isinstance(text, str):
        raise ValueError("Thumbnail text must be a string; leave it empty for suggestions.")
    return {"requested": requested, "text": text}


def validate_selection(data):
    require_brief(data)
    if data["layout"] not in {"blur", "crop", "source"}:
        raise ValueError("Select blur, crop or source layout.")
    if len(data["clips"]) != data["brief"]["count"]:
        raise ValueError("Selected count differs from the agreed count. Ask about revising the brief.")
    ids = set()
    for clip in data["clips"]:
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,60}", clip["id"]) or clip["id"] in ids:
            raise ValueError("Use unique simple clip identifiers.")
        ids.add(clip["id"])
        if "thumbnail" in clip:
            thumbnail_request(clip["thumbnail"])
        if not isinstance(clip.get("captions"), bool):
            raise ValueError("Ask whether captions should be on or off for every video.")
        ranges = clip_ranges(clip, data["duration"])
        total = sum(b - a for a, b in ranges)
        if not data["brief"]["min_seconds"] - .001 <= total <= data["brief"]["max_seconds"] + .001:
            raise ValueError("Duration including the opening hook is outside the approved range.")
        retime_cues(data["cues"], ranges)
    if any(c["captions"] for c in data["clips"]):
        validate_style(data)


def approve(path, confirmation, matching_video_note):
    data, _ = load_review(path)
    validate_selection(data)
    data["approval"] = {"signature": digest(payload(data)), "note": note(confirmation),
                        "matching_video_note": note(matching_video_note)}
    write(path, data)
    return page(path)


def import_review(path, edited):
    data, _ = load_review(path)
    incoming = read(edited)
    incoming_video = incoming.get("video")
    if isinstance(incoming_video, dict):
        incoming_video = dict(incoming_video)
        for key in ("size", "mtime_ns"):
            # Accept exact decimal browser strings, never rounded numeric matches.
            if incoming_video.get(key) == str(data["video"][key]):
                incoming_video[key] = data["video"][key]
    if incoming.get("schema") != SCHEMA or incoming_video != data["video"] or incoming.get("transcript_source") != data["transcript_source"]:
        raise ValueError("This correction file belongs to another source/review.")
    # Preserve a saved cover choice when importing a page made before that feature.
    previous = {c["id"]: c.get("thumbnail") for c in data["clips"]}
    for clip in incoming["clips"]:
        preference = clip.get("thumbnail", previous.get(clip["id"]))
        if preference is not None or "thumbnail" in clip:
            clip["thumbnail"] = thumbnail_request(preference)
    # Browser corrections cannot change paths, font bytes, approvals or source identity.
    for key in ("cues", "clips", "style", "layout"):
        data[key] = incoming[key]
    validate_cues(data["cues"], data["duration"])
    data["approval"] = None
    write(path, data)
    return page(path)


def wrap_text(text, font_path, size, width):
    from PIL import ImageFont
    if any(c in text for c in "\\{}"):
        raise ValueError("Caption contains ASS control characters (backslash/braces); review a literal-safe text version first.")
    font = ImageFont.truetype(str(font_path), round(size))
    lines = [""]
    for word in text.split():
        if font.getlength(word) > width:
            raise ValueError("A caption word is too wide; choose a smaller real-font size.")
        test = (lines[-1] + " " + word).strip()
        if font.getlength(test) > width:
            lines.append(word)
        else:
            lines[-1] = test
    if len(lines) > 2:
        raise ValueError("A subtitle cue needs more than two lines; split its text/times before approval.")
    return lines


def _ass_color(hex_color):
    return "&H00" + hex_color[5:7] + hex_color[3:5] + hex_color[1:3]


def _ass_time(sec):
    n = round(sec * 100)
    h, n = divmod(n, 360000)
    m, n = divmod(n, 6000)
    s, c = divmod(n, 100)
    return f"{h}:{m:02}:{s:02}.{c:02}"


def ass_text(cues, style, font, width=1080, height=1920):
    # Use a 1080-wide design space even for source-aspect output.
    margin = 580 if height > width else 60
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}
WrapStyle: 2
ScaledBorderAndShadow: yes
[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Caption,{font['family']},{style['size']},{_ass_color(style['color'])},{_ass_color(style['color'])},{_ass_color(style['outline_color'])},&H80000000,0,0,0,0,100,100,0,0,1,{style['outline']},0,2,70,70,{margin},1
[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = []
    for cue in cues:
        lines = wrap_text(cue["text"], font["path"], style["size"], width - 140)
        text = r"\N".join(lines)
        events.append(f"Dialogue: 0,{_ass_time(cue['start'])},{_ass_time(cue['end'])},Caption,,0,0,0,,{text}")
    return header + "\n".join(events) + "\n"


def _layout_filter(layout):
    if layout == "source":
        return "scale=trunc(iw/2)*2:trunc(ih/2)*2,setsar=1"
    if layout == "crop":
        return "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1"
    return ("split[bg][fg];[bg]scale=1080:1920:force_original_aspect_ratio=increase,"
            "crop=1080:1920,gblur=sigma=42,eq=brightness=-0.22[back];"
            "[fg]scale=1080:608:force_original_aspect_ratio=decrease,setsar=1[front];"
            "[back][front]overlay=(W-w)/2:430")


def _encode(args, cwd):
    return process([binary("ffmpeg"), "-hide_banner", "-loglevel", "error", "-nostdin", "-y",
                    "-threads", "2", "-filter_complex_threads", "1", "-filter_threads", "1", *args], cwd=str(cwd))


def verify_video(path, duration):
    info = probe(path)
    if abs(float(info["format"]["duration"]) - duration) > .15:
        raise ValueError("Encoded duration differs from the approved hook/body timeline.")
    if not any(s["codec_type"] == "audio" for s in info["streams"]):
        raise ValueError("Encoded clip lost audio")
    process([binary("ffmpeg"), "-v", "error", "-i", str(path), "-f", "null", "-"])


def render(path):
    data, root = load_review(path)
    validate_selection(data)
    signature = digest(payload(data))
    if (data.get("approval") or {}).get("signature") != signature:
        raise ValueError("Show the full timed transcript, hooks and styles; obtain fresh user approval before rendering.")
    output = root / "exports" / signature[:16]
    manifest = {"review_signature": signature, "clips": [], "complete": False, "visual_review_required": True}
    with worker(root):
        # Preserve earlier exports, including failed partial runs and user edits.
        version = 1
        while output.exists():
            version += 1
            output = root / "exports" / f"{signature[:16]}-{version}"
        output.mkdir(parents=True)
        font = validate_style(data) if any(c["captions"] for c in data["clips"]) else None
        if font:
            (output / "fonts").mkdir(exist_ok=True)
            shutil.copyfile(font["path"], output / "fonts" / (font["id"] + Path(font["path"]).suffix))
        for clip in data["clips"]:
            ranges = clip_ranges(clip, data["duration"])
            duration = sum(b - a for a, b in ranges)
            cues = retime_cues(data["cues"], ranges)
            base = output / clip["id"]
            save_formats(base, cues, {"clock": "clip timeline seconds", "complete": True,
                                     "review_signature": signature, "source_ranges": ranges})
            # Trim video AND audio through the same sequence, including moved hooks.
            graph, labels, inputs = [], [], []
            n = len(ranges)
            for i, (a, b) in enumerate(ranges):
                # Seek each bounded passage; avoid buffering an entire long episode
                # while concat waits for a hook that occurs later in the source.
                inputs += ["-threads", "2", "-ss", str(a), "-t", str(b - a), "-i", data["video"]["path"]]
                graph += [f"[{i}:v:0]setpts=PTS-STARTPTS,fps=30[v{i}]",
                          f"[{i}:a:0]asetpts=PTS-STARTPTS,aresample=48000[a{i}]"]
                labels.append(f"[v{i}][a{i}]")
            graph.append("".join(labels) + f"concat=n={n}:v=1:a=1[joined][audio]")
            graph.append("[joined]" + _layout_filter(data["layout"]) + "[video]")
            clean = output / (clip["id"] + "-clean.mp4")
            _encode([*inputs, "-filter_complex", ";".join(graph),
                     "-map", "[video]", "-map", "[audio]", "-c:v", "libx264", "-threads", "2", "-preset", "fast",
                     "-crf", "20", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
                     "-movflags", "+faststart", str(clean)], output)
            verify_video(clean, duration)
            entry = {"id": clip["id"], "duration": duration, "clean": str(clean),
                     "srt": str(base.with_suffix(".srt")), "ranges": ranges}
            if clip["captions"]:
                video_stream = next(s for s in probe(clean)["streams"] if s["codec_type"] == "video")
                h = round(1080 * video_stream["height"] / video_stream["width"])
                ass = base.with_suffix(".ass")
                ass.write_text(ass_text(cues, data["style"], font, 1080, h), encoding="utf-8")
                captioned = output / (clip["id"] + "-captioned.mp4")
                _encode(["-i", str(clean), "-vf", f"subtitles={ass.name}:fontsdir=fonts",
                         "-map", "0:v:0", "-map", "0:a:0", "-c:v", "libx264", "-threads", "2", "-preset", "fast",
                         "-crf", "20", "-pix_fmt", "yuv420p", "-c:a", "copy", "-movflags", "+faststart",
                         str(captioned)], output)
                verify_video(captioned, duration)
                entry["captioned"] = str(captioned)
            manifest["clips"].append(entry)
            write(output / "manifest.json", manifest)
        manifest["complete"] = True
        write(output / "manifest.json", manifest)
    return output / "manifest.json"


def page(path):
    from .clip_review import build_page
    data, root = load_review(path)
    result = root / "review.html"
    result.write_text(build_page(data), encoding="utf-8")
    save_formats(root / "full-transcript", data["cues"],
                 {"clock": "video seconds", "complete": True,
                  "reviewed": (data.get("approval") or {}).get("signature") == digest(payload(data))})
    return result
