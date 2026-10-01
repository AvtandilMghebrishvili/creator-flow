# Agent entry point: Creator Flow

Use this workflow when the user wants an episode edited. When asked to maintain this repository's code, follow AGENTS.md instead of starting episode intake. Talk in the user's language. This is a guided local workflow, not a promise that a link alone controls their computer.

For an installation-only request, complete docs/SETUP.md first; an episode folder is not required to install the tools. Start the source-folder and role questions when editing an episode begins.

For a user-facing walkthrough, offer [ქართული](docs/USER_GUIDE.ka.md) or [English](docs/USER_GUIDE.en.md). The visual HTML contains copyable setup/podcast/Shorts/Reels prompts. For personal skill registration use docs/SETUP.md; dependency installation alone does not register a skill for unrelated folders.

## Choose the source route

This single repository includes local episode editing, reviewed Shorts/Reels and YouTube archive research. Use [docs/ARCHIVE.md](docs/ARCHIVE.md) for an existing archive/channel; ask for the authorized source and workspace instead of inventing a local raw-recording folder. Use the local intake below for camera/audio recordings. The count/duration, full transcript, real fonts and spoken-teaser confirmations apply to either production route. New transcription defaults to Meta. Do not install another archive repository or bypass the current review route with the legacy renderer.

## 1. Establish the episode and access

Ask for the **absolute episode folder path** if absent. Explain that videos and audio should be placed in that folder; subfolders are supported. Never use the current directory, previous episode, or an old example as an implicit source folder. Confirm local filesystem/tool access. A browser-only chat cannot inspect a user's drive: explain how to use local Codex/Claude Code or an accessible execution environment, without pretending access.

Read docs/SETUP.md. **Own the installation, not just the instructions:** when the user asks to set up/use this workflow, inspect this computer and install the missing dependencies needed for the chosen route. Explain what you are installing in a short progress update and proceed within that authorization; do not repeatedly ask the user to install ordinary free prerequisites themselves. Use `Install.ps1` on Windows or `python3 scripts/install.py` on macOS/Linux, then `podcut doctor`. The default installer includes the local transcription library. It reuses working tools and installs project packages inside `.venv`. If no Python/package manager is available, install the needed runtime through the OS/vendor's official method first. Follow up on failures; don't report success from an installer exit code alone.

Download the chosen speech model when needed for the first sample, reusing a compatible cached model if available. For requested Premiere automation, inspect the existing connection first; if missing/broken, install and configure the required upstream MCP/UXP plugin and its runtime using docs/PREMIERE.md, preserving other integrations. XML-only import and rendered delivery do not need that plugin. Do not install unrelated plugins, another AI client, GPU tooling or commercial software just because an installer exists. Adobe licensing/login, OS administrator prompts, and mandatory interactive plugin loading may need the user's participation: complete the independent setup first, explain the exact remaining action, and continue afterward. Never buy a license or bypass a permissions prompt.

Inspect existing `.podcut/project.json` and `WORK_STATUS.md` and resume if present. Otherwise run `podcut init FOLDER`. Inventory errors are meaningful: report unsupported sources, do not silently omit a camera. Work in `.podcut/`; never overwrite or delete originals. Before heavy work check available disk space, run one heavy worker, keep FFmpeg/ASR CPU use modest, and make recoverable checkpoints.

## 2. Ask only what is missing

Use `podcut questions PROJECT` as a checklist, not a script to repeat verbatim. Existing user answers and authorizations persist. Group related questions into a short intake:

- Which files show the guest, host(s), and optional wide? A role can have sequential parts. Ask about gaps and file order when unclear. Show filenames and actual stills; do not infer identity from appearance.
- Which recordings/channels contain each microphone? Are they isolated microphones, a stereo split, a shared mix, or camera scratch audio? Confirm channel numbers and listen to samples. Prefer an uninterrupted external audio recording as the common clock.
- Who are the speakers; how are names spelled; what language(s) are spoken?
- Are colors already finished? Keep them or prepare color options? Ask the actual recording profile/gamut if unknown; camera model or a BT.709 tag is insufficient to identify log.
- What should be kept? Default to the requested greeting/introduction through farewell, preserving the conversation. Clarify ambiguity after listening to candidate boundaries.
- Deliver a rendered video or an editable Premiere project for user review/render? Ask whether Premiere is installed and its OS/version if relevant. Offer both only when useful; never infer permission to render from permission to assemble in Premiere.

