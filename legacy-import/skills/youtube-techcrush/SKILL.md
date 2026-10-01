---
name: youtube-techcrush
description: Prepare Shorts from a podcast/interview archive or a local edited episode. Use for transcript-based clip selection, spoken teasers, caption review and archive/channel analysis. Uses Podcut Flow for local Meta transcription, original-font subtitle choices and approved clip rendering. Do not use for unrelated coding, generated presenter videos or automatic publishing.
---

# YouTube archive + Podcut Flow

Use [the shared workflow](references/podcut-flow.md) for episode-to-clips production. Its current implementation is in [Podcut Flow](https://github.com/AvtandilMghebrishvili/podcut-flow); locate/reuse the checkout or install it from its instructions. Do not assume the local renderer exists in this archive repository.

## Agree before production

Ask for the episode folder or authorized archive source, and whether the user wants the full episode, clips or both. Propose clip count and duration **as questions** and wait for agreement; include opening teaser time. Reuse existing answers. Do not start episode processing/rendering while those choices are unanswered; read-only intake can continue.

Use **Meta Omnilingual ASR by default for new transcription**. Reuse already reviewed transcripts. Existing YouTube captions are an optional archive input, not a universal accuracy authority; review against the matching video. Whisper/comparison is opt-in. Do not upload unpublished footage to obtain captions.

Show the **complete timed transcript** before assembly or caption burn-in. Accept corrections, then obtain confirmation of the revised text/times. Ask captions on/off for each video. Offer real-font family/color/size samples or accept user-supplied TTF/OTF files; never use image-generated lettering or invented fonts. Verify Georgian/English glyph coverage.

Select an actual spoken source passage for the hook. Play it first as a teaser, then continue the body, retaining the passage at its original place by default. Show the source range, resulting order and total duration. A title overlay is optional and cannot substitute for the requested spoken teaser.

Confirm the current transcript, clip boundaries, hook and applicable caption style before rendering. Changing those choices invalidates earlier confirmation. Preserve clean video, separate editable subtitles and the optional captioned version. Use the Podcut review page and approval-aware commands; the legacy `render-short.js` does not implement these gates or spoken-hook reordering.

## Archive tools retained here

For published videos, `scripts/fetch-transcripts.js` can obtain available captions. `scripts/channel-stats.js` provides channel view summaries; `scripts/find-candidates.js` makes a heuristic shortlist. These tools use Node and yt-dlp; see [setup](references/setup.md). Scoring weights are predefined, not automatically learned from channel data. Read every candidate, listen, check context and refine sentence boundaries.

The original `scripts/render-short.js` is a separate legacy YouTube-download/karaoke-overlay route. Use it only when explicitly chosen with its limitations understood, after the same user review steps. The shared Podcut renderer takes local video and produces static readable cue captions, clean/captioned versions and repeated spoken teasers. Do not claim the two renderers have identical features.

Use [hooks](references/hooks.md), [metadata](references/metadata.md), [channel data](references/channel-data.md) and [strategy](references/strategy.md) only when relevant. Historical channel/language observations are examples, not universal promises. Inspect real output frames and playback before delivery. Publishing/uploading needs the user's explicit instruction.
