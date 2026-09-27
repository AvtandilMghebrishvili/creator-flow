# Command guide and project contract

Read [START_HERE.md](../START_HERE.md) for the conversation and editorial workflow. Commands below run locally and never replace inspection/listening. Paths named `PROJECT` refer to `EPISODE/.podcut/project.json`; replace placeholders with actual paths and quote paths containing spaces.

## Inventory and decisions

```sh
podcut doctor
podcut init "ABSOLUTE_EPISODE_FOLDER"
podcut questions "PROJECT"
podcut status "PROJECT"
```

The generated manifest stores actual probe data, source fingerprints and stable IDs. Edit its fields rather than constructing probe metadata by hand. Mark chosen sources `use: true`; unused sources stay false. A camera's `role` is `guest`, `host`, `host2`, `wide`, or another confirmed role. Several sequential files may share a role. A microphone source has its confirmed speaker/mix role. `reference_id` names a selected recording with usable audio; choose continuous external audio when possible.

Important fields (fragments, not a complete runnable manifest):

```json
{
  "reference_id": "s04",
  "speakers": [{"id": "guest", "name": "Guest name"}, {"id": "host", "name": "Host name"}],
  "timeline": {"fps": "25/1", "width": 1920, "height": 1080},
  "audio": {"tracks": [{"source_id": "s04", "speaker": "guest"}, {"source_id": "s05", "speaker": "host"}]},
  "decisions": {"mapping_confirmed": true, "language": "ka", "color_requested": true, "delivery": "premiere"},
  "layout": {"confirmed": true, "left": "guest", "right": "host"},
  "speaker_examples": [{"reference": 18.2, "speaker": "host"}, {"reference": 42.1, "speaker": "guest"}],
  "bounds": [16.28, 3610.64]
}
```

All time values are **seconds**, unless a field explicitly says frames. `bounds` and editorial turns use the common reference clock. Source-local times are a different clock. Do not infer seating from this example.

For a stereo recorder with guest left / host right, duplicate its source entry with a new unique ID, preserving its path/fingerprint/probe; set one entry's `channel: 0`, the other's `channel: 1`. `audio_stream` is the zero-based audio-stream index; `channel` is zero-based within that stream. A null channel downmixes, so never leave it null when microphones are split across channels. List the two IDs separately in `audio.tracks`. Listen to establish channel identity. A real shared mono mix remains one `speaker: "mix"` track. Sequential mic-file assembly and discontinuous reference clocks need manual preparation before this v1 helper pipeline; never duplicate missing coverage.

Choose timeline FPS from the intended delivery; integer and standard NTSC rates such as `30000/1001` are supported. Do not reinterpret 50/60-fps recordings as slow motion merely because the timeline is 25/30 fps. Mixed resolutions are fit inside the delivery frame; verify framing in Premiere. HDR, anamorphic, interlaced, variable-frame-rate and RAW workflows may require deliberate conversion first.

## Sync: offset and drift

```sh
podcut sync "PROJECT"
```

For each usable audio source, spectral matching proposes several separated anchors and refines them with waveform correlation. The stored model is:

```text
source_seconds = offset + rate * reference_seconds
```

A later-starting source can have a negative offset. `rate` near one accounts for clock drift, not a creative speed change. Inspect each result; low peak separation, weak correlation, high residuals or extreme drift require attention. The reference itself is `{offset: 0, rate: 1}`. Verify start, middle and end against the actual recording, including mouth movements. Never set verified merely to bypass a guard.

For manual synchronization, save at least two widely separated matching moments, preferably three or more:

```json
[{"reference": 10, "source": 7.5}, {"reference": 610, "source": 607.53}, {"reference": 1210, "source": 1207.56}]
```

```sh
podcut sync-anchors "PROJECT" s02 "anchors.json"
podcut verify-sync "PROJECT" s02 --note "Checked clap and lip-sync near start, middle and end; evidence in sync-review.md."
```

Anchor verification is per file/channel. A single linear model cannot repair recording interruptions. Split a discontinuous source into continuous parts or prepare a documented corrected source, then re-inventory. Camera scratch audio is used for sync only; final audio is controlled by `audio.tracks`.

## Real color alternatives

For each selected camera set `color_space` to confirmed `rec709` or `log`. For log, set `input_lut` to a locally obtained correct manufacturer log/gamut-to-Rec.709 **3D CUBE**. Unsupported LUT domains/1D shapers must be converted using a color tool. A metadata tag alone is not enough. Optional per-camera fields:

```json
{"color_correction": {"exposure": 0.1, "balance": [1.01, 1.0, 0.99]}, "review_times": [120, 1800]}
```

These values are examples, not universal camera corrections. Match skin, neutral objects and exposure across cameras by inspecting actual frames. `review_times` are in that source's clock.

