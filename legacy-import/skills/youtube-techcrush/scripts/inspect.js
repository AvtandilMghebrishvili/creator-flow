/**
 * Read a transcript span with exact timestamps, to set clip in/out points on a real
 * sentence boundary. The 42-second scoring window is an arbitrary grid — the clip
 * should not inherit its edges.
 *
 *   node scripts/inspect.js --video <videoId> --from 600 --to 665
 */
import { loadTranscript } from './lib/segment.js';
import { ts } from './lib/paths.js';
import { parseArgs, requireArg, isMain } from './lib/args.js';

export function inspect(id, fromSec, toSec) {
  const { words } = loadTranscript(id);
  const span = words.filter((x) => x.ms >= fromSec * 1000 && x.ms <= toSec * 1000);
  const lines = [];
  let cur = null;
  for (const x of span) {
    // Start a new line on a pause or when the current one gets long enough to read.
    if (!cur || x.ms - cur.ms > 3000 || cur.t.length > 90) { cur = { ms: x.ms, t: '' }; lines.push(cur); }
    cur.t += (cur.t ? ' ' : '') + x.t;
  }
  return lines.map((l) => `${ts(l.ms)} (${(l.ms / 1000).toFixed(1)}s)  ${l.t}`).join('\n');
}

if (isMain(import.meta.url)) {
  const args = parseArgs();
  const usage = 'Usage: node scripts/inspect.js --video <id> --from <sec> --to <sec>';
  console.log(inspect(
    requireArg(args, 'video', usage),
    Number(requireArg(args, 'from', usage)),
    Number(requireArg(args, 'to', usage)),
  ));
}
