# Setup

Node 20+ and roughly 250 MB. No admin rights, no Python, no npm dependencies.

Everything lands inside the project directory, so uninstalling is deleting a folder.

```
<project>/
├── tools/
│   ├── ffmpeg/bin/{ffmpeg,ffprobe}.exe
│   └── yt-dlp.exe
├── assets/fonts/*.ttf
└── data/{raw,transcripts,clips,out}/
```

## Check first

```bash
node scripts/doctor.js
```

Reports what is present, what is missing, and whether NVENC GPU encoding is available.
Run it before anything else and again whenever something behaves oddly.

## ffmpeg (portable, ~107 MB zip)

Windows — [gyan.dev](https://www.gyan.dev/ffmpeg/builds/) essentials build:

```powershell
Invoke-WebRequest https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip -OutFile ffmpeg.zip
Expand-Archive ffmpeg.zip -DestinationPath tools\_ffx
Move-Item tools\_ffx\ffmpeg-* tools\ffmpeg
Remove-Item tools\_ffx, ffmpeg.zip -Recurse -Force
```

macOS/Linux: `brew install ffmpeg`, or a static build from johnvansickle.com.

The build must include `libass` (for the `subtitles` filter) — the essentials build does.

## yt-dlp (~18 MB)

A self-contained executable. It does **not** require Python despite being a Python
project.

```bash
curl -L -o tools/yt-dlp.exe \
  https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe
```

Update it regularly — YouTube changes break extraction, and a stale yt-dlp is the most
common cause of sudden failures:

```bash
tools/yt-dlp.exe -U
```

## Fonts

Static instances only — see `rendering.md` for why variable fonts fail in libass.

Georgian: [notofonts/georgian releases](https://github.com/notofonts/georgian/releases)
→ `full/ttf/NotoSansGeorgian-{ExtraBold,Black}.ttf` into `assets/fonts/`.

Latin: any heavy static face works. Inter, Montserrat ExtraBold, and Archivo Black are
all reasonable and freely licensed.

## Optional: local transcription

Only needed for footage not yet on YouTube. See `transcription.md` before installing
~4 GB of model.

## Secrets

No API keys are required for the core pipeline. If any are added later (ElevenLabs for
dubbing, for instance), put them in `.env` and make sure `.env` is in `.gitignore`
before writing anything into it — not after.
