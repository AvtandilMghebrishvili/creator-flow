# YouTube archive inside Creator Flow

The archive scripts from YOUTUBETECHCRUSH are now bundled here, alongside the podcast and reviewed Shorts/Reels tools. **One checkout and one installer** serve both routes. No second repository or separately copied archive skill is needed. Both original Git histories and the [MIT notice](archive/LICENSE) are retained.

## Setup and workspace

Use `Install.ps1 -WithArchive` on Windows or `python3 scripts/install.py --with-archive` on macOS/Linux. This also installs the normal podcast tools and Meta libraries. It reuses a working Node 22+ and installs yt-dlp with its default extras into the same `.venv`. Node is optional for users working only with local episodes/clips. The [yt-dlp dependencies](https://github.com/yt-dlp/yt-dlp#dependencies) include a JavaScript runtime for full YouTube support; bundled scripts explicitly enable their running Node executable. There are no npm packages to install.

When Node is missing the installer uses an available WinGet, Homebrew, apt-get or dnf. An existing incompatible/broken Node installation needs diagnosis; it is not silently overwritten. If the package manager does not provide Node 22+, the agent installs a supported release from [Node.js](https://nodejs.org/en/download), then reruns the check.

Activate `.venv` or use its full `creator-flow` executable path. Run from the user's chosen archive workspace, **outside the checkout**. The tools write `data/raw`, `data/transcripts`, `data/clips` and `data/out` there. Alternatively set `CREATOR_FLOW_ROOT` to that absolute directory. The old `YTC_ROOT` still works. Explicit executable overrides are `CREATOR_FLOW_NODE`, `CREATOR_FLOW_YTDLP`, `PODCUT_FFMPEG` and `PODCUT_FFPROBE`; portable `tools/` binaries also remain supported.

```sh
creator-flow archive doctor
creator-flow archive channel-stats --channel "https://www.youtube.com/@Handle"
creator-flow archive fetch-transcripts --video VIDEO_ID --langs "ka-orig,ka"
creator-flow archive find-candidates --all --limit 3
creator-flow archive inspect --video VIDEO_ID --from 600 --to 665
```

Only access the sources the user selected. Downloading and caption access depend on YouTube availability and permissions; a successful local doctor does not certify them. No automatic uploads are performed.

## From archive research to reviewed clips

1. Ask for the source/workspace and propose output count and duration as questions; wait for the user's choice. Preserve choices already given.
2. For **new transcription**, use **Meta Omnilingual ASR by default** with the user's local recording, following [TRANSCRIPTION.md](TRANSCRIPTION.md). Existing YouTube captions are an optional input, reviewed by listening. Do not upload unpublished recordings to obtain captions.
3. Read the shortlisted passages in context and refine boundaries. Archive scoring uses predefined TECHcrush topic weights, not learned channel-specific preferences; adapt editorial choices to the actual channel. [Channel analysis](archive/channel-data.md), [hooks](archive/hooks.md), [metadata](archive/metadata.md), [strategy](archive/strategy.md).
4. Follow [CLIPS.md](CLIPS.md) for the **complete transcript with timecodes**, corrections, captions on/off, real font/color options, spoken teaser and final confirmation. The teaser repeats first and remains later in the conversation. Its duration counts toward the chosen total.
5. Use `creator-flow clips-*` for current local assembly. It preserves clean video, editable subtitles and the optional captioned copy. Premiere delivery follows [PREMIERE.md](PREMIERE.md); Premiere-only mode never forces a full episode render.

The reviewed renderer takes a **matching local edited video and its complete transcript in that video's clock**. The archive's `{words:[{t,ms}]}` JSON is a research input with approximate segment starts, not that schema. Do not rename it to a final transcript or invent word ends. Use a complete reviewed matching transcript per CLIPS.md, or generate one through the normal Meta route. Slicing a downloaded source changes its clock; verify and rebase timings before review.

## Legacy renderer

The old `render-short.js` is retained as `creator-flow archive legacy-render` for explicitly requested compatibility. It downloads a source section, burns karaoke-style text and offers a **text overlay**, not the new repeated spoken teaser. It does not enforce review-state approval and cannot remove burned-in text. Its font fallback and NVENC detection are historical and need manual verification. Do not select it for the new workflow by default. See [legacy rendering](archive/rendering.md).

## Migration and compatibility

The public project is **Creator Flow | Podcasts, Shorts & Reels**. `creator-flow` is the preferred command; `podcut` and `python -m podcut` remain equivalent for existing projects. The Python distribution/module and private `.podcut/` state retain their original identifiers to avoid breaking saved work. Existing checkouts and virtual environments can stay at their current path; update the Git remote and rerun the installer. Do not rename an active `.venv` directory to rebrand it.

The imported JavaScript is shipped in `src/podcut/youtube/`, including built wheels. Archive tests live with the Python tests and run in the same Windows/Linux CI. YOUTUBETECHCRUSH is retained only as a historical repository pointing here; future changes belong here.
