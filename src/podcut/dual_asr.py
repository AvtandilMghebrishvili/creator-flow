"""Sequential two-engine transcription with recoverable, reference-clock comparisons.

Agreement is not ground truth. Neither engine overwrites the other's text or timings.
"""
from difflib import SequenceMatcher
import gc
import html
import math
import os
from pathlib import Path
import time
import unicodedata

import numpy as np
import soundfile as sf

from .asr_models import resolve_models
from .core import digest, ffmpeg, fingerprint, load, probe, read, state, worker, write
from .transcript import asr_audio, asr_signature, save_formats, stamp

CHUNK_SECONDS = 20.0
CONTEXT_SECONDS = 1.0
ALGORITHM = 'dual-asr-v2'


def normalized_words(text):
    text = unicodedata.normalize('NFKC', text).casefold()
    # Preserve letters/marks/numbers in every script; punctuation becomes a boundary.
    return ''.join(c if unicodedata.category(c)[0] in 'LMN' else ' ' for c in text).split()


def edit_distance(a, b):
    row = list(range(len(b) + 1))
    for i, left in enumerate(a, 1):
        next_row = [i]
        for j, right in enumerate(b, 1):
            next_row.append(min(next_row[-1] + 1, row[j] + 1, row[j-1] + (left != right)))
        row = next_row
    return row[-1]


def compare_texts(left, right):
    a, b = normalized_words(left), normalized_words(right)
    edits = edit_distance(a, b)
    return {'normalized_match': bool(a or b) and a == b,
            'review_required': a != b or not (a or b),
            'both_empty': not (a or b), 'word_edits': edits,
            'word_disagreement': edits / max(len(a), len(b), 1),
            'whisper_word_count': len(a), 'meta_word_count': len(b),
            'differences': [{'kind': tag, 'whisper': ' '.join(a[i:j]), 'meta': ' '.join(b[k:l])}
                            for tag, i, j, k, l in SequenceMatcher(None, a, b, autojunk=False).get_opcodes()
                            if tag != 'equal']}


def token_words(tokens, timestamps, duration):
    """Group CTC characters without presenting emissions as exact speech boundaries."""
    if len(tokens) != len(timestamps):
        raise ValueError('Meta returned inconsistent token timestamps; cannot fabricate word timing.')
    if any(not math.isfinite(float(t)) or t < 0 or t > duration + .1 for t in timestamps):
        raise ValueError('Meta returned invalid token timestamps.')
    if any(b < a for a, b in zip(timestamps, timestamps[1:])):
        raise ValueError('Meta returned unordered token timestamps.')
    words, letters, first, last = [], [], None, None

    def flush():
        nonlocal letters, first, last
        if letters:
            words.append({'word': ''.join(letters), 'start': float(first),
                          'end': min(duration, float(last) + .02)})
        letters, first, last = [], None, None

    for token, timestamp in zip(tokens, timestamps):
        # The pinned tokenizer emits characters and spaces; also accept sentencepiece spaces.
        for char in token.replace('▁', ' '):
            if char.isspace():
                flush()
            else:
                if first is None:
                    first = timestamp
                last = timestamp
                letters.append(char)
    flush()
    return words


def open_engine(name, config):
    if name == 'whisper':
        from faster_whisper import WhisperModel
        return WhisperModel(config['path'], device=config['device'], compute_type=config['compute_type'],
                            cpu_threads=2, num_workers=1, local_files_only=True)
    import sherpa_onnx
    return sherpa_onnx.OfflineRecognizer.from_omnilingual_asr_ctc(
        model=config['assets']['model.int8.onnx'], tokens=config['assets']['tokens.txt'],
        num_threads=2, provider='cpu')


def decode(name, engine, samples, language):
    if name == 'whisper':
        segments, _ = engine.transcribe(samples, language=language, beam_size=5,
                                       word_timestamps=True, condition_on_previous_text=False,
                                       vad_filter=True)
        segments = list(segments)
        return {'text': ''.join(segment.text for segment in segments).strip(),
                'words': [{'word': w.word, 'start': float(w.start), 'end': float(w.end),
                           'confidence': float(w.probability)}
                          for segment in segments for w in (segment.words or []) if w.word.strip()]}
    stream = engine.create_stream()
    stream.accept_waveform(16000, samples)
    engine.decode_stream(stream)
    result = stream.result
    words = token_words(result.tokens, result.timestamps, len(samples) / 16000)
    if normalized_words(result.text) != normalized_words(' '.join(w['word'] for w in words)):
        raise ValueError('Meta text and timed tokens disagree; retain the failure for review.')
    return {'text': result.text, 'words': [dict(w, word=' ' + w['word']) for w in words]}


