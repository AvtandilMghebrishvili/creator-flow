---
name: podcut-flow
description: Guide local podcast editing from a user-selected episode folder in Codex or Claude. Use for synchronizing camera footage and external microphones, speaker-led cuts, real color-look choices, timestamped transcripts, and Premiere assembly or requested rendering. Handles missing camera/microphone mapping and single-camera mixed-audio ambiguity. Do not use for unrelated coding or generated presenter videos.
---

# Podcut Flow

Read [START_HERE.md](../../../START_HERE.md) in this repository and follow it as the canonical workflow. If this skill was copied separately, locate the repository; do not assume these relative resources still exist.

Ask for the episode's absolute source folder if it was not supplied. Reuse existing answers and saved `.podcut/` state. Ask only missing camera, microphone, color, language, boundaries and delivery questions. For a single wide camera and shared audio, ask left/right identity and timestamped speaker examples; do not claim independent voice isolation.

Use [setup](../../../docs/SETUP.md) for local dependencies and [workflow](../../../docs/WORKFLOW.md) for commands and project fields. Produce actual-frame color alternatives and honor the user's selection. Verify sync and drift before editorial decisions. Preserve distinct external microphones on separate lanes; exclude scratch audio from the final timeline.

Use [Premiere instructions](../../../docs/PREMIERE.md) for XML import or optional local MCP. XML alone is not a finished native project. Save/reopen/verify `.prproj`; never do a full render in Premiere-only mode. Deliver source and edited-clock transcripts. Describe actual verification and any remaining limitations honestly.
