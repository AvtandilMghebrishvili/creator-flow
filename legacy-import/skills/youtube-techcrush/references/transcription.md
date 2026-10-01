# Transcription: Meta default, reviewed archive captions optional

For **new local transcription**, use **Meta Omnilingual ASR** through [Podcut Flow](https://github.com/AvtandilMghebrishvili/podcut-flow/blob/main/docs/TRANSCRIPTION.md). Its default is the local CTC 300M INT8 model. Reuse reviewed existing transcripts; do not re-transcribe solely to change engines. Whisper/comparison is explicitly optional.

For already published videos, `scripts/fetch-transcripts.js` can retrieve available YouTube captions. Listen and review the actual track. Platform/model quality varies with the recording; historical comparisons on one Georgian sample do not establish a general ranking. Do not upload private footage merely to obtain captions.

Show the **complete transcript with timecodes** before assembling video or burning captions. Let the user correct names, words and timings, then obtain confirmation of the revised text. Keep the original draft separately. Approval is tied to the version being used; later edits need a new confirmation.

## Archive input

The archive scripts flatten available `json3` caption events to `{t, ms}` entries, retaining the track label. An event segment can contain multiple words: timestamps must not be presented as guaranteed word alignment. Request the user's actual language, inspect the returned track and avoid silently treating a translated fallback as original speech.

```sh
node scripts/fetch-transcripts.js --video VIDEO_ID --langs "ka-orig,ka"
```

Missing captions are a reason to use the local Meta route with the user's authorized local recording, not to upload automatically or switch to a paid service. Paid/cloud services require the user's choice. No transcription source alone establishes speaker identity; `>>` indicates a possible speaker change, not a name.

## Local clip handoff

Follow [the shared workflow](podcut-flow.md). The local reviewed renderer needs a complete transcript matching the **edited video clock**, with `segments` and seconds, not this archive's raw `{t,ms}` format or source-clock ASR times. For a Podcut episode use its final-clock transcript. Verify imported timings against the exact video. Repeating the spoken hook at the start also repeats its text at the corresponding new timecodes.

Meta's word boundaries remain approximate. The new local renderer uses editable static cues; it does not invent exact karaoke alignment after text corrections. Keep separate SRT/VTT/TXT/JSON and a clean video so captions can be omitted or changed later.
