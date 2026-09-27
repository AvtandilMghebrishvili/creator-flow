# Local setup

Use a local agent with terminal and file access: Codex desktop/CLI or Claude Code. A GitHub link in a web chat is documentation access, not access to local media. Ask for the exact episode folder first. Keep the repository and episode folders separate.

## Let the agent install what is missing

Installing/using this workflow includes setting up its required free local dependencies. The agent should inspect the computer, reuse working installations, install what is missing for the selected delivery, and verify it works. Give a brief progress update, rather than handing the user a list of routine installation chores or asking again for each dependency. Preserve existing environments, MCP settings and working plugins. User participation is needed only for actual blocked steps such as an OS administrator prompt, an Adobe account login or mandatory interactive plugin loading.

After cloning or downloading/extracting this repository, Windows users/agents can run:

```powershell
.\Install.ps1
```

It locates a usable 64-bit Python 3.10+ or installs Python 3.12 through WinGet, verifies FFmpeg/ffprobe, installs them if both are missing, creates/reuses `.venv`, and installs Podcut plus the local transcription library. It uses the registered `Python.Python.3.12` and `Gyan.FFmpeg` packages, with exact IDs and no automatic upgrade of working system tools. See Microsoft's [WinGet install options](https://learn.microsoft.com/en-us/windows/package-manager/winget/install). It never changes PowerShell's persistent execution policy. If script execution is restricted, the agent can inspect the script and use the equivalent individual commands below; do not weaken the machine's policy.

On macOS/Linux with a usable Python:

```sh
python3 scripts/install.py
```

The helper uses an existing Homebrew, apt-get or dnf installation for missing FFmpeg. If Python or the package manager is absent, the agent installs the prerequisite using the supported OS/vendor method, then resumes. It does not bootstrap an arbitrary package manager or add unreviewed repositories. On systems outside those routes, use the official FFmpeg build and rerun. After any package-manager operation it checks both executables actually run; a partial/broken installation needs diagnosis instead of a duplicate installation.

Options:

| Windows | macOS/Linux | Meaning |
| --- | --- | --- |
| `-Check` | `--check` | Inspect only; no installs or file writes |
| `-WithoutTranscription` | `--without-transcription` | Skip the ASR library only when it is not needed |
| `-Premiere` | `--premiere` | Also report the required agent-managed Premiere connection step |

`-Premiere`/`--premiere` does **not** install Adobe or certify an MCP connection. For automated Premiere assembly the agent must complete [Premiere setup](PREMIERE.md), including installation of a missing MCP/plugin and a read-only connection test. If that connection is already healthy, reuse it. If the user only wants an XML import package or a render, no Premiere plugin is required. Adobe itself requires the user's licensed installation/account; purchasing a subscription is outside dependency setup.

The bootstrap verifies imports (including native libraries), checks package compatibility after changes, and caches its setup fingerprint in `.venv/` so repeat runs skip a working installation. Model weights are downloaded by the agent when the selected transcription model is first needed. Do not report the complete workflow ready until the model's short sample and any requested Premiere connection have also been verified. Keep a short local setup receipt alongside the episode's status: reused tools, new installs, checked versions, connection results and any blocked interactive step. Do not commit that machine-specific receipt.

## Manual equivalents and prerequisite recovery

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

The default installer includes both local recognizers. For manual setup:

```sh
python -m pip install -e '.[transcribe]'
```

Use the environment's Python, including its full Windows path when not activated. **Whisper + Meta run locally and sequentially by default.** Meta uses a pinned 365 MB Omnilingual CTC 300M INT8 conversion through sherpa-onnx, including native Windows support. Whisper's download size depends on the chosen model. These are downloads, not uploads of the episode. The CLI only permits new model downloads with `--allow-download`; otherwise both models must be cached. Start with a short language-specific sample and choose a larger Whisper model only when justified. CPU/two threads is the default; `--device cuda` affects Whisper only and needs compatible existing dependencies. See [models, comparison, licensing and recovery](TRANSCRIPTION.md).

```sh
podcut transcribe PROJECT --model small --language ka --start 60 --seconds 40 --allow-download
```

Inspect/listen to the sample before a full run without `--start`/`--seconds`. Save corrected names and uncertain passages; do not describe unchecked ASR as a verified transcript. A missing or unusable model is a disclosed remaining step, not permission to invent text.

## Agent discovery

The repository supplies `.agents/skills/podcut-flow/SKILL.md` for [Codex skill discovery](https://learn.chatgpt.com/docs/build-skills) and `.claude/skills/podcut-flow/SKILL.md` for [Claude Code skills](https://code.claude.com/docs/en/skills). Work from the repository or explicitly instruct the agent to read `START_HERE.md`. Keep the whole repository if installing the skill elsewhere: its relative guide links need the companion files. `AGENTS.md` and `CLAUDE.md` route episode work and repository maintenance separately.

For Premiere use the [dedicated guide](PREMIERE.md). The agent installs a missing integration when automated native assembly is selected; XML import is the simpler connection-free path. No Premiere credentials, bridge secrets, API keys or user-specific MCP configuration ship with this repository.

## Long recordings

Use one heavy job at a time. Helpers use two CPU threads where supported and a `.podcut/worker.lock`. Do not remove the lock until you have verified the recorded process stopped. WAV stems can exceed several GB; use a filesystem with large-file support. Rendering needs space for shot intermediates and the final file. Confirm actual disk capacity against source duration, microphone count and chosen delivery. Keep the application responsive and persist status between stages.
