---
name: creator-flow
description: Guide local podcast editing, reviewed Shorts and Reels, or YouTube archive research with Meta transcription, original-font captions, spoken teasers and Premiere or rendered delivery. Use for real-recording production and archive/channel analysis, not unrelated coding or generated presenter videos.
---

# Creator Flow for Claude Code

Read the canonical [START_HERE.md](../../../START_HERE.md) and [shared skill](../../../.agents/skills/creator-flow/SKILL.md), then follow that workflow. Resolve paths from this repository; if installed separately, first locate the repository checkout.

Use **Meta Omnilingual ASR by default** for transcription and the final-clock text baseline. The normal installer and `podcut transcribe PROJECT` use Meta alone. Whisper and dual comparison are opt-in; see [transcription](../../../docs/TRANSCRIPTION.md). Preserve existing reviewed transcripts when resuming.

For episode/Shorts work read [clip and subtitle review](../../../docs/CLIPS.md). Ask count/duration before production; show the complete timed transcript for user correction and confirmation before assembly; ask captions on/off and original-file font/color choices. Prepend an approved real spoken hook as a teaser and retain its later occurrence by default. Preserve clean video and editable subtitles. A changed text, hook, cut or style needs renewed confirmation.

Ask for the episode folder if absent, preserve the user's existing answers, and save state in that episode's `.podcut/`. Confirm speaker/camera/microphone mapping, color choice and final delivery. One shared audio recording cannot be relabeled as two isolated microphones. Premiere-only work must not render the complete video. Use [setup](../../../docs/SETUP.md), [workflow](../../../docs/WORKFLOW.md) and [Premiere guidance](../../../docs/PREMIERE.md) as needed.

Complete the installation as part of setup: reuse working tools, install missing dependencies with the repository installer, and install/configure a missing MCP/UXP plugin for requested Premiere automation. Check the resulting connection; do not stop at providing download links. User participation is only needed for a real blocked OS/account/interactive step.

For YouTube archive/channel research use [the bundled archive guide](../../../docs/ARCHIVE.md) and `creator-flow archive`. This code is already in the same repository; do not clone a second toolkit. Ask for the authorized archive source/workspace. New transcript generation still defaults to Meta, and all production review gates above apply. Use original archive metadata/hooks/strategy references only when relevant.
