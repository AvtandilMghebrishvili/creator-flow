# Local setup

Use a local agent with terminal and file access: Codex desktop/CLI or Claude Code. A GitHub link in a web chat is documentation access, not access to local media. Ask for the exact episode folder first. Keep the repository and episode folders separate.

## Install the tools

Requirements: Python **3.10+**, FFmpeg and ffprobe on PATH, adequate free disk space. Git is convenient for installing/updating the repository. FFmpeg builds must include the codecs needed by the actual media. Obtain FFmpeg from the [official download links](https://ffmpeg.org/download.html); Python from [python.org](https://www.python.org/downloads/).

On Windows, install those dependencies, reopen your terminal and check `python --version`, `ffmpeg -version`, `ffprobe -version`. If Python is launched with `py`, substitute `py` for the initial `python` command. No PowerShell execution-policy changes are needed:

```powershell
git clone https://github.com/AvtandilMghebrishvili/podcut-flow.git
cd podcut-flow
python -m venv .venv
.\.venv\Scripts\python -m pip install -e .
.\.venv\Scripts\podcut doctor
```

On macOS/Linux, install FFmpeg with your normal package manager, then:

```sh
git clone https://github.com/AvtandilMghebrishvili/podcut-flow.git
cd podcut-flow
python3 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/podcut doctor
```

In the remaining documentation, `podcut` means the executable in this environment. You can activate the environment, or use the full path above. `python -m podcut` is equivalent. `PODCUT_FFMPEG` and `PODCUT_FFPROBE` may point to specific executables when PATH is unsuitable.

Run `podcut init "ABSOLUTE_EPISODE_FOLDER"` once. This creates `.podcut/project.json` beside the source media; it does not move them. Subsequent work resumes that file. Do not put media inside the repository. Read `inventory_errors.json`, including unsupported RAW files, before continuing.

## Transcription

Install the optional local recognizer only when needed:

```sh
python -m pip install -e '.[transcribe]'
```

Use the environment's Python, including its full Windows path when not activated. [faster-whisper](https://github.com/SYSTRAN/faster-whisper) runs locally; selecting a model name may require downloading model weights. This is a download, not an upload of the episode. Explain model size/compute needs first. The CLI only permits a new model download with `--allow-download`; otherwise use cached weights or a local model directory. Start with a short language-specific sample and choose a larger model only if quality requires it and resources permit. CPU/int8/two threads is the default; CUDA is optional and requires compatible installed dependencies.

```sh
podcut transcribe PROJECT --model small --language ka --start 60 --seconds 45 --allow-download
```

Inspect/listen to the sample before a full run without `--start`/`--seconds`. Save corrected names and uncertain passages; do not describe unchecked ASR as a verified transcript. A missing or unusable model is a disclosed remaining step, not permission to invent text.

## Agent discovery

The repository supplies `.agents/skills/podcut-flow/SKILL.md` for [Codex skill discovery](https://learn.chatgpt.com/docs/build-skills) and `.claude/skills/podcut-flow/SKILL.md` for [Claude Code skills](https://code.claude.com/docs/en/skills). Work from the repository or explicitly instruct the agent to read `START_HERE.md`. Keep the whole repository if installing the skill elsewhere: its relative guide links need the companion files. `AGENTS.md` and `CLAUDE.md` route episode work and repository maintenance separately.

For Premiere use the [dedicated guide](PREMIERE.md). MCP is optional; XML import is the simplest path. No Premiere credentials, bridge secrets, API keys or user-specific MCP configuration ship with this repository.

## Long recordings

Use one heavy job at a time. Helpers use two CPU threads where supported and a `.podcut/worker.lock`. Do not remove the lock until you have verified the recorded process stopped. WAV stems can exceed several GB; use a filesystem with large-file support. Rendering needs space for shot intermediates and the final file. Confirm actual disk capacity against source duration, microphone count and chosen delivery. Keep the application responsive and persist status between stages.
