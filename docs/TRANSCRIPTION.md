# Meta transcription and optional Whisper comparison

`podcut transcribe` defaults to **Meta Omnilingual ASR only** (`--engine meta`). Meta's draft becomes the baseline for retiming into the edit. Whisper is optional and is neither required, loaded nor downloaded in the default route. Nothing is sent to an external transcription service and no paid ASR API is used.

## Setup and first sample

Run the usual `Install.ps1` / `python3 scripts/install.py`. Its `transcribe` extra includes `sherpa-onnx` and the model-download helper. Existing installations are reused; already installed Whisper is preserved but not used by default. The installer verifies libraries; **weights and actual recognition are verified by running a sample**.

For an existing, synchronized Creator Flow project:

```sh
podcut transcribe PROJECT --language ka --start 60 --seconds 40 --allow-download
```

## Optional comparison

Install the optional Whisper extra only when comparison or Whisper-only transcription is wanted:

```sh
python scripts/install.py --with-whisper
# Manual equivalent in the active environment:
python -m pip install -e ".[transcribe,whisper]"
podcut transcribe PROJECT --engine both --language ka --model small --seconds 40 --allow-download
```

On Windows, `Install.ps1 -WithWhisper` is equivalent. Do not combine it with `-WithoutTranscription`. An explicit comparison processes the same audio with both engines sequentially and saves both drafts plus a listening page. For a comparison test without setting up an episode, pass a specific audio file:

```sh
podcut compare-audio "PATH_TO_RECORDING.wav" --language ka --model small --start 60 --seconds 40 --allow-download
```

The standalone command only decodes the requested interval of the first audio stream, downmixed to mono. It saves under the recording's `.podcut/asr-tests/` folder and does not edit an episode, change source mappings or select a transcript for an existing project. Choose a representative mixed recording or test each isolated microphone separately. This mode does not infer speaker identity or synchronize different recordings.

`--allow-download` permits weight downloads only. Without it, the selected model must be cached (both models only for an explicit comparison). Missing Meta causes a clear failure, never a silent switch to Whisper. The first Meta download is approximately **365 MB**, plus a token table and license. Optional Whisper's size depends on `--model`; `small` is a modest-resource starting point, not a claim of high Georgian accuracy. `--model` is a Whisper option and does not change the pinned Meta model.

## What exactly runs

| Engine | Model and execution | Timing |
| --- | --- | --- |
| Meta (default) | **omniASR_CTC_300M**, original November 2025 model, INT8 ONNX conversion distributed by sherpa-onnx maintainer csukuangfj; CPU, two threads | CTC character emission times grouped into approximate word boundaries |
| Whisper (opt-in) | Selected faster-whisper model; CPU INT8 with two threads by default | Estimated word boundaries |

The Meta adapter uses [sherpa-onnx's documented Omnilingual support](https://k2-fsa.github.io/sherpa/onnx/omnilingual-asr/models.html), which works on native Windows, macOS and Linux where compatible Python wheels exist. It does not install WSL, fairseq2, a new GPU stack or a Premiere plugin. The model repository revision and SHA-256 checksums for weights, tokens and license are pinned in `src/podcut/asr_models.py` and verified before use. Corrupt files are rejected. Models live in the normal Hugging Face cache, outside Git.

This is **not** the 7B LLM, the December v2 checkpoint or the older MMS model. Do not attribute their benchmark results to this 300M conversion. [Meta's Omnilingual code/models](https://github.com/facebookresearch/omnilingual-asr#license) and [sherpa-onnx](https://github.com/k2-fsa/sherpa-onnx) use Apache-2.0; Whisper uses MIT. Model files and license notices remain in their cache; no weights are redistributed with Creator Flow. There is no per-minute model fee for local use; hardware/cloud rental and the user's editor subscriptions are separate.

The CTC model detects languages from audio; it does not accept language conditioning. `--language ka` labels the Meta transcript and guides Whisper when explicitly selected. A supported language does not guarantee readable results on every recording. `--device cuda` applies **only to optional Whisper**, using already-compatible CUDA dependencies; Meta always uses CPU here. Comparison loads the two models one at a time.

## Read the results

Each run contains:

- `meta/reference.{json,txt,srt,vtt}`: the primary draft on the source/reference clock, with model identity, range, timing caveats and processing time.
- Optional comparison adds `whisper/reference.{json,txt,srt,vtt}` as a separate draft and `comparison.html`: both texts side by side, differing words, and timestamp buttons to listen. Open locally in a browser and keep its relative audio file beside it; some editor HTML previews may restrict local playback. Nothing uploads audio.
- Optional `comparison.json`: per-window text differences, normalized word edit distance divided by the larger word count, model versions and processing durations. Meta-only runs do not produce a comparison report.
- Per-engine chunk receipts and `run_status.json`: original model text/words for the context window, warnings and resume information, including explicit failure status. Zero-duration Whisper word alignments retain the text and trigger review rather than silently deleting words. Inconsistent decoded text and word text fail explicitly.

**Disagreement is not WER, accuracy, a confidence score, or a winner.** Punctuation/case differences are normalized; Georgian letters and numbers are retained. Both-empty windows are flagged for listening, and identical hypotheses can share the same error. The system does not merge conflicting words or silently replace one model's text with the other's. To judge accuracy, listen and prepare a human-corrected reference, especially for names, numbers, overlap and mixed languages. Compare speed using the saved decode times/real-time factor; these exclude download/loading and are not universal hardware benchmarks.

Meta uses 20-second windows with up to one second of context on each side, below its input length limit. Optional comparison feeds identical windows to both engines. Timed words are assigned to the central window to avoid repeating context. ASR boundaries remain approximate and may differ near window edges. Meta's last character emission plus 20 ms estimates a word end; this is not forced alignment or verified caption timing. Review and correct subtitles before delivery.

## Full episode and retiming

After reviewing the sample, run:

```sh
podcut transcribe PROJECT --language ka
podcut retime-transcript PROJECT
```

Meta processes the complete reference audio. A partial test is marked `complete: false` and cannot count as the episode transcript. Completed chunks are reused without loading the model again. Changed source/microphone mapping, sync, model files/versions, language, range or selected engines creates a separate run. The project worker lock prevents concurrent heavy work.

`transcript_latest.json` points to **Meta's draft**, including after an explicit comparison. This is the configured baseline, not an automatic quality ranking. The pointer records the selected engine and current comparison path (null for Meta-only runs). An older `transcript_comparison_latest.json` remains historical until another comparison is made. Old drafts are preserved; the next successful Meta run updates the main pointer. Use `retime-transcript PROJECT --transcript PATH_TO_WHISPER_REFERENCE_JSON` only to deliberately select a different reviewed draft. Retiming checks source-clock provenance and kept-range coverage. A sample made by `compare-audio` is not an interchangeable project-clock transcript.

If a selected engine fails, the run fails visibly, completed receipts remain, and the previous project transcript pointer is preserved. Fix the dependency/model error and repeat the same command to continue. Do not call partial work complete or automatically run a different engine. An explicitly chosen Whisper-only route (requiring the optional `whisper` extra) is:

```sh
podcut transcribe PROJECT --engine whisper --language ka --model small
```

This explicitly selected route makes its Whisper draft the retiming baseline. Keep recordings, model files, actual transcripts and comparison reports local; do not commit them to the public repository. CI uses synthetic signals and mocked recognition to verify timing, recovery and reporting contracts, not ASR language quality.
