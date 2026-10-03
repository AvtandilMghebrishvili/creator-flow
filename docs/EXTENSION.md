# Creator Flow for YouTube

[ქართული ინსტრუქცია](EXTENSION.ka.md)

A Chrome/Edge Manifest V3 extension that adds a collapsible Creator Flow panel **inside YouTube**. This is a local developer build, not a Chrome Web Store or Edge Add-ons listing.

## What works

| Panel | Implemented behavior | Evidence boundary |
| --- | --- | --- |
| Overview | Reads current video/channel title, loaded description, public count where available, and a transparent packaging checklist | Missing data stays unknown; no predicted CTR or opaque quality score |
| Packaging | Actual thumbnail at large/feed size; editable title/description/tag drafts; copy controls | Local drafts are templates. No metadata is published |
| Analytics | Separate Shorts/video summaries for up to 200 loaded cards; date-scoped Studio CSV import; weighted CTR, watch hours, views, subscribers and video rows | Visible cards are a sample, not a full crawl; Studio data is imported, not live OAuth analytics |
| Ideas | Topic-derived local idea templates or model-generated channel-specific ideas with rationale and evidence | No automatic trend search, keyword-volume service or guaranteed performance |
| Connect | Optional loopback bridge to OpenAI API or an installed Ollama model; async jobs; optional thumbnail vision; JSON handoff to/from Codex/Claude | Explicit Send action. Requires your own configured model; chat subscriptions/MCP connections are not inherited |

The extension supports Georgian and English. It does not control playback, publish changes, read cookies, collect browsing history or request all-site access. Only `youtube.com` and `www.youtube.com` receive the content script. YouTube Studio itself is not scraped.

## Install in Chrome or Edge

1. Obtain this checkout (or unzip the extension package).
2. Open `chrome://extensions` or `edge://extensions`.
3. Enable **Developer mode**, choose **Load unpacked**, and select `extensions/creator-flow`, the directory containing `manifest.json`.
4. Reload YouTube. Open a video or channel, then click the **Creator Flow** button at the bottom right. Pin the toolbar action if desired.
5. Use the language button for Georgian/English. The refresh button rereads the current page; expanding a description or scrolling a channel makes more evidence available.

Developer mode and Load unpacked are browser-controlled actions; the installer does not silently force-install into your personal browser profile. The normal Codex in-app browser is not the Chrome/Edge extension installation target. Refresh the extension on its management page and reload YouTube after updates.

## Import real Studio analytics

In **Settings → Studio CSV**, select the exact channel URL used on the page, the reporting period and a CSV exported from YouTube Studio's per-video Advanced mode report. Export with **English headers, comma delimiters, decimal dots**. Supported headers:

```csv
Content,Video title,Views,Impressions,Impressions click-through rate (%),Watch time (hours),Average view duration,Subscribers
abcdefghijk,Example video,1200,15000,4.2,30,0:01:30,12
```

`Video ID` or `video_id` also works for Content; `Title` works for Video title. Content/video ID, title and views are required; other metrics may be absent. Total rows are ignored to avoid double-counting. Invalid numbers, duplicate IDs, bad dates and malformed rows are rejected. At most 10,000 rows per CSV, 8 imported channels and 5 MB total are stored. Import replaces that channel's previous dataset. Handle URLs and `/channel/ID` URLs are not silently equated; use the same one as the current page.

The displayed CTR is weighted by impressions only across rows where both values are known. Each metric shows coverage. Average view duration is not a retention curve. No causal claim is made from raw lifetime Shorts versus long-video counts. Missing metrics are **unknown**, never zero.

## Connect AI locally

Install Creator Flow normally, then find the **Extension ID** on the extension's Settings page. Run the bridge in a terminal using a private workspace **outside Git repositories**:

```sh
creator-flow extension-serve --workspace "PRIVATE_WORKSPACE" --extension-id YOUR_EXTENSION_ID
```

This connects the extension to the local service but **does not enable a model**. The terminal prints the location of `connection.json`. Enter its URL and pairing token in the extension Settings and click Connect. Tokens rotate each bridge restart. Grant loopback permission when the browser asks; no remote host permission is requested by the extension. Keep the terminal running while using AI. Start the same command again after closing it. Multiple `--extension-id` arguments allow separately installed Chrome/Edge copies.

Choose one AI provider explicitly:

