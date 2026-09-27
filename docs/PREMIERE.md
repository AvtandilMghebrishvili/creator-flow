# Premiere delivery: choose the simpler path first

Ask whether Premiere is installed, its version and OS. The user chooses **Premiere assembly for their own review/render** or a final video. Do not render a complete video in Premiere-only mode. Creating audio stems and still color previews is part of preparation, not a final video export.

## Path A — XML import, no MCP required

This is the simplest portable handoff. `podcut xml PROJECT` produces `Podcut_FINAL.xml` and `color_handoff.json` in `.podcut/exchange/`. The XML references original footage and prepared external microphone WAVs. It does not include camera scratch audio. Selected camera roles are on separate video tracks, with each independent microphone on its own audio track.

1. In Premiere create a new, clearly named episode project; save it to the episode's working folder. Avoid altering an unrelated open project.
2. Import `Podcut_FINAL.xml` using File → Import, then open the imported FINAL sequence. Relink only to the inventoried originals/stems if prompted.
3. Check sequence size, frame rate, duration, clip boundaries, source-speed interpretation and framing. Inspect footage with different resolutions/rates. XML effect/scale interpretation can vary across NLE versions.
4. Open `color_handoff.json`. Each source prefix such as `s01 | guest | 0001` maps to its approved LUT. Apply that matching LUT **once** to all corresponding shots in Lumetri, or to the source/master clip where appropriate. Use the LUT's full baked conversion-and-look as the Input LUT; avoid an additional log conversion or duplicate grade. `original` means no LUT. Check the actual image after each camera group.
5. Label microphone lanes clearly: guest and host separately when independent recordings exist. Keep mono microphones centered. Compare the combined level against `audio_stems.json`; pan laws and routing can change the imported mix. Never duplicate a shared mix and call it isolated guest/host audio.
6. Save a versioned **native `.prproj`**. Close/reopen that saved project and verify relinks, cuts, color, track separation, audio routing, playback, and start/middle/end lip sync. Keep the approved comparison images available for matching.
7. Deliver the `.prproj`, linked media/stems/LUT locations, source and final-clock transcripts, and a short review note. The user performs the final render.

The XML alone is an **exchange package**, not a finished native project and not proof of applied color. If the agent cannot operate the installed app, it should provide the package and these remaining steps honestly. Moving to another computer requires collecting/copying linked assets or relinking; do not move the episode folder mid-edit.

## Path B — optional local Premiere MCP

When the user selects automated Premiere assembly, **the agent completes this setup**, including the required missing plugin/runtime, instead of merely telling the user to install it. First test any existing Premiere MCP connection; reuse a working installation. If it is broken, diagnose it and preserve its configuration before repair. Discover the tools and perform a read-only app query; files on disk or a tool count alone do not prove the plugin is connected.

Install only the components required by the chosen upstream release. Preserve existing Codex/Claude MCP entries and local bridge credentials; add or repair this connection without replacing the whole client configuration. Use the current official upstream release/setup instructions, inspecting the installer before running it. If the app needs a login, an OS prompt or an interactive UXP load action, finish the independent steps, explain that exact user action, and resume verification afterward. If Premiere itself is absent, use the user's existing Creative Cloud entitlement or explain the missing licensed app; do not purchase a subscription. XML-only delivery does not require this installation.

For automated app operation, this workflow can use the independent open-source [PremiereProMCP project](https://github.com/CaYatur/PremiereProMCP). Podcut Flow does not bundle its server, Adobe software or a user's bridge credentials. Follow the upstream version's prerequisites, supported Premiere versions and installation instructions. Do not assume the current local machine's configuration works on another computer.

The upstream Windows installer workflow is:

1. Obtain the Setup ZIP from the project's [Releases](https://github.com/CaYatur/PremiereProMCP/releases), extract it and follow its Setup.bat instructions. Inspect what is being installed and use the upstream release appropriate to the app.
2. Load/connect the Premiere UXP plugin as instructed, using Adobe's UXP Developer Tool when required. Adobe documents [UXP plugin installation](https://developer.adobe.com/premiere-pro/uxp/plugins/distribution/install/).
3. Read the **locally generated** `%APPDATA%\PPMCP\HOW-TO-CONNECT.txt` and `mcp-config-snippet.json`. Use the personalized executable/script paths from those files in the agent's MCP configuration. Never publish their secrets or copy another person's local-auth files.
4. Configure a **local stdio server** in Codex or Claude Code. It is not a hosted URL connector that can be pasted into a web-chat remote MCP field. Use the client's actual installed help/configuration and the generated snippet. Claude Code documents [local MCP server configuration](https://code.claude.com/docs/en/mcp).
5. Restart/reload the relevant client if needed, open the plugin inside Premiere, and test a read-only app/project query. Confirm the expected episode project/sequence before editing.

For Claude Code, the generic shape is:

```text
claude mcp add premiere-pro --scope user -- "FULL_PATH_TO_NODE" "FULL_PATH_TO_SERVER_INDEX_JS"
```

Substitute the actual paths from the generated setup files. For Codex, inspect `codex mcp add --help` or use its MCP settings and the same local command/arguments. Avoid guessing TOML/JSON fields from a different client's config. If upstream has changed, consult its current documentation rather than treating these examples as immutable installation commands.

After connection, discover the available tools/schema, then perform a read-only connectivity check. Save a checkpoint before timeline mutations. Import the XML, identify the returned **sequence ID**, open/activate the right timeline in the app, apply colors, inspect tracks and save. Validate visible state and file contents; a successful tool return is not sufficient. Before repeating an action after a timeout, inspect whether it already happened to avoid duplicate imports/effects.

Some Premiere/tool versions have shown stale-object errors during clip splitting or track renaming. If this occurs, stop retrying the same mutation blindly: use the already-cut XML and rename through the UI where possible. Programmatic sequence activation may not open its timeline tab, and a still-export helper may capture a stale UI frame. Seek, let the app settle, and verify that the image actually corresponds to the requested sequence/time. These are observed integration risks, not claims about every release.

MCP success does not bypass native save/reopen review. Report missing app access or compatibility problems explicitly; the exchange-package path remains available.

## Experimental offline Lumetri adapter

`podcut premiere-luts` can add approved CUBE LUT references to a **new copy** of certain gzip/XML Premiere projects, using the local Adobe-installed Lumetri preset as a template. Prefer supported app/UI operations. Native project internals are undocumented and may change; this adapter is experimental, derived from a Premiere 26.3-era workflow, and has not been verified against every release.

Requirements: close the target project, save a checkpoint, identify its exact sequence ID, retain the XML-generated source prefixes, locate the installed `LumetriPresets.prfpset`, and choose a new output path. The command refuses an existing output and existing Lumetri components rather than silently stacking/replacing grades.

```text
podcut premiere-luts PROJECT --native INPUT.prproj --preset LumetriPresets.prfpset --sequence-id SEQUENCE_ID --output NEW_GRADED.prproj --closed
```

`--closed` records a condition the operator must actually establish; it does not close Premiere itself. The helper emits a receipt with `native_reopen_verified: false`. Open the generated copy in Premiere, verify every camera group, save natively and cold-reopen it before claiming success. If structure differs, preserve the original and use Path A/B. Do not distribute Adobe preset binaries or the user's local connection credentials in this repository.
