# Shared local workflow

[Podcut Flow](https://github.com/AvtandilMghebrishvili/podcut-flow) provides the local episode/clip review and rendering route. Follow its [CLIPS.md](https://github.com/AvtandilMghebrishvili/podcut-flow/blob/main/docs/CLIPS.md) and START_HERE.md as the maintained implementation guide.

1. Ask for the folder/source and episode, clips or both. Propose count and durations as questions; wait for the user's answer before production.
2. For new recognition, use Meta Omnilingual ASR. Keep the full timestamped draft and allow user correction. YouTube captions remain an optional archive input; Whisper is opt-in.
3. Show the entire timed transcript, then the proposed clips and real spoken hooks. The default hook is a repeated teaser at the start, followed by the normal body, including its original occurrence. Include both occurrences in the final transcript and total duration.
4. Ask subtitles on/off per video and show actual original-font/color/size variations. Accept supplied TTF/OTF files. Never use generated fonts. Preserve original font licenses and verify actual Georgian/English characters.
5. After user confirmation of current text, timings, clip choices, hook and style, assemble the requested videos. Corrections or changed choices invalidate approval.
6. Deliver a clean MP4, optional captioned MP4 and separate SRT/VTT/TXT/JSON. Burned-in captions cannot be removed from the same pixels; choose the clean version instead. For Premiere, maintain editable caption tracks and respect the user's choice to render themselves.

The Podcut commands are `clips-init`, `clips-propose`, `clips-font`, `clips-review`, `clips-import`, `clips-approve` and `clips-render`. They require a **matching local edited video** and its complete final-clock transcript. Never pass a Podcut project configuration, a source-clock ASR sample or this repository's raw `{t,ms}` archive JSON as if it were already that format. Follow the import/schema instructions and verify the clock. The reviewed local module does not need Node or yt-dlp; those remain dependencies of this repository's archive tools.

Install/reuse Podcut's Python/FFmpeg dependencies through its normal installer. Do not install another copy of working tools. If Premiere-only work has no final export yet, prepare review materials and await the user's export or explicitly assemble/verify editable clip sequences in Premiere; do not force a full render.
