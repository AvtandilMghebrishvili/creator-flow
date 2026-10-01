# Thumbnails and covers

[ქართული მაგალითი](USER_GUIDE.ka.md#thumbnails) · [English walkthrough](USER_GUIDE.en.md#thumbnails)

Offer an optional thumbnail for the full episode and for each selected Short/Reel. This is an agent-managed image task alongside the local video workflow. The CLI records requests; an available image-generation/editing tool produces the actual artwork. A saved request or prompt is not a finished thumbnail.

## Offer and remember the choice

Ask once when planning the requested outputs, or before handoff if still unanswered. For example:

> Would you like a cover for the episode, separate covers for the selected Shorts/Reels, both, or none? Do you have guest/host photos and exact cover wording, or should I propose suitable frames and text?

Georgian:

> თაბნეილი სრული ეპიზოდისთვის მოვამზადო, შერჩეული Shorts/Reels-ისთვისაც, ორივესთვის თუ არ გინდა? სტუმრისა და წამყვანის ფოტოები და სასურველი ტექსტი გაქვს, თუ კადრები და ტექსტის ვარიანტები შემოგთავაზო?

Reuse an existing yes/no answer and any supplied photos, layout, copy, variant count or provider choice. A decline skips thumbnail work. An unanswered offer is not authorization to generate images and does not block otherwise approved video delivery. Asking about covers must not restart episode intake or force a full render in Premiere-only work.

`creator-flow questions PROJECT` includes the optional offer. Save its answer in `project.json` as `decisions.thumbnail_requested: true` or `false`; absent/null means not answered. Record exactly which outputs were requested in the private brief. For a clips-only job, `review.html` has **Ask me / Yes / No** and **Cover text** for each clip. Download corrections and import them with the existing `clips-import` command. Empty cover text means the agent should suggest wording, not invent an approved headline. Importing review corrections clears the current video review approval as usual; the video confirmation does not approve a thumbnail or publish anything.

## Use the matching content

| Output | Content to read | Suggested design canvas |
| --- | --- | --- |
| Full episode | Reviewed full transcript and the actual kept conversation; choose its main subject and promise | Landscape 16:9 |
| Short / Reel | That clip's selected body and spoken hook, in playback order, plus enough surrounding context to avoid a misleading claim | Portrait 9:16 |

These are composition starting points, not permanent platform upload specifications. Ask which platform/surface is intended and check its current requirements before platform delivery. A separate portrait cover file does not guarantee that the platform accepts it as a custom Short thumbnail or displays it on every surface.

Record transcript/source clock, episode or clip ID, supporting time ranges, a one-sentence topic, and the connection between the proposed imagery and the conversation. A Short about one subject must not receive a generic full-episode headline about another. Reuse an episode cover only when its message also fits that clip and the user chooses reuse. If text, cut ranges or the subject changes, revisit the affected cover rather than silently delivering a stale design.

## Real people, topic-based surroundings

Use the actual identified **guest photo on the left and host photo on the right** as the starting layout, and honor any requested reversal or alternative. Ask which file belongs to whom when uncertain. Use supplied portraits first; if absent, offer suitable sharp frames from the user's footage and show them for selection. Save each frame's source path/time privately. A single participant, multiple hosts, or a clip featuring someone else needs an appropriate confirmed layout; never invent an absent person merely to fill a side.

Inspect the chosen references before generating. Preserve identity, facial features and natural expressions, keep faces recognizable, and leave space for the text. Generate the surrounding background/objects/visual metaphors from the supported topic. An AI discussion might use abstract computation motifs; a camera discussion might use camera/lens imagery. These are examples, not a repeated template. Do not manufacture a photorealistic event, quotation or claim that the conversation does not support. Topic graphics must remain secondary to the speakers and headline.

## Exact text and concepts

Use the user's supplied headline or call to action verbatim unless they request copy editing. Otherwise offer a few concise alternatives based on the actual content, typically 2–3 concepts with a short headline, topic-visual idea and layout rationale. Examples of word count are creative guidance, not hard limits. The wording may be Georgian, English or another requested language. Do not imply a paraphrase is an exact spoken quote.

Let the user choose or revise the text/concept, unless they already delegated that choice. Existing exact copy or delegated creative choice does not need another approval loop. Show concrete drafts, accept feedback, and save the selected version. Confirm spellings and inspect every letter, particularly Georgian, at normal size and at a small feed preview. Where supported, preserve an editable text layer with an original licensed font. The video-caption original-font rules still apply; a generated cover image never supplies a video font.

## Generate with the available image tool

For Codex, prefer its available built-in image-generation/editing capability; for another client, use a connected image tool that actually supports the selected photo references. Follow that tool's reference-image rules and inspect local references first. Do not silently switch to an unrelated paid API, purchase credits or claim an image tool is installed by the Python installer. If no suitable tool is available, prepare the content-backed brief, selected photos and copy, and identify the missing connection. Continue independent video work.

Explain which selected image service will process the photo references; unlike local Meta transcription, image generation may use an external service. Use only the selected reference images and needed content summary. Keep original photographs, private transcript extracts, credentials and local provider settings outside the public repository.

Create artwork for the agreed format and outputs. A useful request structure is:

```text
Output: [episode or clip ID], [platform/surface], [aspect ratio]
Content evidence: [reviewed source and time range], [actual topic/claim]
References: [identified guest photo], [identified host photo]
Layout: guest left, host right, unless the recorded choice differs
Surroundings: [visuals grounded in this episode or this exact clip]
Text verbatim: [selected headline / CTA], language [language]
Keep: participant identity, readable faces, exact spelling, clear margins
Avoid: invented participants, unsupported claims and unrelated topic imagery
```

Inspect the resulting image for identity preservation, correct placement, text, topic fit, clutter and edge cropping. Show the actual generated draft; refine the chosen design. Do not substitute a generic stock person for a missing guest/host photo. A failed generation remains an incomplete image task, not permission to hand off a prompt as if it were the artwork.

## Private state and delivery

Maintain an agent-owned `.podcut/thumbnails/brief.json` (or a `thumbnails/` folder beside a clips-only review), following [the fictional brief example](../examples/thumbnail-brief.json). This is a record for the agent, not a CLI generation command or a rigid renderer schema. Keep generation requests/results, chosen text, identities, actual input references and tool details here. The browser request stores only `{requested, text}`; it cannot supply a trusted image-generation receipt or approval.

Deliver actual PNG/JPEG covers, clearly named by episode/clip and format, plus the chosen text and a short mapping to the corresponding video. Include a text-free version or editable composition when requested and supported, without promising a layered source that was never produced. Keep originals and previous versions. Record each final path, canvas, reviewed source/ranges, exact copy, tool/prompt and selection status. Changing a cover does not authorize replacing a published one.

Creating a thumbnail does not upload it. Publishing or changing a live thumbnail requires a separate user request and a verified connection for that destination. Platform upload limitations should be checked at that point, not guessed from the cover's existence.