```sh
podcut colors "PROJECT"
podcut approve-color "PROJECT" natural
```

`colors` creates per-camera LUTs and comparison JPGs containing original, natural, warm and contrast. Show all cameras to the user; approve only their selection. If footage is already finished and the user wants it preserved, use `approve-color PROJECT original`. Changed inputs/corrections need new previews and a new choice. These modest starting looks do not perform automatic shot-by-shot professional color matching.

## Transcription and episode boundaries

Install the optional recognizer as described in SETUP.md. Run and evaluate a short sample, then the full reference-clock transcript:

```sh
podcut transcribe "PROJECT" --model small --language ka
```

Full runs have `complete: true`; partial samples do not count as full delivery. ASR runs in resumable chunks and records word timings when available. JSON, TXT, SRT and VTT remain labeled as drafts. Correct names and unclear passages by listening. Find the greeting/introduction and farewell in the recording and set `bounds`. When the user supplies more complex cuts, save chronological or deliberately reordered keep intervals as `[[start,end], ...]`; see `examples/keeps.json`.

## Plan and editorial review

```sh
podcut plan "PROJECT"
```

Distinct microphone recordings can propose speaker turns using relative speech energy. Bleed, unequal gains and interruptions can mislead it. The default cadence is up to 38 seconds on a close angle followed by 7 seconds of wide if available. Treat this as a candidate edit to review, not an editorial decision engine. It uses verified source coverage and falls back to wide near a camera's end. With only one camera, consecutive planning chunks stay on that camera and are not new angles.

With a shared mix and multiple cameras, supply reviewed turns covering the kept intervals, or explicitly select a static camera:

```sh
podcut plan "PROJECT" --turns "turns.json" --keeps "keeps.json"
podcut plan "PROJECT" --static-camera s01
```

Turns format: `[{"start": 16.28, "end": 45.6, "speaker": "host"}, ...]`. Times use the reference clock. See examples. Review file boundaries, speaker transitions, opening/closing and source availability; revise the turns/keeps then rebuild. The plan uses frame-aligned source in/out positions. Mid-shot clock fitting limits residual drift without changing video speed; if error exceeds one timeline frame, the validator rejects it and the agent must use shorter shots or a documented media correction.

```sh
podcut validate "PROJECT"
podcut approve-plan "PROJECT" --note "Reviewed speaker turns, greeting/farewell, camera coverage and all boundary transitions."
podcut audio "PROJECT"
podcut retime-transcript "PROJECT"
```

Plan approval records actual agent/user review, not necessarily a new permission question. Changed source, sync, color, bounds or audio configuration invalidates the plan. Rebuild/review downstream assets after relevant changes.

## Audio and delivery

Audio preparation high-passes gently, applies mild compression, resamples each mic onto the same clock and concatenates the kept intervals. It preserves independent mono stems, applies a common mix-level normalization and linked limiter, and measures the combined output. Default target is about -18 LUFS, with a conservative true-peak ceiling. This is a stereo podcast default, not a universal platform requirement. It does not claim voice isolation, advanced denoising, automatic perfect bleed removal or editorial silence trimming.

```sh
podcut xml "PROJECT"
```

For Premiere, follow [PREMIERE.md](PREMIERE.md). XML uses original footage, separate camera roles and audio lanes. Its `color_handoff.json` identifies the approved LUT for each clip prefix. Native color application, save/reopen and audio routing checks are still necessary.

```sh
podcut render "PROJECT"
```

Rendering is gated to `delivery: "render"` or `"both"`. The current encoder produces a Rec.709 H.264 MP4, AAC stereo, with the original footage cut and chosen LUTs applied. It caches completed shot intermediates, validates frame counts, decodes the result, measures encoded loudness/peak, and checks sampled audio against the stems. If a final file already exists it refuses to overwrite it. Review the actual output before delivery; numerical success alone is not an editorial review.

## Handoff contents

| Location inside `.podcut/` | Purpose |
| --- | --- |
| `project.json`, `brief.md`, `WORK_STATUS.md` | Decisions, verified source mappings and resume context |
| `audio/analysis_*`, `sync` inside project | Scratch audio and clock evidence |
| `color/`, `color_options.json` | Actual-frame comparisons and approved LUTs |
| `edit_plan.json` | Cuts, source/timebase mapping and review status |
| `audio/`, `audio_stems.json` | Separate aligned microphone stems and loudness checks |
| `transcripts/`, `transcript_latest.json` | Reference-clock and edited-clock transcript formats |
| `exchange/` | Premiere XML and color handoff |
| `exports/` | Requested rendered video and encoded validation report |

Output folders are versioned by input/plan signatures. Keep the original media, stems, LUTs and native project together or deliberately collect/relink them in Premiere before moving to another machine. Supply user-facing files and a concise handoff, not just internal logs.
