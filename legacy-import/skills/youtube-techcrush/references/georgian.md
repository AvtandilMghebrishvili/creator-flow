# Georgian (ქართული) and other low-resource languages

Verified September 2026. Most YouTube tooling assumes English; these are the specific
places it breaks for Georgian, and the workarounds.

## Speech-to-text

**Current shared workflow:** new local transcription defaults to Meta Omnilingual ASR through [Podcut Flow](podcut-flow.md). Review the full timed transcript before assembly. The table/comparison below records an earlier sample, not a general model ranking; Whisper is now opt-in.

| Source | Georgian | Quality | Cost |
|---|---|---|---|
| **YouTube auto-captions (`ka-orig`)** | yes | good on the historical sample below | free |
| whisper.cpp / OpenAI `large-v3` | yes, nominally | poor — frequently unusable | free (local) |
| whisper `large-v3-turbo` | yes, nominally | worse than large-v3 | free (local) |
| ElevenLabs Scribe | yes | strong | paid |

Direct comparison on the same two minutes of Georgian podcast audio:

- whisper large-v3: *"და უსახვედურეს რატოც ესო ნასას. ესე იგი ველაბარაგებით."*
- YouTube `ka-orig`: *"და უსაყვედურეს რატო წერსო ნასასო, ესე იგი ველაპარაკები"*

The YouTube version was closer to the recording in this historical sample. This is a
sample observation, not a general accuracy claim or an explanation of model training.

Use reviewed existing captions for archive work when appropriate. For raw/unpublished
footage, use **Meta by default**, test a representative sample and review names/timing.

## Text-to-speech

Relevant only if generating narration. **Clip mining does not need TTS at all** — the
archive already contains the creator's real voice, which is better than any synthetic
option and carries no authenticity risk.

If narration is genuinely required:

| Provider | Georgian | Notes |
|---|---|---|
| edge-tts (Microsoft Edge) | 2 voices: `ka-GE-EkaNeural`, `ka-GE-GiorgiNeural` | free, no API key; flat prosody |
| ElevenLabs v3 | yes (74 languages incl. Georgian) | best quality; voice cloning; paid |
| Azure Speech | same 2 voices as edge-tts | paid, no quality gain over free |
| Google Cloud TTS | **none** | Georgian not supported at all |
| OpenAI TTS | not officially | mispronounces; unreliable |

The free path gives a channel exactly two voices, so every video sounds identical —
which is both a viewer problem and an authenticity-policy problem. For Node, use an
`edge-tts` npm port; the original is Python.

## Fonts and captions

Use **static** font files. libass ignores variable-font weight axes, so a variable
ExtraBold silently renders as Regular — thin, low-contrast, and hard to read over video.

Get static Noto Sans Georgian from the
[notofonts/georgian releases](https://github.com/notofonts/georgian/releases)
(`NotoSansGeorgian-ExtraBold.ttf`, `-Black.ttf`). The google/fonts copy is variable-only.

Do not silently force Georgian casing changes. If Mtavruli uppercase is requested,
verify that the chosen original font contains the actual characters. Offer weight,
size and color choices using real font files and show the result for approval.

Georgian words run long. Keep captions to 3–4 words per line and expect to reduce the
count relative to an English equivalent.

## Console output on Windows

Georgian text through a pipe in the default Windows console renders as mojibake. This is
a display artifact, not data corruption. Write to a JSON or text file and read that
instead of debugging an encoding problem that does not exist.

## Generalising

The pattern holds for most languages outside the top ~20:

1. Platform-native ASR (YouTube's) usually beats local open models.
2. TTS options are few and interchangeable at the free tier; only paid multilingual
   models are genuinely usable.
3. Font rendering, not the model, is where output quality is silently lost.
4. **Clip mining sidesteps all of it**, because real recorded speech needs no synthesis
   and no transcription beyond what the platform already provides.
