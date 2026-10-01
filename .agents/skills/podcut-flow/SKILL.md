---
name: podcut-flow
description: Guide local podcast and clip editing in Codex or Claude with Meta Omnilingual ASR, synchronization, colors, full transcript review, original-font captions and spoken opening teasers. Use for episode/Shorts preparation, Premiere assembly or requested rendering from local recordings. Handles source mapping and shared-audio ambiguity. Do not use for unrelated coding or generated presenter videos.
---

# Podcut Flow

Read [START_HERE.md](../../../START_HERE.md) in this repository and follow it as the canonical workflow. If this skill was copied separately, locate the repository; do not assume these relative resources still exist.

Use **Meta Omnilingual ASR by default** for transcription and as the final-clock text baseline. The normal installer and `podcut transcribe PROJECT` use Meta alone. Whisper and dual comparison are opt-in. See [transcription](../../../docs/TRANSCRIPTION.md) for setup, sampling and timing review; preserve existing reviewed transcripts when resuming.

Ask for the episode's absolute source folder if it was not supplied. Reuse existing answers and saved `.podcut/` state. Ask only missing camera, microphone, color, language, boundaries and delivery questions. For a single wide camera and shared audio, ask left/right identity and timestamped speaker examples; do not claim independent voice isolation.

Use [setup](../../../docs/SETUP.md) for local dependencies and [workflow](../../../docs/WORKFLOW.md) for commands and project fields. Produce actual-frame color alternatives and honor the user's selection. Verify sync and drift before editorial decisions. Preserve distinct external microphones on separate lanes; exclude scratch audio from the final timeline.

Follow [clip and subtitle review](../../../docs/CLIPS.md): ask whether the user wants the episode, clips or both; propose count and total durations as questions and wait before production. Show the full Meta transcript with timecodes for correction and explicit confirmation before assembly/caption burn-in. Ask captions on/off per video, and offer actual original-font/color samples or accept the user's font file. The hook is an approved real spoken passage prepended as a teaser and repeated in the later conversation by default. Confirm final text, ranges, hook and applicable style, preserving the clean video and separate editable subtitles. Changes require a new confirmation of the affected current version.

Own dependency setup: inspect/reuse existing tools, run the repository installer for missing requirements, and install/configure a missing Premiere MCP/plugin when automated native assembly is selected. Verify imports, executables and the app connection. Ask for user participation only at an actual interactive/permission/account step; ordinary dependency installs are part of setting up the requested workflow.

Use [Premiere instructions](../../../docs/PREMIERE.md) for XML import or optional local MCP. XML alone is not a finished native project. Save/reopen/verify `.prproj`; never do a full render in Premiere-only mode. Deliver source and edited-clock transcripts. Describe actual verification and any remaining limitations honestly.
