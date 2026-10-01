# Working in Creator Flow

For **editing a user's podcast**, read START_HERE.md and the creator-flow skill. Ask for the episode folder if missing. Preserve choices and source media. Follow the user's requested delivery; Premiere-only work must not trigger a full video render.

**Transcription default: Meta Omnilingual ASR.** Use it for new source-clock transcripts and as the edited-clock baseline. Whisper/comparison is opt-in; see docs/TRANSCRIPTION.md. Preserve existing reviewed transcripts when resuming.

**Episode/clip review:** follow docs/CLIPS.md. Propose output count and duration as a question and wait for the user's choice before production. Show the complete timestamped transcript for correction/confirmation before assembly or caption burn-in. Ask captions on/off per video and offer original-file font/color styles; no generated fonts. Use a real spoken hook as an opening teaser and retain it later in the conversation (repeat by default). Obtain confirmation of the current text, cuts, hook and applicable style; changes invalidate that confirmation. These gates apply to episode production, not coding/setup/tests.

For **installing the workflow**, follow docs/SETUP.md and complete missing dependency/integration setup, reusing working tools. Installation alone does not require an episode folder. Do not stop at listing downloads when the user has asked you to perform setup.

For **developing this repository**, inspect relevant code, make the change, run meaningful tests with `python -m pytest`, and update affected documentation. Do not start episode intake for a coding task. Keep dependencies modest and processing local. Use synthetic media in tests. Do not add real recordings, transcripts, personal filesystem paths, local-auth files or secrets. Independent source lanes, stable timebases, stale-output rejection and honest delivery labels are required behavior.

Skill location: `.agents/skills/creator-flow/SKILL.md`. Detailed setup and implementation usage are under `docs/`.

Archive tools are bundled in `src/podcut/youtube/`; read `docs/ARCHIVE.md` for that route. Use the unified `creator-flow` command (`podcut` remains an alias). For archive/integration changes run `node --test tests/selection.test.mjs` as well as relevant Python tests. Preserve both original Git histories and attribution.

**Optional thumbnails:** offer episode and per-Short/Reel covers, preserving accepted/declined choices. Follow docs/THUMBNAILS.md: use the matching reviewed content, real identified guest/host photos on opposite sides, relevant generated topic visuals, and supplied or chosen headline/CTA text. A clip cover must reflect that clip. Missing references/tooling need explicit handling; a request is not a generated image. Keep receipts private and upload only on a separate request.
