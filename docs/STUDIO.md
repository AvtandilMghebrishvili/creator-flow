# Creator Flow Studio: subscriptions, shared memory and local editing

[ქართული](STUDIO.ka.md)

Studio is the local control panel opened by the extension's **CF** button or at `http://127.0.0.1:8772/studio/`. It owns project memory and routes explicit tasks to the user's chosen connector. The companion must be running on the same computer. Opening a panel, saving memory or selecting a provider never starts generation.

## Install and start

Install the base workflow first. On Windows, from the repository:

```powershell
.\Install-Studio.ps1
.\Start-Studio.ps1
```

The installer adds the optional JWT/cryptography dependency and the tested unmodified vendor packages, Gemini CLI 0.62.0 and Claude Code 2.1.288, under ignored `tools/subscription-connectors`. It requires Node.js 22+ for those CLIs. `-WithoutVendorClis` installs only the ChatGPT connector dependencies. It does not log into accounts, accept account consent, download AI models or perform generation.

The launcher defaults to the current user's local application-data directory, outside Git. You can choose `-Workspace "PRIVATE_FOLDER" -Port 8772`. Keep its terminal running; launch it again after restarting the computer. The workspace retains projects/jobs; the pairing token changes each start. Only one companion may use a workspace at once. If a process crashed, inspect its `worker.lock` PID before removing a stale lock.

On other platforms, install `pip install -e ".[connectors]"`, install the supported vendor CLIs if wanted, and run:

```sh
creator-flow studio-serve --workspace PRIVATE_WORKSPACE --port 8772
```

The local UI works without an extension ID. For direct extension requests to the bridge, start with `Start-Studio.ps1 -ExtensionId YOUR_ID` (Windows) or add `--extension-id YOUR_ID` to the CLI command, then pair through extension Settings using the private `connection.json` URL/token. Stop the previous companion before restarting on the same port. The extension's CF button can open Studio without granting it account tokens. Reload the unpacked extension for version 0.2.0. Store ZIPs under `dist`; generate with `python scripts/package_extension.py --output dist/creator-flow-extension-0.2.0.zip`.

## Connectors and supported execution

| Connector | Subscription route | Text / ideas / analysis | Image output |
| --- | --- | --- | --- |
| ChatGPT | Official **Continue with ChatGPT** and explicit plan-usage permission | Direct streaming request using the selected account's model catalog | Task handoff to ChatGPT, then image import |
| Gemini | User signs into official Gemini CLI with Google | Local CLI invocation using its cached Google login | Task handoff to Gemini, then image import |
| Claude | User signs into their unmodified Claude Code | Local CLI invocation after `claude.ai` auth-method check | Unsupported; choose an image-capable connector |
| Chat handoff | Any supported provider's official app | Copy the prepared task, then return its result | Only providers with image creation in their own app |

For ChatGPT, finish the browser consent flow, refresh Studio, choose the saved account, load its model list, select a model and save the connector configuration. Sign-in, enabled connector and successful generation are separate states. Studio does not infer quota, subscription tier or guaranteed availability. Use **Manage usage** to review plan limits and credits in ChatGPT.

The official plan-usage flow requires HTTP Responses requests; **the billing credential is the user's authorized ChatGPT plan, not a developer API key**. Studio sends `store:false` and `stream:true`, accepts only a terminal `response.completed`, and never falls back to separately billed API credentials. This preview does not support image generation, so the image task is clearly marked `handoff`, never claimed as generated. [Official plan usage](https://developers.openai.com/siwc/token-sharing-open-source) · [Supported features and limits](https://developers.openai.com/siwc/token-sharing-open-source/preview-limitations).