def windows(start, end):
    count = math.ceil((end - start) / CHUNK_SECONDS)
    return [(start + i * CHUNK_SECONDS, min(end, start + (i + 1) * CHUNK_SECONDS))
            for i in range(count)]


def make_segment(words, lo, st, en):
    selected = []
    for word in words:
        a, b = float(word['start']) + lo, float(word['end']) + lo
        if not math.isfinite(a) or not math.isfinite(b) or b < a:
            raise ValueError('Invalid ASR word boundary')
        if st <= (a + b) / 2 < en:
            selected.append(dict(word, start=max(st, a), end=min(en, b)))
    if not selected:
        return []
    # Whisper can give real text zero-duration word alignments. Never silently delete those words.
    valid_span = selected[-1]['end'] > selected[0]['start']
    return [{'start': selected[0]['start'] if valid_span else st,
             'end': selected[-1]['end'] if valid_span else en,
             'text': ''.join(w['word'] for w in selected).strip(),
             'words': selected if valid_span else [], 'speaker': None,
             'timing_issue': any(w['end'] <= w['start'] for w in selected)}]


def run_engines(audio, audio_origin, start, end, output, models, language, audio_signature,
                full_duration, clock):
    ranges = windows(start, end)
    write(output / 'run_status.json', {'status': 'running', 'range': [start, end]})
    transcripts = {}
    try:
        for name, config in models.items():
            engine = None
            rows, elapsed = [], 0.0
            try:
                for index, (st, en) in enumerate(ranges):
                    receipt = output / name / f'chunk_{index:06}.json'
                    if receipt.exists():
                        data = read(receipt)
                    else:
                        if engine is None:
                            print(f'Loading {name}: {config["name"]}', flush=True)
                            engine = open_engine(name, config)
                        lo, hi = max(start, st - CONTEXT_SECONDS), min(end, en + CONTEXT_SECONDS)
                        x, sr = sf.read(audio, start=round((lo - audio_origin) * 16000),
                                        stop=round((hi - audio_origin) * 16000), dtype='float32')
                        if sr != 16000 or x.ndim != 1 or not len(x):
                            raise ValueError('ASR comparison requires nonempty mono 16 kHz audio.')
                        tick = time.monotonic()
                        decoded = decode(name, engine, x, language)
                        warnings = []
                        if '\ufffd' in decoded['text']:
                            warnings.append('Model output contains a replacement character; listen and correct text.')
                        if any(w['end'] <= w['start'] for w in decoded['words']):
                            warnings.append('Zero-duration word alignment: text retained; timing needs review.')
                        if normalized_words(decoded['text']) != normalized_words(''.join(w['word'] for w in decoded['words'])):
                            raise ValueError('Decoded text and word text disagree. Cannot safely build timed drafts.')
                        data = {'range': [st, en], 'context_range': [lo, hi],
                                'raw_decode': decoded, 'warnings': warnings,
                                'segments': make_segment(decoded['words'], lo, st, en),
                                'decode_seconds': time.monotonic() - tick}
                        write(receipt, data)
                    if data['range'] != [st, en]:
                        raise ValueError('Cached chunk range mismatch. Inspect the run receipts.')
                    rows.extend(data['segments'])
                    elapsed += data['decode_seconds']
                    print(f'{name}: {en - start:.0f}/{end - start:.0f}s', flush=True)
                metadata = {'clock': clock, 'language': language, 'model': config['name'],
                            'engine': config, 'machine_draft': True, 'timing_review_required': True,
                            'complete': start == 0 and end >= full_duration - .001,
                            'range': [start, end], 'audio_signature': audio_signature,
                            'decode_seconds': elapsed, 'real_time_factor': elapsed / (end - start),
                            'timing_note': config['timing']}
                base = output / name / 'reference'
                save_formats(base, rows, metadata)
                transcripts[name] = read(base.with_suffix('.json'))
            finally:
                del engine
                gc.collect()  # Free one model before loading the other, including GPU allocations.
        comparison = build_comparison(output, transcripts, ranges)
        write(output / 'comparison.json', comparison)
        write_html(output / 'comparison.html', comparison, audio, audio_origin)
        write(output / 'run_status.json', {'status': 'completed', 'range': [start, end]})
        return output / 'comparison.json'
    except Exception as exc:
        write(output / 'run_status.json', {'status': 'failed', 'error': str(exc), 'range': [start, end]})
        raise