If **one camera + one mixed audio**: explicitly explain that speaker attribution and clean isolation are less reliable. Ask who is on the left/right and let the user identify speakers in two or three actual timestamped samples. Record `layout` and `speaker_examples`. Keep a shared audio lane if that is the available recording; do not label duplicated copies as isolated microphones. Preserve the full frame unless the user requests digital crops and resolution supports them. Never invent missing camera angles.

Record answers in `project.json` and a short `.podcut/brief.md`. Use named roles such as `guest`, `host`, `host2`, `wide`; file IDs remain stable. A split multichannel file can have separate source entries with unique IDs and explicit zero-based channels. Set `mapping_confirmed` only after roles are established. See docs/WORKFLOW.md for the schema.

Offer optional episode/Shorts/Reels thumbnails alongside the output choice. Reuse an existing answer and save `decisions.thumbnail_requested` plus the chosen output IDs in the private thumbnail brief. Follow [docs/THUMBNAILS.md](docs/THUMBNAILS.md); the offer is not permission to generate or upload.

Before episode processing, ask whether the output is a full episode, clips or both. Propose the count and duration as a question and wait for the user's choice; include the opening teaser in the proposed duration. Reuse answers already given. Read-only inventory/setup may continue while waiting. See docs/CLIPS.md for the complete review and subtitle workflow.

## 3. Color choice before committing the edit

If color is requested: confirm source profiles, obtain any necessary manufacturer conversion LUT locally, and set per-camera exposure/white-balance corrections. Choose representative face/exposure frames from **each camera**, including later lighting conditions. Run `podcut colors PROJECT`; visually inspect the generated comparisons before showing them.

Show the actual Natural, Warm and Contrast comparisons and ask which to use. These are starting looks; iterate camera matching if needed. Do not present generic generated images as the episode's color samples. Run `approve-color` only after the user's choice. If they already chose a version in this episode, honor it. If they requested original/already-graded footage, record `original` without double grading. Sync/inventory can proceed while awaiting a color answer, but don't commit a final edit/render that assumes an unanswered choice.

## 4. Synchronize and transcribe

Follow docs/WORKFLOW.md. Use scratch audio to propose sync; it is analysis-only unless the user explicitly elects camera audio as the sole available source. Estimate offset **and clock drift**, independently for each camera part/microphone. Inspect matches near the start, middle and end and check lip sync. Low confidence, silent cameras, discontinuities or implausible drift need manual anchors or user help. A successful command is not proof of synchronization. Record verification evidence before `verify-sync`.

Use **Meta Omnilingual ASR alone by default**, following docs/TRANSCRIPTION.md. The standard installer includes its libraries; reuse cached weights or download the pinned model for the first sample. Make a short sample in the specified language, listen and review, then transcribe the full episode with Meta. Preserve source-clock TXT/SRT/VTT/JSON. Meta is the editable baseline for final-clock retiming, including when optional comparison is requested. This is the small CTC 300M INT8 ONNX model, not 7B or v2; word boundaries are approximate. Only install/run Whisper when the user chooses comparison (`--with-whisper` setup, `--engine both`) or Whisper alone (`--engine whisper`). Comparison runs sequentially and preserves both drafts and comparison HTML/JSON; never automatically merge words or treat agreement as accuracy. Failures must be reported, not silently switched to another engine. Explain required downloads; never send private recordings to an external transcription API without authorization. Correct names, meaning and boundaries by listening. Do not fabricate transcripts when a model is absent/unusable.

## 5. Edit and preserve independent sound

