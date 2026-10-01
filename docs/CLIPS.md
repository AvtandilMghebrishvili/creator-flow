# Reviewed clips, subtitles and opening teasers

Creator Flow combines its Meta transcription/editing route with the local clip-mining and vertical-layout workflow from [the original YOUTUBETECHCRUSH project](ARCHIVE.md). This module uses Python and the existing FFmpeg installation; Node is not needed for local clips. YouTube archive fetching and channel-statistics scripts are bundled in this same repository; see [ARCHIVE.md](ARCHIVE.md). Archive scoring remains a predefined heuristic, not a learned ranking model.

## User flow: ask, review, then assemble

1. Ask whether the user wants the full episode, clips, or both. Propose **count and duration as a question**, for example: “სამი 45–60-წამიანი კლიპი მოვამზადოთ, თუ სხვა რაოდენობა/ხანგრძლივობა გირჩევნია?” Count and duration are examples, never silent defaults. Include the opening teaser in the total duration. Wait for the answer before episode processing/clip production; read-only intake can continue. Reuse answers already provided.
2. Use Meta Omnilingual ASR by default. Preserve its original draft and the complete, timestamped TXT/SRT/VTT/JSON. For a Creator Flow edit, use `retime-transcript` to obtain the matching edited-clock transcript. Show the **whole transcript**, not only candidate excerpts, before video assembly or caption burn-in. The user may correct it in chat, edit the files, or use the local review page. Corrections require confirmation of the revised text; they are not automatic approval.
3. Propose complete, self-contained passages and their exact boundaries. Let the user choose the clips and an **actual spoken passage from the video** for each opening hook. By default the hook is a **repeated teaser**: play it first, then play the body in its original order, including that passage again. Record the hook's source times and show the full resulting text/order/duration. Do not substitute an invented quote, AI voice, or text-only overlay for the requested spoken hook.
4. Ask captions **on or off for each video**. Offer a few real-font/style previews: family, size, text color and outline. Render lettering using original publisher/installed/user-supplied font files only. Never use image-generated lettering or an invented font. Show both Georgian and English as relevant; verify the actual characters used. Accept the user's own TTF/OTF. Ask again only when a required choice is missing or changes.
5. After the user confirms the full text/times, clip selection, hooks and applicable caption style, record approval against that exact review. Then assemble only the requested deliverables. Editing text, timing, hook, captions, style or source invalidates the previous approval. Re-show the affected result and obtain a new confirmation.
6. Preserve a **clean video**, optional **captioned video**, and separate subtitles/transcripts. Captioned pixels cannot be switched off inside a burned-in MP4; use the clean version or regenerate the captioned version from the approved text. In Premiere, keep captions in a separate editable track and verify that hiding it removes them. Upload/publishing is a separate user request.

These confirmation points are the requested product behavior, not a generic approval requirement for repository maintenance, tool installation or synthetic tests.

## Current supported input and timing

The executable clip module takes an **existing local edited video with its matching audio** and a **complete transcript on that video's clock**. Use a clean input for switchable subtitles: text already burned into the supplied video cannot be removed by this module. Use Creator Flow's final `episode.json` transcript, not `.podcut/project.json` and not the source-clock `reference.json`. It also accepts explicitly verified imported transcripts labeled `clock: "media seconds"`, `complete: true`, with `segments: [{start,end,text,words?}]` in seconds. Do not simply relabel a mismatched source transcript. An agent must check the transcript against the video at separated points and record that evidence when approving.

If the user chooses Premiere-only episode work, do not render the full episode to feed this module. Prepare the transcript/shortlist for review, keep the native project editable, and use the user's final export when available. Creating native hook/clip sequences and editable caption tracks directly inside Premiere is an agent-managed app operation requiring verification; `clips-render` produces MP4s, not a `.prproj`. If the user changes timing in Premiere, re-export/reconcile the transcript before generating clips. Full-episode captions can use one selected range with `source` layout and an explicitly agreed long duration; the same review rules apply.

Meta word times are approximate. The importer groups up to four original timed words into editable cues. If text was corrected without updating its words, the corrected segment text is retained. Cuts through cues are rejected: refine the cue or cut by listening. This version renders **readable static cue captions**, not forced-aligned karaoke highlighting. Correcting a word does not manufacture a new word alignment. Speaker identity is not inferred from captions. Captions with literal ASS control characters (backslash/braces) currently require an explicitly reviewed plain-text alternative rather than silent text substitution.

## Commands

After agreeing scope and producing the matching full Meta transcript:

```sh
podcut clips-init FINAL_VIDEO.mp4 FINAL_TRANSCRIPT.json EPISODE/.podcut/clips \
  --count 3 --min-seconds 45 --max-seconds 60 --note "User chose three 45–60s clips including teasers"
podcut clips-propose EPISODE/.podcut/clips/review.json
podcut clips-font EPISODE/.podcut/clips/review.json ORIGINAL_FONT.ttf --origin "Publisher URL or user-supplied font"
podcut clips-review EPISODE/.podcut/clips/review.json
```

Open the returned `review.html` locally. It shows the whole transcript with editable text/start/end fields, a local video picker for listening, clip boundaries, spoken hook range, repeat/move choice, per-video captions switch, and real-font/color/size previews. Nothing uploads the selected video. Each hook/body range expands to show its text in playback order. Add/remove/split cues in JSON or ask the agent to apply the exact correction; the page edits existing cues. Missing or insufficient candidates are shown honestly rather than inventing extra clips.