Gemini and Claude sign-in stays in their official apps. On Windows, **Open sign-in terminal** opens that installed app for the user; on other systems use `gemini` or `claude auth login`. Provider credentials are never copied into the extension or Creator Flow. The app verifies subscription-oriented authentication before tasks and rejects API/environment overrides. It launches text tasks with tools restricted, and does not automatically retry or switch vendors. Vendor CLIs may implement their own internal retry/limit behavior. [Gemini authentication](https://geminicli.com/docs/get-started/authentication/) · [Claude Code conditions](https://code.claude.com/docs/en/legal-and-compliance).

For distributing a product containing Claude Code, follow Anthropic's conditions for running the unmodified binary and end-user authentication. This is not a custom Claude.ai OAuth client or a service reselling the user's quota. No automatic browser chat scraping, cookie extraction, CAPTCHA bypass or private API endpoints are used.

## Roles and shared memory

Enable one connector to route all its supported roles to it. With several enabled, assign **analysis, ideas, writing and images** individually. A missing or disabled role fails visibly. An image task cannot silently turn into a text result or move to another vendor.

Create a project and optionally select its existing private episode folder. Memory contains the brief, audience, corrected names, style and user decisions. Explicitly accepted model outputs join the context; ordinary generated results remain unapproved. Optionally attach a context JSON exported from the YouTube extension. With the extension paired, open its Connect tab, click **Load Studio projects**, select the destination and **Attach context to project**. This opens the matching Studio memory page without generating or sending anything to a provider. It transfers text/metrics only, not thumbnail pixels. Newer project revisions cannot be overwritten by a stale tab.

Every job freezes the project context and revision when submitted. Edits use optimistic version checks to prevent another window from overwriting newer memory. A result from an older revision must be reviewed and deliberately incorporated into current memory. Projects remain isolated. Exported memory JSON is a portable project record, not a synchronization of private ChatGPT/Gemini/Claude conversation histories. Do not put secrets into shared editorial memory.

Clicking **Start task** sends the shown project context to the chosen provider. Video files are not attached by this interface. When image work is a handoff, copy the task into the official app, create/download the image there and import its local PNG/JPEG/WebP path. The real image is validated and copied into the private workspace. A returned image is not automatically published or burned into video.

## Local video and Reels controls

Studio calls the existing Creator Flow Python/FFmpeg workflow, not arbitrary shell commands:

- Attach/inventory an episode; run sync, color previews, Meta transcription and audio preparation; export an approved Premiere XML or explicitly render an approved episode plan.
- For **new raw camera projects**, source/audio mapping, sync verification, color selection and the episode edit plan are still prepared in the existing agent/CLI workflow. This version does not add a complete multicamera timeline editor or native Premiere automation UI.
- From an edited video and its complete matching transcript, confirm the clip count/duration, create a review and propose segments.
- Open the complete timed transcript, edit text and boundaries, choose a real spoken hook (repeat by default), captions on/off per clip, original font files, color/outline/size and layout.
- Save corrections, review the current saved text and matching video, and approve it. Saving invalidates old approval. Unsaved editor changes block approval/rendering. Start rendering separately; the existing source fingerprints, duration and approval checks still run.

Source media stays local. Captions use original font files; fonts are not generated. Local Meta weights must already be installed: the panel does not silently download models. Old outputs are preserved. The queue records running/completed/failed/interrupted state; progress is a job state, not an invented percentage. Inspect final video/audio before publishing. None of these controls uploads to YouTube.

## Storage and verification

The loopback companion verifies Host, Origin and bearer authorization for workspace operations. Its same-origin UI bootstraps a local pairing token, with cross-site embed protection and restrictive CSP. OAuth uses fresh state, nonce and PKCE, validates signed ID tokens, binds registrations to verified identity, serializes token refresh and rotates refresh credentials atomically. Tokens stay in the companion's protected vault: Windows DPAPI, Unix owner-only file permissions. No OAuth token enters extension/browser storage or a prompt.

Automated tests exercise memory/routing, OAuth validation, stream failures, account boundaries and CLI/API separation. Browser tests exercise actual local Studio UI, timed transcript correction, explicit approval and a real synthetic FFmpeg clip render. Tests use synthetic provider responses. A passing test does not mean a user's provider login, model, quota, image generation or billing entitlement has been verified live.

```sh
python -m pytest -q
node --test tests/extension.test.cjs tests/selection.test.mjs
# Optional: set CREATOR_FLOW_PLAYWRIGHT to an installed Playwright module, then:
node tests/studio-browser.cjs
```
