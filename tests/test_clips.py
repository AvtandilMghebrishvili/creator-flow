from pathlib import Path

import numpy as np
import pytest

from podcut import clips
from podcut.core import binary, ffmpeg, process, read, write


@pytest.fixture
def review(tmp_path, monkeypatch):
    video = tmp_path / "video.mp4"
    video.write_bytes(b"synthetic placeholder")
    transcript = tmp_path / "transcript.json"
    write(transcript, {"clock": "final timeline seconds", "complete": True,
                       "segments": [{"start": i, "end": i + .8, "text": f"Word {i}"} for i in range(6)]})
    monkeypatch.setattr(clips, "probe", lambda _: {"format": {"duration": "6"},
                                                   "streams": [{"codec_type": "video"}, {"codec_type": "audio"}]})
    return clips.init(video, transcript, tmp_path / "review", 1, 5, 8, "User chose one 5-8 second clip")


def select(path, captions=False):
    d = read(path)
    d["clips"] = [{"id": "one", "start": 0, "end": 6,
                   "hook": {"start": 2, "end": 3, "mode": "repeat"}, "captions": captions}]
    write(path, d)
    return d


def test_repeat_hook_retimes_text_and_leaves_original_passage():
    clip = {"start": 0, "end": 6, "hook": {"start": 2, "end": 3, "mode": "repeat"}}
    cues = [{"start": i, "end": i + .8, "text": str(i)} for i in range(6)]
    ranges = clips.clip_ranges(clip, 6)
    actual = clips.retime_cues(cues, ranges)
    assert ranges == [(2, 3), (0, 6)]
    assert [c["text"] for c in actual] == ["2", "0", "1", "2", "3", "4", "5"]
    assert [c["start"] for c in actual] == [0, 1, 2, 3, 4, 5, 6]
    clip["hook"]["mode"] = "move"
    assert [c["text"] for c in clips.retime_cues(cues, clips.clip_ranges(clip, 6))] == ["2", "0", "1", "3", "4", "5"]


def test_cutting_inside_a_cue_requires_timing_correction():
    with pytest.raises(ValueError, match="crosses a subtitle"):
        clips.retime_cues([{"start": 1, "end": 3, "text": "do not cut this"}], [(2, 4)])


def test_draft_or_changed_review_never_renders(review, monkeypatch):
    select(review)
    monkeypatch.setattr(clips, "_encode", lambda *a, **k: pytest.fail("Encoding must not start"))
    with pytest.raises(ValueError, match="fresh user approval"):
        clips.render(review)
    clips.approve(review, "User approved this complete transcript", "Checked matching video start/middle/end")
    d = read(review)
    d["cues"][0]["text"] = "A later correction"
    write(review, d)
    with pytest.raises(ValueError, match="fresh user approval"):
        clips.render(review)


def test_changed_scope_and_hook_duration_need_new_agreement(review):
    select(review)
    d = read(review)
    d["brief"]["max_seconds"] = 6
    write(review, d)
    with pytest.raises(ValueError, match="confirm the new brief"):
        clips.approve(review, "yes", "clock checked")
    clips.set_brief(review, 1, 5, 6, "User changed duration to 5-6")
    with pytest.raises(ValueError, match="including the opening hook"):
        clips.approve(review, "yes", "clock checked")


def test_complete_transcript_own_clock_and_valid_times_required():
    d = {"clock": "reference recording seconds", "complete": True, "segments": []}
    with pytest.raises(ValueError, match="Retime Meta"):
        clips.normalize_transcript(d, 10)
    d["clock"] = "final timeline seconds"
    d["complete"] = False
    with pytest.raises(ValueError, match="partial ASR"):
        clips.normalize_transcript(d, 10)
    with pytest.raises(ValueError, match="finite"):
        clips.validate_cues([{"start": 0, "end": float("nan"), "text": "bad"}], 10)
    with pytest.raises(ValueError, match="non-overlapping"):
        clips.validate_cues([{"start": 0, "end": 2, "text": "a"}, {"start": 1, "end": 3, "text": "b"}], 10)


def test_corrected_segment_text_is_not_replaced_by_stale_words():
    data = {"clock": "final timeline seconds", "complete": True, "segments": [
        {"start": 0, "end": 1, "text": "correct name", "words": [
            {"start": 0, "end": .8, "word": "wrong"}]}]}
    assert clips.normalize_transcript(data, 2)[0]["text"] == "correct name"


