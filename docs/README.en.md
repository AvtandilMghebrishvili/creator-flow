# Podcut Flow

A reusable local podcast-editing workflow for Codex and Claude Code, with Python helpers for synchronization, color previews, edit planning, separate microphone stems, timestamped transcripts, Premiere exchange and optional rendering.

Give a local agent this prompt:

```text
Use https://github.com/AvtandilMghebrishvili/podcut-flow.
Read START_HERE.md and its podcut-flow skill. Edit my podcast.
Episode folder: /absolute/path/to/episode
Ask only for information I have not already provided.
```

If the path is missing, the agent asks for it first. Place all episode video and audio in that folder, optionally in subfolders. A browser chat cannot read a local drive from the GitHub link alone.

The agent asks which files are guest/host/wide cameras, which microphones or recorder channels belong to whom, whether colors need work, what language is spoken, and whether to deliver a render or a Premiere project. For one camera and one mix, it asks left/right seating and speaker identities in timestamped samples, and explains that clean independent voice isolation is not guaranteed.

If color is requested, it presents Natural, Warm and Contrast alternatives from actual episode frames, then uses the user's choice. It verifies sync across the recording, preserves separate microphones on separate lanes, and exports both original-clock and edited-clock TXT, SRT, VTT and JSON transcripts. Camera scratch audio is excluded from the final sequence when external recordings are available.

Premiere delivery uses original-media XML plus stems and LUTs, followed by native import, color application, save and reopen verification. **XML is not a completed `.prproj`.** Direct app automation needs an installed working connection; a simple manual-import path is included. Premiere-only mode does not render the full video.

Start with [local setup](SETUP.md), then [the agent playbook](../START_HERE.md). The [command guide](WORKFLOW.md), [Premiere guide](PREMIERE.md) and [limitations](LIMITATIONS.md) describe supported behavior and what still requires review. This is an agent-guided toolkit, not an unattended editor for arbitrary footage. Real episode media and private machine settings are not included. MIT licensed.
