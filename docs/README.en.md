# Podcut Flow

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/podcut-logo-dark.png">
  <img src="assets/podcut-logo.png" alt="Podcut Flow cut-microphone logo" width="560">
</picture>

A reusable local podcast-editing workflow for Codex and Claude Code, with **Meta Omnilingual ASR as the default local transcription engine**, synchronization, color previews, separate microphone stems, timestamped transcripts, Premiere exchange and optional rendering. Whisper is an optional comparison tool.

## The workflow at a glance

**Episode → reviewed clips:** agree count and duration first, then review/correct the entire timed Meta transcript before assembly. Choose captions on/off per video and original-file font/color/size variants. An approved spoken passage plays as an opening teaser and remains in the later conversation. The local review page exports corrections; the renderer requires current approval and preserves a clean video plus separate subtitles. See [clips and caption review](CLIPS.md). This adapts the local Shorts workflow from [YOUTUBETECHCRUSH](https://github.com/AvtandilMghebrishvili/YOUTUBETECHCRUSH).

[![Six steps from episode files through default Meta Omnilingual ASR transcription to a Premiere project or rendered video](assets/podcut-workflow-guide.png)](assets/podcut-workflow-guide.png)

1. Put one episode's video and audio in one folder.
2. Give local Codex/Claude Code this repository link and the folder path.
3. Let the agent install missing tools and confirm each camera/microphone's role.
4. Verify synchronization and choose a look from your actual footage if grading is wanted.
5. Review the edit and default Meta Omnilingual ASR transcript; recognition runs locally and independent microphones stay on separate tracks.
6. Choose a native Premiere project for your review/render, or a rendered video.

This is an illustrated example, not a product screenshot or real color preview. A wide camera and isolated microphones are optional; the agent adapts to the files you actually have. [Logo assets and generation notes](assets/README.md).

## Local transcription with Meta

Transcription defaults to **Meta Omnilingual ASR only**. Its timestamped draft is the baseline for retiming into the edit. The standard installer includes Meta dependencies; it does not require or download Whisper. Add optional Whisper support with `Install.ps1 -WithWhisper` or `python3 scripts/install.py --with-whisper`, then select `--engine both` for a comparison. Meta remains the baseline; drafts are never automatically merged.

Meta uses the small CTC 300M INT8 model through native sherpa-onnx (about 365 MB), not the 7B/v2 system. This route works on Windows without WSL. There is no local per-minute ASR fee. See [comparison setup, exact models and review limits](TRANSCRIPTION.md).

## Start an episode

Give a local agent this prompt:

```text
Use https://github.com/AvtandilMghebrishvili/podcut-flow.
Read START_HERE.md and its podcut-flow skill. Edit my podcast.
Use the default Meta Omnilingual ASR for transcription.
Episode folder: /absolute/path/to/episode
Ask only for information I have not already provided.
```

If the path is missing, the agent asks for it first. Place all episode video and audio in that folder, optionally in subfolders. A browser chat cannot read a local drive from the GitHub link alone.

Dependency installation is included in the workflow. The agent reuses working tools and installs missing Python/FFmpeg/project/transcription requirements, using `Install.ps1` on Windows or `scripts/install.py` where Python is available. For requested Premiere automation it also installs/configures a missing MCP/plugin and verifies the connection. Adobe licensing/login, OS prompts or interactive plugin loading may still require the user. See [setup](SETUP.md) for the exact installer scope.

The agent asks which files are guest/host/wide cameras, which microphones or recorder channels belong to whom, whether colors need work, what language is spoken, and whether to deliver a render or a Premiere project. For one camera and one mix, it asks left/right seating and speaker identities in timestamped samples, and explains that clean independent voice isolation is not guaranteed.

If color is requested, it presents Natural, Warm and Contrast alternatives from actual episode frames, then uses the user's choice. It verifies sync across the recording, preserves separate microphones on separate lanes, and exports both original-clock and edited-clock TXT, SRT, VTT and JSON transcripts. Camera scratch audio is excluded from the final sequence when external recordings are available.

Premiere delivery uses original-media XML plus stems and LUTs, followed by native import, color application, save and reopen verification. **XML is not a completed `.prproj`.** Direct app automation needs an installed working connection; a simple manual-import path is included. Premiere-only mode does not render the full video.

Start with [local setup](SETUP.md), then [the agent playbook](../START_HERE.md). The [command guide](WORKFLOW.md), [Premiere guide](PREMIERE.md) and [limitations](LIMITATIONS.md) describe supported behavior and what still requires review. This is an agent-guided toolkit, not an unattended editor for arbitrary footage. Real episode media and private machine settings are not included. MIT licensed.
