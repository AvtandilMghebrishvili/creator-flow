# Creator Flow — Podcasts, Shorts & Reels

<img src="assets/creator-flow-logo.png" alt="Creator Flow — Podcasts, Shorts & Reels" width="760">

**One local workflow for podcasts, Shorts/Reels and YouTube archives, guided by Codex or Claude Code.** Podcut Flow and YOUTUBETECHCRUSH are consolidated in this repository, with both Git histories preserved. There is one installer, one agent entry point and no second checkout to manage.

## Start

Give a local agent this prompt:

```text
Use https://github.com/AvtandilMghebrishvili/creator-flow.
Read START_HERE.md and the creator-flow skill.
Episode folder: /absolute/path/to/episode
I want the episode, Shorts/Reels, or both. Ask me about count and duration.
Use Meta Omnilingual ASR by default and install missing tools.
Show the complete timed transcript for review before assembly.
Reuse answers I already gave you.
```

Put one episode's recordings in one folder, optionally with subfolders. If absent, the agent asks for the absolute path. For archive work give the chosen video/channel and a local workspace instead. A browser chat cannot read your drive merely from a GitHub link; use a local agent or accessible execution environment.

## The shared workflow

1. Identify files, cameras and microphones; install missing dependencies. With one camera/shared mix, ask left/right seating and timed speaker examples. Do not promise clean independent voice separation.
2. Ask whether to produce the full episode, clips or both. Propose counts and durations as questions; wait for the choice. Teaser time counts toward the total.
3. Verify synchronization and drift. If grading is wanted, offer looks from actual source frames and honor the selected version. Preserve independent external microphone lanes.
4. Generate new transcripts with **Meta Omnilingual ASR**, locally. Reuse existing reviewed transcripts; archive captions are an optional reviewed source. Show the **entire transcript with timecodes**, accept corrections and confirm the current version before assembly.
5. Choose captions on/off per video and real publisher/installed/user-supplied TTF/OTF fonts, color and size. Verify Georgian/English glyph coverage. Never use generated lettering as video subtitles.
6. Prepend the approved **real spoken passage** as an opening teaser, retaining its original later occurrence. Confirm text, cuts, hook and applicable style; changes invalidate approval.
7. Deliver clean video, optional captioned video and separate editable subtitles, or a saved/reopened/verified Premiere project. Premiere-only mode does not render the full episode. Publishing requires a separate explicit request.

The [root README diagram](../README.md#ფლოუ-ვიზუალურად) shows this flow. Read [START_HERE.md](../START_HERE.md) for agent intake and [CLIPS.md](CLIPS.md) for the local review page.

## Install once

```powershell
git clone https://github.com/AvtandilMghebrishvili/creator-flow.git
cd creator-flow
.\Install.ps1 -WithArchive
.\.venv\Scripts\creator-flow doctor
.\.venv\Scripts\creator-flow archive doctor
```

macOS/Linux: `python3 scripts/install.py --with-archive`. Omit the archive flag for local episode/clip work. The installer reuses working tools and sets up Python/FFmpeg/Meta in `.venv`; the optional archive route adds Node 22+ and yt-dlp. No npm installation is needed. Missing Premiere automation components are set up by the agent following [PREMIERE.md](PREMIERE.md). Adobe licensing/login and required interactive steps may still need the user.

Meta is the small **CTC 300M INT8 ONNX** model, about 365 MB, not the 7B/v2 system. Its weights download for the first sample. Whisper and dual comparison are opt-in. See [TRANSCRIPTION.md](TRANSCRIPTION.md) for exact models, licenses and approximate word timing limits.

## Tools and compatibility

| Route | Guide |
| --- | --- |
| Local cameras, sync, color, independent audio and editing | [WORKFLOW.md](WORKFLOW.md) |
| Reviewed Shorts/Reels, spoken teaser, original-font captions | [CLIPS.md](CLIPS.md) |
| Bundled archive fetching, channel summaries and candidates | [ARCHIVE.md](ARCHIVE.md) |
| Native Premiere delivery or exchange package | [PREMIERE.md](PREMIERE.md) |

`creator-flow` is the main command. Existing `podcut` commands, the Python distribution/module name and private `.podcut/` project state remain compatible. Existing checkout paths need not change. Archive code ships inside the same wheel and is tested with the Python code on Windows/Linux. Legacy karaoke rendering remains explicitly separate from the current approval-aware clip renderer.

The current clip renderer needs an **already exported local video and complete transcript matching its clock**. Raw archive `{t,ms}` JSON is not a final-clock transcript. In Premiere-only work use the user's export or assemble/verify editable clip sequences in Premiere; do not force a full episode render. XML is an exchange package, not a completed native `.prproj` until imported, saved and verified. Burned-in captions cannot be toggled off inside that MP4; preserve clean output and editable subtitles.

This is an agent-guided toolkit, with human review of text, sync, fonts and edit decisions. See [SETUP.md](SETUP.md), [LIMITATIONS.md](LIMITATIONS.md), [MIT license](../LICENSE) and [attribution](../THIRD_PARTY_NOTICES.md). No private recordings, transcripts, credentials, fonts or model weights are included in the repository.
