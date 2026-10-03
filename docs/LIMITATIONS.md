# Capabilities and review boundaries

| Area | Implemented | What still needs judgment or another tool |
| --- | --- | --- |
| Intake | Local inventory, stable source IDs, missing-question checklist | User confirms roles, channels, episode folder and delivery |
| Synchronization | Spectral/waveform anchors, offset/drift model, manual anchors | Real-world echo/bleed, silent cameras and interrupted recordings need inspection |
| Camera planning | Mic-energy suggestions, reviewed turns, explicit static camera, coverage fallback | Not semantic diarization; speaker identity and editorial rhythm must be reviewed |
| Audio | Distinct final-clock mono stems, mild cleanup, shared normalization/limiting, measured combined mix | No guaranteed voice isolation, advanced denoising or perfect bleed suppression |
| Color | Real frame comparisons, per-camera 3D LUTs, three starting looks | Correct input profile/LUT, white balance, exposure and camera matching need inspection |
| Transcript | Meta CTC 300M by default; four formats, source/edit clocks and resumable receipts; optional Whisper comparison and listening report | Meta's token-based word boundaries are approximate; small CTC is not 7B/v2; language quality needs listening; comparison does not automatically merge text |
| Clips/subtitles | Complete transcript review page; corrections; count/duration approval; repeated spoken hook with matching audio/text; clean and optional captioned MP4; real-font checks | Requires a matching local edited video; static cue captions, not forced-aligned karaoke; shortlist is heuristic; native Premiere captions and archive-fetching remain separate routes. See CLIPS.md |
| Thumbnails | Optional episode intake and per-clip yes/no/copy controls; persistent requests and documented agent workflow | Actual generation needs a reference-capable image tool and real identified photos. Text, identity and topic fit need visual review; cover upload support depends on the destination. See THUMBNAILS.md |
| Premiere | Original-media FCP7 XML, LUT handoff, installation guide | Native `.prproj` creation and app save/reopen review require installed Premiere access |
| Render | Sequential H.264/AAC export, frame/decode/loudness checks, sampled audio alignment | Full editorial/visual review; different delivery codecs need an explicit implementation change |

The automated test suite uses generated signals and video. It exercises clock recovery, drift fitting, coverage, transcript retiming, color handling, separate audio stems, Unicode paths and an actual FFmpeg XML/render pipeline. This is evidence about those paths, not proof of arbitrary real-world footage or every NLE version. Local development/testing began on Windows; CI also exercises Linux. The optional ASR adapter is tested without downloading a large model, so recognition accuracy is never inferred from CI. The native Premiere patch is an experimental adapter and is not an officially supported Adobe integration.

One wide camera cannot become independently captured close angles. One mixed mic cannot reliably become two isolated microphones. Seating and timestamped speaker examples help editorial identification; they do not solve overlapping voice separation. Separate files that contain the same mix do not count as independent microphones.

Proprietary RAW, variable-rate, HDR, anamorphic or interlaced media may require a supported editor and a documented conversion. H.264/H.265 camera originals are not necessarily RAW. Do not identify log/gamut from camera make alone, and do not assume a BT.709 container tag proves a finished Rec.709 image. Use manufacturer LUTs with the correct profile and licensing. No camera-specific LUTs are bundled.

Each synchronized source must be continuous under one linear clock model. Multiple camera files can share a role, but a camera interruption inside a file needs separate treatment. This version expects each chosen audio stem's source to cover all kept intervals; sequential microphone chunks or reference-clock gaps must be assembled explicitly before using the generic helper. It rejects missing audio coverage rather than filling it with unrelated speech.

Transcription follows the selected reference recording's duration. Edits outside that range need an explicitly extended reference and verified alignment. Millisecond SRT/VTT timestamps are not frame-based broadcast timecode. Do not call unreviewed ASR word timings exact captions. Mixed languages and noisy/overlapping Georgian speech often need stronger models and human correction.

The agent should persist uncertain points in the episode's handoff. If a required native app, model or source is unavailable, it can finish independent preparation and explain the specific remaining step. A saved XML, successful MCP return, generated MP4 or numerical validation report alone is not evidence that every requested deliverable was reviewed.

The optional [YouTube extension](EXTENSION.md) provides local page checks, visible-card samples, dated Studio CSV metrics and an opt-in model bridge. It has no live Google OAuth, automatic trend/keyword research or publishing controls. A connected model still needs factual review; tests do not establish scoring accuracy. Thumbnail visual analysis requires explicit image opt-in and a vision-capable model.