def build_comparison(output, transcripts, ranges):
    left, right = transcripts['whisper'], transcripts['meta']
    for key in ['clock', 'range', 'audio_signature', 'language']:
        if left[key] != right[key]:
            raise ValueError('Cannot compare transcripts from different audio/clocks/languages: ' + key)
    comparisons = []
    for index, (st, en) in enumerate(ranges):
        chunks = {name: read(output / name / f'chunk_{index:06}.json') for name in transcripts}
        texts = {name: ' '.join(s['text'] for s in chunk['segments']) for name, chunk in chunks.items()}
        row = dict(start=st, end=en, **texts, **compare_texts(texts['whisper'], texts['meta']))
        row['warnings'] = {name: chunk['warnings'] for name, chunk in chunks.items() if chunk['warnings']}
        if row['warnings']:
            row['review_required'] = True
        comparisons.append(row)
    return {'schema_version': 1, 'algorithm': ALGORITHM, 'clock': left['clock'],
            'range': left['range'], 'audio_signature': left['audio_signature'],
            'complete': left['complete'] and right['complete'], 'machine_draft': True,
            'automatic_winner': None, 'human_review_required': True,
            'metric_note': 'Word disagreement between two hypotheses, NOT WER, accuracy or truth. '
                           'Agreement can still be wrong; review silence, names and overlapping speech.',
            'engines': {name: {k: data[k] for k in ['model', 'engine', 'decode_seconds', 'real_time_factor', 'timing_note']}
                        for name, data in transcripts.items()},
            'summary': {'windows': len(comparisons),
                        'review_windows': sum(c['review_required'] for c in comparisons),
                        'word_disagreement': sum(c['word_edits'] for c in comparisons) /
                            max(1, sum(max(c['whisper_word_count'], c['meta_word_count']) for c in comparisons))},
            'windows': comparisons}


def write_html(path, report, audio, origin):
    escape = html.escape
    audio_url = Path(os.path.relpath(audio, path.parent)).as_posix()
    from urllib.parse import quote
    cards = []
    for row in report['windows']:
        notes = '<br>'.join(escape(f'{d["whisper"] or "∅"} ↔ {d["meta"] or "∅"}') for d in row['differences'])
        warnings = '<br>'.join(escape(f'{name}: {message}') for name, messages in row.get('warnings', {}).items()
                               for message in messages)
        label = 'შესამოწმებელია / Review' if row['review_required'] else 'ტექსტები ემთხვევა / Match'
        cards.append(f'''<section><header><button data-seek="{row['start'] - origin:.3f}">{stamp(row['start'])}</button>
          → {stamp(row['end'])} · {label} · სხვაობა / disagreement: {row['word_disagreement']:.0%}</header>
          <div class="pair"><article><h3>Whisper</h3><p>{escape(row['whisper']) or '∅'}</p></article>
          <article><h3>Meta Omnilingual</h3><p>{escape(row['meta']) or '∅'}</p></article></div>
          <p>{warnings}</p><details><summary>განსხვავებული სიტყვები / Differences</summary><p>{notes or '—'}</p></details></section>''')
    details = ''.join(f'<li>{escape(name)}: {escape(e["model"])} · {e["decode_seconds"]:.1f}s '
                      f'· RTF {e["real_time_factor"]:.2f}</li>' for name, e in report['engines'].items())
    page = '''<!doctype html><html lang="ka"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
    <title>Podcut Flow · Whisper + Meta</title><style>
    body{margin:auto;max-width:1100px;padding:24px;background:#f1f5f9;color:#142432;font:17px/1.65 system-ui,sans-serif}
    h1{line-height:1.2} .notice,section{background:white;border-radius:14px;padding:22px;margin:18px 0}
    header{font-weight:600;color:#126d64}.pair{display:grid;grid-template-columns:1fr 1fr;gap:24px}
    article{min-width:0}p{overflow-wrap:anywhere}button{border:0;border-radius:7px;background:#d9f5ed;padding:8px;cursor:pointer}
    audio{width:100%}h3{margin-bottom:8px}details{border-top:1px solid #ddd;padding-top:12px}
    .player{position:sticky;top:0;background:#f1f5f9;padding:10px 0} @media(max-width:650px){.pair{grid-template-columns:1fr}}
    </style><h1>Whisper + Meta<br>ტრანსკრიპტების შედარება</h1>
    <div class="notice">ორივე ტექსტი ავტომატური მონახაზია. თანხვედრა სისწორის გარანტია არ არის.
    განსხვავების პროცენტი მოდელებს ადარებს; ეს არ არის სიზუსტის შეფასება.
    ტაიმკოდზე დაჭერით მოუსმინე ჩანაწერს. Meta-ს სიტყვების დრო მიახლოებითია.
    <br>Both texts and timings need review. No automatic winner or merged transcript.</div>'''
    page += f'<ul>{details}</ul><p>Clock: {escape(report["clock"])} · Range: {stamp(report["range"][0])}–{stamp(report["range"][1])}</p>'
    page += f'<div class="player"><audio id="audio" controls preload="metadata" src="{escape(quote(audio_url, safe="/.:"))}"></audio></div>'
    page += ''.join(cards)
    page += '''<script>document.querySelectorAll('[data-seek]').forEach(b=>b.addEventListener('click',()=>{
    const a=document.getElementById('audio');a.currentTime=Number(b.dataset.seek);a.play().catch(()=>{});}));</script></html>'''
    path.write_text(page, encoding='utf-8')


