# YOUTUBETECHCRUSH

## Shared workflow with Podcut Flow

For new episodes and local Shorts, start with **[Podcut Flow](https://github.com/AvtandilMghebrishvili/podcut-flow)**. It uses **Meta Omnilingual ASR by default**, asks for clip count/durations, shows the complete timed transcript for correction and approval, offers captions on/off with original-font/color choices, and prepends a real spoken teaser while retaining it later in the conversation. Clean video and editable subtitles are preserved. [Shared workflow and commands](skills/youtube-techcrush/references/podcut-flow.md).

**ქართული:** ჯერ ვთანხმდებით რაოდენობასა და ხანგრძლივობაზე, შემდეგ სრულ ტექსტს ტაიმკოდებით ამოწმებ/ასწორებ. ირჩევ ნამდვილ ფონტს, ფერს და სუბტიტრებს ჩართულს/გამორთულს. ჰუკი დასაწყისში ტიზერად მეორდება და სრულ საუბარშიც რჩება. აწყობა იწყება მხოლოდ მიმდინარე არჩევანის დასტურის შემდეგ.

The archive tools below remain available. Their original renderer is a legacy YouTube-download/karaoke-overlay route; it does not implement the new review gates or spoken-hook reordering. Podcut's local route uses Python/FFmpeg and static cue captions; the archive tools here use Node/yt-dlp. See the linked guide for the actual boundary between them.

A Claude skill for turning a long-form podcast archive into YouTube Shorts — by mining
footage that already exists, not by generating AI video from scratch.

Built and tested on [TechCrush](https://www.youtube.com/@TechCrush1), a Georgian tech
channel with a large interview archive. Works for any channel; the Georgian parts are
documented because that is where most YouTube tooling quietly falls apart.

## Why clip mining instead of AI generation

The popular "AI YouTube automation" stack builds videos from nothing: stock footage, a
synthetic voice, a scraped script. It starts fast and ends badly — the output is
interchangeable with thousands of identical channels, YouTube's inauthentic-content
policy targets exactly that pattern, and there is no moat.

If a creator already has hours of original footage, that archive is the asset. The
scarce resource is not video generation. It is **knowing which 45 seconds are worth
cutting, and what to say in the first two.**

Two practical consequences:

- **No text-to-speech needed.** The archive contains the creator's real voice, which
  removes the hardest problem in non-English video automation entirely.
- **No authenticity risk.** It is real footage of a real person saying something they
  actually said.

## What it does

```
transcripts → candidate moments → you pick → hook → render → you approve → you upload
```

- Pulls **free word-level transcripts** from YouTube's own captions — no API key, no
  quota, and for low-resource languages substantially better than local Whisper
- Scores 42-second windows across the whole archive against signals derived from the
  channel's **own view data**, not general advice
- Measures which topics actually perform, using medians, and surfaces the gap between
  what a channel publishes most and what works best
- Renders **1080×1920** clips with word-by-word captions, hook overlay, and GPU encoding

It deliberately stops before uploading. That step needs a human.

## Requirements

Node 20+, portable ffmpeg, `yt-dlp`, and a font. **No Python, no npm dependencies, no
admin rights.** Roughly 250 MB.

## Install

```bash
git clone https://github.com/AvtandilMghebrishvili/YOUTUBETECHCRUSH
cd YOUTUBETECHCRUSH && ./install.sh          # or .\install.ps1 on Windows
```

This copies the skill to `~/.claude/skills/youtube-techcrush`. Then in your project
directory:

```bash
node ~/.claude/skills/youtube-techcrush/scripts/doctor.js
```

`references/setup.md` covers the portable toolchain.

## Use

```bash
# what actually works on this channel
node scripts/channel-stats.js --channel "https://www.youtube.com/@Handle"

# transcripts for the whole archive (free; a few minutes for a few dozen videos)
node scripts/fetch-transcripts.js --channel "https://www.youtube.com/@Handle"

# shortlist candidate moments
node scripts/find-candidates.js --all --limit 3

# set exact in/out points on a sentence boundary
node scripts/inspect.js --video <id> --from 600 --to 665

# render
node scripts/render-short.js --video <id> --start 605 --end 652 \
  --hook "First line|Second line" --out my-clip
```

Set `YTC_ROOT` to point the scripts at a project directory other than the current one.

## Documentation

| File | Covers |
|---|---|
| [`SKILL.md`](skills/youtube-techcrush/SKILL.md) | The workflow Claude follows |
| [`references/hooks.md`](skills/youtube-techcrush/references/hooks.md) | Hook patterns, with measured wins and failures |
| [`references/rendering.md`](skills/youtube-techcrush/references/rendering.md) | Layout, captions, fonts, ffmpeg specifics |
| [`references/channel-data.md`](skills/youtube-techcrush/references/channel-data.md) | Reading performance data without fooling yourself |
| [`references/georgian.md`](skills/youtube-techcrush/references/georgian.md) | Georgian TTS/ASR/font findings |
| [`references/transcription.md`](skills/youtube-techcrush/references/transcription.md) | Captions vs Whisper, and when each wins |
| [`references/strategy.md`](skills/youtube-techcrush/references/strategy.md) | Cadence, content mix, measurement |
| [`references/setup.md`](skills/youtube-techcrush/references/setup.md) | Portable, no-admin install |

## Findings worth stealing

Measured, not assumed:

- The historical Georgian sample favored YouTube captions over local Whisper `large-v3`.
  New local transcription now defaults to **Meta Omnilingual ASR** in the shared workflow;
  review the actual recording rather than treating one sample as a universal ranking.
- **Google Cloud TTS has no Georgian at all.** Free Georgian TTS is two Edge voices,
  which means every video on a channel sounds identical.
- **Variable fonts render at the wrong weight in libass.** Use static instances or your
  ExtraBold captions silently come out Regular.
- **A centre crop destroys wide two-shots.** Every multi-camera podcast edit contains
  them; a blurred-background inset is the safe default.
- **Medians, not means.** One viral clip will otherwise keep a dead category alive in
  the numbers.

## Credits

The general YouTube playbooks that informed the strategy references draw on
[claude-youtube](https://github.com/AgriciDaniel/claude-youtube) by Daniel Agrici.
The pipeline, scoring, rendering, and language findings here are original.

## License

MIT — see [LICENSE](LICENSE).