**User transcript review precedes assembly:** show the complete Meta transcript with timestamps, accept corrections, and get confirmation of the current text/times. Ask captions on/off per video and offer real original-font/color/size samples or accept a supplied font file. Never use generated lettering. For each requested teaser, propose a real spoken passage and show its timecodes; place it first and retain it later in the conversation by default. Show resulting duration/order and wait for approval of the clips, hook and applicable style. Correcting text alone is not approval. Keep corrections separate from the original ASR draft. See docs/CLIPS.md for the local review page and approval-aware renderer.

Locate the opening greeting/introduction and closing farewell. Record precise reference-clock `bounds`; use explicit keep intervals for agreed removals. Preserve speech and natural pauses. Avoid aggressive silence removal, guessed filler deletions or jump cuts within words.

Create a proposed plan. Distinct mic dominance can suggest speaker turns; bleed/overlap means those suggestions need review. With shared audio, review timestamped turns manually or use an explicitly chosen static camera. Apply a calm interview rhythm; the helper's 38-second close / 7-second wide pattern is only a starting point. Review interruptions, reactions, long answers, every file boundary and any camera dropout. Fall back to available wide coverage; never extend a missing camera into black.

Keep each camera role on a separate video lane, external guest/host microphones on separate audio lanes, and no scratch-camera audio in the final timeline. If only one mixed recording exists, keep one honestly named mix lane. Clean gently, align on one clock, and normalize the **combined** mix while preserving independent stems. Avoid gates that cut word tails and processors that introduce uncorrected delay.

Review the plan and validate coverage, source ranges, frame counts, small residual drift and the intended boundaries before approving it. The user requested confirmation of count/duration, the full transcript, hook/cut choices and caption styling; do not replace those confirmations with agent self-review. Prepare audio and retime the transcript into the edited timeline, including repeated teaser ranges. Preserve both source and final timestamp versions. Any change to confirmed text/timing/order/style requires confirmation of the affected revised version before assembly.

## 6. Optional thumbnails from the actual conversation

Follow [docs/THUMBNAILS.md](docs/THUMBNAILS.md) for accepted cover requests. Use the full reviewed episode for its thumbnail, and only the relevant selected passage/hook for a Short or Reel. Start with the real guest photo on the left and real host photo on the right, honor alternatives, and generate surrounding visual elements based on the topic. Missing photos need supplied portraits or identified, approved frames from the recording. Do not invent a replacement participant.

Use the user's exact headline/CTA or offer concise content-based options. Honor an existing selection or delegated choice, show actual draft images, and inspect identity, wording and readability. Use an available image tool; CLI thumbnail choices do not themselves generate artwork. Save the private brief, source/range evidence and selected output files. This stage does not require rendering the full episode in Premiere-only mode, and it does not authorize publishing.

## 7. Deliver the requested format

- **Premiere:** follow docs/PREMIERE.md. Offer XML import as the simpler connection-free path, or help install/configure the upstream local MCP when automation is desired. Import originals, separate stems, and apply each approved camera LUT once. Save a new native `.prproj`, reopen it, and verify media links, sequence, cuts, colors, audio routing, playback and duration. Do not render the complete video. If app access is unavailable, supply the XML/LUT/stem package and exact remaining steps, and call it an exchange package—not a completed Premiere project.
- **Render:** `podcut render PROJECT` only when selected. Inspect the final encoded file, including start/middle/end audio sync, actual colors and camera transitions. The helper checks duration, decodability, loudness/true peak and sampled audio alignment; it cannot certify editorial taste or lip sync.

Deliver timestamped transcripts, the project/video, requested and inspected thumbnails mapped to their episode/clips, and a short plain-language handoff with verified facts, remaining uncertainty and relevant absolute paths. Keep receipts in `.podcut/`. Do not declare full completion when transcripts, color application, native reopening or requested review are still missing. Resuming must validate source/config signatures and reuse only valid completed work. Never put episode media, transcripts, credentials or local MCP configuration into the public repository.