def interval(start, duration, full):
    if not math.isfinite(start) or start < 0 or (duration is not None and (not math.isfinite(duration) or duration <= 0)):
        raise ValueError('Specify a finite nonnegative start and positive duration.')
    end = min(full, start + duration if duration is not None else full)
    if not start < end:
        raise ValueError('Invalid transcription interval')
    return end


def compare_project(project, model='small', language=None, start=0., duration=None,
                    allow_download=False, device='cpu'):
    p, root = load(project)
    language = language or p['decisions'].get('language')
    if not language:
        raise ValueError('Specify the spoken language before transcription.')
    with worker(root):
        models = resolve_models(model, allow_download, device)
        audio = asr_audio(p, root)
        full = sf.info(audio).duration
        end = interval(start, duration, full)
        signature = digest([asr_signature(p), models, language, start, end, ALGORITHM])
        output = root / 'transcripts' / ('dual_' + signature[:12])
        report = run_engines(audio, 0, start, end, output, models, language, asr_signature(p),
                             full, 'reference recording seconds')
        write(root / 'transcript_comparison_latest.json', {'path': str(report), 'signature': signature})
        # Preserve the existing retiming path. Meta remains independent, never silently merged.
        write(root / 'transcript_latest.json', {'path': str(output / 'whisper' / 'reference.json'),
                                              'complete': read(report)['complete'], 'signature': signature})
        state(root, 'transcript_review', 'Whisper + Meta drafts and comparison saved. Review differences by listening; '
              'Whisper is the editable baseline, not an automatically selected winner.')
        return report


def compare_audio(audio, model='small', language=None, start=0., duration=40.,
                  allow_download=False, device='cpu'):
    """A bounded test on one explicitly supplied recording, without episode intake/editing."""
    audio = Path(audio).expanduser().resolve()
    if not language:
        raise ValueError('Specify --language for the sample.')
    if duration is None:
        raise ValueError('A standalone comparison requires --seconds; use a project for a full episode.')
    info = probe(audio)
    full = float(info['format']['duration'])
    end = interval(start, duration, full)
    root = audio.parent / '.podcut'
    root.mkdir(exist_ok=True)
    with worker(root):
        models = resolve_models(model, allow_download, device)
        audio_signature = digest(fingerprint(audio))
        signature = digest([audio_signature, models, language, start, end, ALGORITHM, 'file-sample'])
        output = root / 'asr-tests' / signature[:12]
        output.mkdir(parents=True, exist_ok=True)
        sample = output / 'sample.wav'
        if not sample.exists():
            temp = output / 'sample.partial.wav'
            ffmpeg(['-y', '-ss', str(start), '-i', str(audio), '-t', str(end - start),
                    '-map', '0:a:0', '-vn', '-ac', '1', '-ar', '16000', '-c:a', 'pcm_s16le', str(temp)])
            temp.replace(sample)
        if abs(sf.info(sample).duration - (end - start)) > .05:
            raise ValueError('Extracted sample duration mismatch; inspect the source audio stream.')
        return run_engines(sample, start, start, end, output, models, language, audio_signature,
                           full, 'source file seconds')
