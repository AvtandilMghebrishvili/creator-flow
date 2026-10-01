# Rendering

Output target: **1080×1920, H.264, AAC 48 kHz, faststart.** YouTube re-encodes anyway,
so aim for a clean high-bitrate master rather than a small file.

## Layout

Two options, and the choice is not cosmetic.

### `blur` (default)

Blurred, darkened, zoom-filled copy of the frame as background; the complete 16:9 frame
scaled to 1080 wide and inset above the captions.

Use this for podcasts and interviews. Multi-camera edits cut between close-ups and wide
two-shots, and a centre crop destroys every wide shot by cutting both speakers in half.
The inset frame is smaller but always correct.

```
[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,
     gblur=sigma=42,eq=brightness=-0.22[bg];
[0:v]scale=1080:-2[fg];
[bg][fg]overlay=(W-w)/2:430[base];
[base]subtitles='<ass>':fontsdir='<fonts>'[v]
```

### `crop`

Centre crop to 9:16. More immersive, faces are larger. Only safe when the source is a
single centred speaker for the whole clip — verify by extracting frames first.

## Vertical budget (1920 px)

| Region | Purpose |
|---|---|
| 0–430 | Blurred background. Optional title bar. |
| 430–1037 | Video frame (1080×607) |
| 1037–1340 | Captions |
| 1340–1920 | Left mostly clear — the Shorts UI (like/comment/share, channel name, description) sits here |

Captions below ~1400 get covered by the interface. This is the most common rendering
mistake and it is invisible unless you check on a real Shorts player or account for it
deliberately.

## Captions

Word-by-word highlighting, generated as ASS. Each line emits one dialogue event per
word, with the active word recoloured inline. This is more verbose than `\k` karaoke
timing but far more predictable in libass and gives full colour control.

- **3–4 words per line.** More does not fit at a readable size on a phone.
- **Font size ~74 px** at 1080 wide, heavy weight, thick outline plus shadow. Captions
  are read over moving video; contrast matters more than elegance.
- **Strip transcript artifacts.** YouTube captions contain `>>` speaker markers and
  bracketed sound tags like `[laughter]`. They are useful for selecting clips and
  embarrassing on screen. `cleanWords()` removes them.
- **`WrapStyle: 0`** with real margins, so long hook lines wrap instead of running off
  both edges of the frame.

## Fonts

Use **static** font files, not variable ones. libass largely ignores variable-font
weight axes and renders the default instance — so a variable "ExtraBold" silently comes
out Regular, which looks weak and washed out over video.

For Georgian, Noto Sans Georgian ships static instances (ExtraBold, Black) in the
[notofonts/georgian](https://github.com/notofonts/georgian) releases. The copy in
google/fonts is variable-only and will disappoint you.

Pass `fontsdir` to the subtitles filter and reference the font by its *family* name.

## Encoding

```
-c:v h264_nvenc -preset p5 -cq 20 -pix_fmt yuv420p
-c:a aac -b:a 192k -ar 48000 -movflags +faststart
```

NVENC renders a 47-second clip in roughly 6 seconds. Fall back to `libx264 -crf 20
-preset medium` when NVENC is unavailable; `doctor.js` reports which you have.

`yuv420p` is not optional — other pixel formats play back green or not at all on some
devices.

## Always inspect before delivering

```bash
ffmpeg -ss <t> -i out.mp4 -frames:v 1 -vf scale=460:-1 frame.jpg
```

Pull 3–4 frames across the clip and actually look at them. Text overflow, caption
collisions, wrong font weight, and mis-timed subtitles are all silent failures — ffmpeg
exits 0 and the file plays. Checking costs seconds; shipping a broken clip costs trust.

## Paths in ffmpeg filters

Windows paths need escaping inside filter arguments: `D:\x\y.ass` becomes `D\:/x/y.ass`.
`ffPath()` in `lib/paths.js` handles it. Unescaped colons produce confusing parse errors
that look like filter-syntax problems.
