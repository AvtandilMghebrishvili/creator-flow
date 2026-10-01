/**
 * Score transcript windows and shortlist candidate moments.
 *
 *   node scripts/find-candidates.js --video <videoId> [--limit 10]
 *   node scripts/find-candidates.js --all [--limit 3]
 *
 * The score is a FILTER, not a verdict. It reliably narrows hundreds of thousands of
 * words to a few dozen windows worth reading, and just as reliably rates some
 * abstract, meandering passages highly because they contain the right nouns.
 * Read every candidate before offering it to anyone.
 */
import fs from 'node:fs';
import path from 'node:path';
import { DATA, ts, ensureDirs } from './lib/paths.js';
import { windows, score, loadTranscript, loadIndex } from './lib/segment.js';
import { parseArgs, isMain } from './lib/args.js';

/** Greedy pick by score, skipping anything that overlaps an already-chosen window. */
function pickNonOverlapping(scored, limit, minGapMs = 40_000) {
  const chosen = [];
  for (const w of [...scored].sort((a, b) => b.score - a.score)) {
    if (chosen.some((c) => Math.abs(c.startMs - w.startMs) < minGapMs)) continue;
    chosen.push(w);
    if (chosen.length >= limit) break;
  }
  return chosen;
}

export function candidatesFor(id, title, limit = 8) {
  const tr = loadTranscript(id);
  const scored = windows(tr.words)
    .map((w) => ({ ...w, ...score(w.text) }))
    .filter((w) => w.score > 0);
  return pickNonOverlapping(scored, limit).map((w) => ({
    videoId: id,
    videoTitle: title,
    start: ts(w.startMs), end: ts(w.endMs),
    startMs: w.startMs, endMs: w.endMs,
    startSec: Math.round(w.startMs / 1000), endSec: Math.round(w.endMs / 1000),
    score: w.score, hits: w.hits, text: w.text,
  }));
}

if (isMain(import.meta.url)) {
  const args = parseArgs();
  ensureDirs();
  const limit = Number(args.limit) || (args.all ? 3 : 10);

  let targets;
  if (args.all) {
    targets = loadIndex();
  } else if (typeof args.video === 'string') {
    const idx = fs.existsSync(path.join(DATA.transcripts, '_index.json')) ? loadIndex() : [];
    targets = [idx.find((v) => v.id === args.video) ?? { id: args.video, title: '(single)' }];
  } else {
    console.error('Usage: node scripts/find-candidates.js (--video <id> | --all) [--limit N]');
    process.exit(1);
  }

  const all = [];
  for (const v of targets) {
    try { all.push(...candidatesFor(v.id, v.title ?? '', limit)); }
    catch { console.error(`  (no transcript for ${v.id} — run fetch-transcripts.js first)`); }
  }
  all.sort((a, b) => b.score - a.score);

  const out = path.join(DATA.clips, args.all ? 'candidates-all.json' : `candidates-${args.video}.json`);
  fs.writeFileSync(out, JSON.stringify(all, null, 2));

  for (const c of all.slice(0, 30)) {
    console.log(`\n[${c.score}] ${c.start}-${c.end}  ${c.videoId}  ${(c.videoTitle || '').slice(0, 45)}`);
    console.log(`  signals: ${c.hits.join(', ')}`);
    console.log(`  ${c.text.slice(0, 320)}...`);
  }
  console.log(`\n\n${all.length} candidates -> ${out}`);
  console.log('Next: read them, refine boundaries with inspect.js, then write hooks.');
}