The shortlist uses generic story/conflict/question/number signals, with Unicode-aware matching. Scores only prioritize reading; listen, check context and refine sentence boundaries. It does not predict views or automatically learn weights from channel analytics.

Download corrections from the page and return the JSON to the agent. A checked review box is a user statement in that file; the agent still verifies it belongs to the current review and records the actual approval. For chat corrections, edit `review.json` and regenerate the page. Neither opening the page nor editing text grants approval.

```sh
podcut clips-import EPISODE/.podcut/clips/review.json review-corrections.json
# Only after the user has approved the complete current text/choices:
podcut clips-approve EPISODE/.podcut/clips/review.json \
  --note "User approved the displayed transcript, clips, repeated hooks and caption style" \
  --matching-video-note "Checked matching final-video speech at start, middle and end"
# Only for requested rendered clip delivery:
podcut clips-render EPISODE/.podcut/clips/review.json
```

`clips-brief` changes agreed count/duration with a new recorded user answer. `clips-propose` never overwrites existing selections. Every clip needs an explicit boolean `captions`, a unique simple `id`, `start`/`end`, and `hook: {start,end,mode:"repeat"}`. Changing to `move` is available if the user asks for it. The renderer validates count, **final duration including repeats**, cue boundaries, font coverage and the approval signature before encoding.

Exports include `*-clean.mp4`, optional `*-captioned.mp4`, separate SRT/VTT/TXT/JSON, ASS when captions are on, and a manifest listing the actual source ranges. The clean and captioned versions share the approved hook/body ordering and audio. Caption styles remain separate from text. Exported MP4s are H.264/AAC at 30 fps. `blur` fits the complete picture in 9:16; `crop` needs a checked centered subject; `source` preserves the source aspect ratio. Encoding checks duration and decodability; inspect real frames and playback for typography, safe areas, context and lip sync before delivery.

## Original fonts

Use installed files or obtain static fonts from their publisher, retaining license notices locally. Suggested starting points:

| Language | Actual font option | Source |
| --- | --- | --- |
| Georgian + Latin | Noto Sans Georgian, static publisher build | [Noto Georgian](https://github.com/notofonts/georgian) |
| Georgian + Latin | Sylfaen, when already licensed/installed | [Microsoft family documentation](https://learn.microsoft.com/en-us/typography/font-list/sylfaen) |
| English | Noto Sans static build; or installed Arial / Arial Bold | [Noto Sans](https://github.com/notofonts/latin-greek-cyrillic), [Arial](https://learn.microsoft.com/en-us/typography/font-list/arial) |
| User choice | Original supplied TTF/OTF | Record the supplied filename/source |

The existing installer adds `fontTools` for checking actual family names, character coverage and static font files. It does not globally install or bundle copyrighted fonts. A missing Georgian/English character fails rather than silently falling back to another face. Variable fonts are rejected in this renderer; request the publisher's static release. Rendered font/style choices require visual review. The local review HTML embeds the selected original font bytes for consistent preview; keep it and export font folders private, and do not distribute font files unless their license permits it.

White, yellow and mint text/outline presets are starting choices, not an automatic selection. No AI-generated font assets are used.

## Caption customization and batch application

![Illustrative caption styling panel, with a fictional host](assets/caption-style-studio.png)

This is generated documentation artwork, not a screenshot or a source of production font assets. The real `review.html` panel uses embedded original font files and exposes font selection, size (24–110), text color, outline color, outline width (0–10), and White/Yellow/Mint presets. To use a different weight, register the original static Bold/Regular file and select that face; there is no separate synthetic bold/italic toggle.

The review's `style` object is **shared across its batch**. Every caption-enabled clip receives that style only when the current text, cuts, hooks and style have been approved and rendering was requested. Captions on/off remains per clip. For different styles, use separate reviewed batches. Color presets update text and outline colors; they do not select or install a font, change size, start an export, or publish a video. Corrections downloaded from the review page must be returned to the agent and imported before approval/rendering.

There is no persistent global preset library. Keep the review JSON to retain its settings; any later style change invalidates its previous approval. Clean videos remain available to omit burned-in captions. Read the visual walkthrough in [ქართული](USER_GUIDE.ka.md#caption-style) or [English](USER_GUIDE.en.md#caption-style).

## Optional thumbnails for each clip

The agent offers a cover for every requested Short/Reel, using **that clip's reviewed passage and spoken hook**, rather than a generic full-episode topic. Use real identified guest/host photographs on opposite sides, generate relevant surrounding topic visuals, and use the user's exact headline/CTA or propose options. See [THUMBNAILS.md](THUMBNAILS.md).

Each clip in `review.html` has **Ask me / Yes / No** and an optional **Cover text** field. The correction JSON stores `thumbnail: {requested: null|true|false, text: "..."}` beside the clip. An empty text field asks for suggestions; an unanswered choice never becomes a yes. Returning the JSON and running `clips-import` persists the choices. Older reviews without these fields remain valid; importing an older page preserves a saved cover choice for a matching clip ID. Corrections invalidate the current video approval as usual.

These controls record a request, not an image-generation job or final-image approval. `clips-render` still exports videos and subtitle files; the agent uses a suitable connected image tool for accepted thumbnails, shows drafts and records selected PNG/JPEG files separately. A missing/declined cover never forces image generation or blocks an approved clip. Track thumbnail content against current ranges/text in the private brief and revisit it after relevant edits. Uploads remain a separate request.