def test_review_corrections_invalidate_approval_and_cannot_change_sources(review, tmp_path):
    select(review)
    clips.approve(review, "User approved", "Checked the matching video")
    incoming = read(review)
    incoming["cues"][0]["text"] = "Corrected"
    edited = tmp_path / "edits.json"
    write(edited, incoming)
    clips.import_review(review, edited)
    assert read(review)["approval"] is None
    assert read(review)["cues"][0]["text"] == "Corrected"
    incoming["video"]["path"] = "/another/video"
    write(edited, incoming)
    with pytest.raises(ValueError, match="another source"):
        clips.import_review(review, edited)


def test_full_review_page_escapes_transcript_as_data(review):
    d = read(review)
    d["cues"][0]["text"] = '</script><script>alert("no")</script>'
    write(review, d)
    html = clips.page(review).read_text(encoding="utf-8")
    assert '</script><script>alert' not in html
    assert "Word 5" in html  # Entire transcript, not just selected clips.
    assert read(review.parent / "full-transcript.json")["segments"][0]["text"] == d["cues"][0]["text"]


def test_georgian_shortlisting_and_no_duplicate_windows(review):
    cues = [{"start": i, "end": i + .8, "text": "პირველად შეცდომა"} for i in range(6)]
    scored = clips.candidates(cues, 2, 4)
    assert scored[0]["score"] > 0
    assert "story" in scored[0]["signals"]
    clips.propose(review)
    assert read(review)["clips"][0]["hook"] is None
    with pytest.raises(ValueError, match="Existing selections preserved"):
        clips.propose(review)


def test_caption_choice_is_required_even_without_font(review):
    d = select(review)
    d["clips"][0]["captions"] = None
    write(review, d)
    with pytest.raises(ValueError, match="on or off"):
        clips.approve(review, "yes", "matched")


def test_changed_source_blocks_reuse(review):
    d = select(review)
    Path(d["video"]["path"]).write_bytes(b"changed video")
    with pytest.raises(ValueError, match="Video changed"):
        clips.page(review)