```sh
# Reuse a model already installed in Ollama; no model downloads are automatic.
creator-flow extension-serve --workspace "PRIVATE_WORKSPACE" --extension-id YOUR_EXTENSION_ID --provider ollama --model YOUR_INSTALLED_MODEL

# OpenAI API: set CREATOR_FLOW_OPENAI_API_KEY in this terminal's environment,
# then choose a model available to your API account with Structured Outputs.
creator-flow extension-serve --workspace "PRIVATE_WORKSPACE" --extension-id YOUR_EXTENSION_ID --provider openai --model YOUR_API_MODEL
```

The OpenAI API is billed separately from a ChatGPT subscription. The extension never reads Codex/Claude login tokens or vidIQ credentials. No paid model request runs on opening YouTube, refreshing, or importing CSV. **Send context** shows the provider/model and asks before sending. Context includes page text, full CSV aggregates and up to 100 CSV rows (including the current video). Treat those rows as private account data.

On a video, optionally enable **Include thumbnail image** with a vision-capable model. The bridge fetches only the canonical public `i.ytimg.com/vi/VIDEO_ID/hqdefault.jpg`, validates its type/size and attaches its pixels to that request. It is a YouTube preview, not a promise to inspect original upload resolution. Without this choice no pixels are sent and the model is instructed not to claim image inspection.

The bridge uses fixed provider endpoints and no shell commands. Its HTTP API binds only to `127.0.0.1`, checks Host, extension Origin (when sent) and a bearer token, limits request sizes, and runs one AI job at a time. API credentials remain in the bridge process environment. Jobs, contexts and reports stay in the selected private workspace. OpenAI requests use `store:false`; this is not a claim about provider retention policies. Do not place connection tokens or reports in this public repository.

Jobs return immediately and are polled so long AI responses do not depend on a persistent extension service worker. Duplicate requests reuse matching running/completed work. Failures are not automatically retried or switched to another provider. Restart-interrupted work is marked uncertain; inspect before explicitly sending again. Health reports configuration readiness, not a paid live-model test. Generated claims still need review.

## Use your existing Codex/Claude chat instead

1. Export **context JSON** and copy the agent prompt from Connect.
2. Give both to your agent. It may use its own available tools within your authorization; vidIQ usage and credits are separate.
3. Request `creator-flow-advice-v1` JSON. Preserve `contextKey` exactly and return these fields:

```json
{
  "schema": "creator-flow-advice-v1",
  "contextKey": "cf-12345678",
  "summary": "Evidence-backed summary",
  "findings": [{"title": "Observation", "detail": "Recommended action", "evidence": "Supplied row/date or a limitation"}],
  "titles": ["Proposed accurate title"],
  "description": "A factual draft description",
  "tags": ["relevant topic"],
  "ideas": [{"title": "Original idea", "format": "Video", "hook": "Proposed opening", "why": "Channel fit", "evidence": "Evidence or explicit hypothesis"}]
}
```

4. Import the report in the same page's Connect tab. A changed page, title, sample, language, topic, image choice or imported analytics produces a different context key; stale reports are rejected. Reports are rendered as text, never executable HTML.

The agent must inspect actual image pixels before visual claims, label samples and hypotheses, and use only authorized private analytics. A report import does not authorize publishing or metadata edits. The local report path is a manual handoff, not an automatic MCP connection.

## Development and verification

```sh
node --test tests/extension.test.cjs tests/selection.test.mjs
python -m pytest -q
python scripts/package_extension.py --output dist/creator-flow-extension.zip
```

The ZIP contains only extension assets, README and license, never bridge tokens or local analytics. No npm build or remote executable code is required. Browser tests should load an actual unpacked extension in an isolated Chromium profile, then exercise YouTube-style fixtures, SPA navigation, report matching, CSV import, language, escaped content and connection failures. Model adapters are tested using fake provider responses; this does not certify a particular real model/account. Live YouTube DOM changes can require selector updates.

## References

- [Chrome content scripts and isolated worlds](https://developer.chrome.com/docs/extensions/develop/concepts/content-scripts)
- [Chrome extension storage](https://developer.chrome.com/docs/extensions/reference/api/storage)
- [Edge local installation](https://learn.microsoft.com/en-us/microsoft-edge/extensions-chromium/getting-started/extension-sideloading)
- [OpenAI Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs)
- [Ollama chat API](https://docs.ollama.com/api/chat)
- [YouTube Advanced mode exports](https://support.google.com/youtube/answer/9717005)
- [YouTube tags guidance](https://support.google.com/youtube/answer/146402)
