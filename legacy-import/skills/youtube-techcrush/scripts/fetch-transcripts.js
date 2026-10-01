/**
 * Pull YouTube's own captions with word-level timestamps. Free, no API key, no quota.
 *
 *   node scripts/fetch-transcripts.js --channel "https://www.youtube.com/@Handle"
 *   node scripts/fetch-transcripts.js --video <videoId>
 *   node scripts/fetch-transcripts.js --channel <url> --tab shorts
 *   node scripts/fetch-transcripts.js --channel <url> --langs "en-orig,en"
 *
 * Prefer '<lang>-orig' over the bare code: the bare track may be a machine
 * translation that round-trips through English and loses accuracy.
 */
import { execFileSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import { TOOLS, DATA, ensureDirs } from './lib/paths.js';
import { parseArgs, isMain } from './lib/args.js';

const USAGE = `Usage:
  node scripts/fetch-transcripts.js --channel <url> [--tab videos|shorts] [--langs "ka-orig,ka"]
  node scripts/fetch-transcripts.js --video <videoId> [--langs ...]`;

const ytdlp = (args) =>
  execFileSync(TOOLS.ytdlp, args, {
    encoding: 'utf8', maxBuffer: 256 * 1024 * 1024, stdio: ['ignore', 'pipe', 'ignore'],
  });

/** Flat channel listing — metadata only, no downloads. */
export function listChannel(channelUrl, tab = 'videos') {
  const raw = ytdlp(['--flat-playlist', '-J', '--no-warnings', `${channelUrl.replace(/\/$/, '')}/${tab}`]);
  return JSON.parse(raw).entries.map((e) => ({
    id: e.id,
    title: e.title,
    views: e.view_count ?? 0,
    duration: e.duration ?? null,
  }));
}

/** json3 caption events -> flat [{t, ms}] word stream. */
function parseJson3(file) {
  const j = JSON.parse(fs.readFileSync(file, 'utf8'));
  const words = [];
  for (const e of j.events ?? []) {
    if (!e.segs) continue;
    for (const s of e.segs) {
      const t = (s.utf8 ?? '').replace(/\n/g, ' ').trim();
      if (t) words.push({ t, ms: e.tStartMs + (s.tOffsetMs ?? 0) });
    }
  }
  return words;
}

export function fetchTranscript(id, title = '', langs = 'ka-orig,ka,en-orig,en') {
  ensureDirs();
  const out = path.join(DATA.transcripts, `${id}.json`);
  if (fs.existsSync(out)) return JSON.parse(fs.readFileSync(out, 'utf8'));

  const tmp = path.join(DATA.transcripts, `_tmp_${id}`);
  try {
    ytdlp([
      '--skip-download', '--write-auto-subs', '--write-subs',
      '--sub-langs', langs, '--sub-format', 'json3',
      '--no-warnings', '-o', `${tmp}.%(ext)s`,
      `https://www.youtube.com/watch?v=${id}`,
    ]);
  } catch {
    // Some videos have captions disabled entirely; fall through to the miss path.
  }

  const wanted = langs.split(',').map((l) => `${tmp}.${l.trim()}.json3`);
  const found = wanted.find((f) => fs.existsSync(f));
  if (!found) return null;

  const doc = {
    id, title,
    source: path.basename(found).replace(`_tmp_${id}.`, '').replace('.json3', ''),
    words: parseJson3(found),
  };
  doc.wordCount = doc.words.length;
  fs.writeFileSync(out, JSON.stringify(doc));
  for (const f of wanted) if (fs.existsSync(f)) fs.unlinkSync(f);
  return doc;
}

if (isMain(import.meta.url)) {
  const args = parseArgs();
  const langs = typeof args.langs === 'string' ? args.langs : 'ka-orig,ka,en-orig,en';
  ensureDirs();

  let videos;
  if (typeof args.video === 'string') {
    videos = [{ id: args.video, title: '(single)' }];
  } else if (typeof args.channel === 'string') {
    videos = listChannel(args.channel, typeof args.tab === 'string' ? args.tab : 'videos');
    fs.writeFileSync(path.join(DATA.transcripts, '_index.json'), JSON.stringify(videos, null, 2));
    console.log(`${videos.length} videos on channel\n`);
  } else {
    console.error(USAGE);
    process.exit(1);
  }

  let ok = 0, miss = 0;
  for (const v of videos) {
    const d = fetchTranscript(v.id, v.title, langs);
    if (d) { ok++; console.log(`  ok   ${String(d.wordCount).padStart(6)} words  [${d.source}]  ${v.id}  ${v.title.slice(0, 45)}`); }
    else   { miss++; console.log(`  --   no captions            ${v.id}  ${v.title.slice(0, 45)}`); }
  }
  console.log(`\n${ok} transcripts, ${miss} skipped -> ${DATA.transcripts}`);
}