def real_font():
    for path in ["C:/Windows/Fonts/arial.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                 "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf"]:
        if Path(path).is_file():
            return Path(path)
    pytest.skip("No installed original test font")


def test_real_font_glyph_validation_and_font_change_invalidate(review, tmp_path):
    font = tmp_path / "original.ttf"
    font.write_bytes(real_font().read_bytes())
    clips.add_font(review, font, "Installed original font, local test only")
    d = select(review, captions=True)
    d["style"]["font_id"] = d["fonts"][0]["id"]
    write(review, d)
    clips.approve(review, "Approved real font", "Clock verified")
    d["cues"][0]["text"] = "\U00020000"
    with pytest.raises(ValueError, match="lacks transcript"):
        clips.validate_style(d)
    font.write_bytes(font.read_bytes() + b"changed")
    with pytest.raises(ValueError, match="unchanged original font"):
        clips.validate_style(read(review))


def test_actual_render_repeats_hook_video_audio_and_captions(tmp_path):
    video = tmp_path / "original.mp4"
    # Red/440 Hz first; blue/880 Hz second. The hook comes from the blue section.
    ffmpeg(["-f", "lavfi", "-i", "color=red:s=320x180:r=30:d=2", "-f", "lavfi", "-i",
            "color=blue:s=320x180:r=30:d=4", "-f", "lavfi", "-i",
            "aevalsrc=0.2*sin(2*PI*if(lt(t\\,2)\\,440\\,880)*t):s=48000:d=6",
            "-filter_complex", "[0:v][1:v]concat=n=2:v=1:a=0[v]", "-map", "[v]", "-map", "2:a",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-y", str(video)])
    transcript = tmp_path / "meta-final.json"
    write(transcript, {"clock": "final timeline seconds", "complete": True,
                       "segments": [{"start": i, "end": i + .8, "text": f"word {i}"} for i in range(6)]})
    path = clips.init(video, transcript, tmp_path / "review", 1, 6, 8, "One 6-8s video confirmed")
    clips.add_font(path, real_font(), "Original installed font, not redistributed")
    d = select(path, captions=True)
    d["style"]["font_id"] = d["fonts"][0]["id"]
    d["layout"] = "source"
    write(path, d)
    clips.approve(path, "Synthetic approved review", "Synthetic clock matches by construction")
    manifest = read(clips.render(path))
    entry = manifest["clips"][0]
    assert Path(entry["clean"]).is_file() and Path(entry["captioned"]).is_file()
    assert entry["duration"] == 7
    assert [s["text"] for s in read(Path(entry["srt"]).with_suffix(".json"))["segments"]] == [
        "word 2", "word 0", "word 1", "word 2", "word 3", "word 4", "word 5"]
    for t, expected_blue in [(.2, True), (1.2, False), (3.2, True)]:
        raw = process([binary("ffmpeg"), "-v", "error", "-ss", str(t), "-i", entry["clean"],
                       "-frames:v", "1", "-vf", "scale=1:1", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]).stdout
        r, g, b = raw[:3]
        assert (b > r) == expected_blue
        audio = process([binary("ffmpeg"), "-v", "error", "-ss", str(t), "-i", entry["clean"],
                         "-t", "0.25", "-vn", "-ar", "16000", "-ac", "1", "-f", "f32le", "-"]).stdout
        samples = np.frombuffer(audio, dtype="<f4")
        freq = np.argmax(abs(np.fft.rfft(samples))) * 16000 / len(samples)
        assert abs(freq - (880 if expected_blue else 440)) < 10
    assert "subtitles" not in entry["clean"]


def test_thumbnail_choices_roundtrip_without_becoming_image_approval(review, tmp_path):
    select(review)
    clips.approve(review, "Approved video", "Checked video clock")
    incoming = read(review)
    incoming['clips'][0]['thumbnail'] = {
        'requested': True, 'text': 'ჩემი სათაური | exact copy',
        'approved': True, 'output': '/not-a-generated-image.png'}
    edited = tmp_path/'corrections.json'
    write(edited, incoming)
    clips.import_review(review, edited)
    saved = read(review)
    assert saved['clips'][0]['thumbnail'] == {'requested': True, 'text': 'ჩემი სათაური | exact copy'}
    assert saved['approval'] is None
    # An older correction page must not erase the saved yes/no answer or copy.
    incoming['clips'][0].pop('thumbnail')
    write(edited, incoming)
    clips.import_review(review, edited)
    assert read(review)['clips'][0]['thumbnail'] == saved['clips'][0]['thumbnail']


@pytest.mark.parametrize('value', [None, {'requested': 'yes'}, {'requested': 1}, {'requested': False, 'text': []}])
def test_invalid_thumbnail_request_is_not_written(review, tmp_path, value):
    select(review)
    original = review.read_bytes()
    incoming = read(review)
    incoming['clips'][0]['thumbnail'] = value
    edited = tmp_path/'invalid.json'
    write(edited, incoming)
    with pytest.raises(ValueError, match='Thumbnail'):
        clips.import_review(review, edited)
    assert review.read_bytes() == original


@pytest.mark.parametrize('requested', [None, False, True])
def test_optional_thumbnail_request_does_not_block_video_approval(review, requested):
    data = select(review)
    data['clips'][0]['thumbnail'] = {'requested': requested, 'text': ''}
    write(review, data)
    clips.approve(review, 'Approved video, cover handled separately', 'Video clock checked')
    assert read(review)['approval']['signature']


def test_browser_fingerprint_keeps_exact_nanoseconds_and_rejects_a_changed_stamp(review, tmp_path):
    import json
    import re
    select(review)
    before = read(review)
    html = clips.page(review).read_text(encoding='utf-8')
    browser = json.loads(re.search(r'<script id="data" type="application/json">(.*?)</script>', html, re.S).group(1))
    for key in ('size', 'mtime_ns'):
        assert browser['video'][key] == str(before['video'][key])
    edited = tmp_path/'browser.json'
    write(edited, browser)
    clips.import_review(review, edited)
    assert read(review)['video'] == before['video']
    browser['video']['mtime_ns'] = str(before['video']['mtime_ns'] + 1)
    write(edited, browser)
    with pytest.raises(ValueError, match='another source'):
        clips.import_review(review, edited)
