/** Check archive dependencies without creating data directories or downloading media. */
import { execFileSync } from 'node:child_process';
import { TOOLS, ROOT } from './lib/paths.js';

const rows = [];
rows.push(['Node', Number(process.versions.node.split('.')[0]) >= 22, process.versions.node]);
for (const [name, command, args] of [
  ['ffmpeg', TOOLS.ffmpeg, ['-version']],
  ['ffprobe', TOOLS.ffprobe, ['-version']],
  ['yt-dlp', TOOLS.ytdlp, ['--version']],
]) {
  try {
    const output = execFileSync(command, args, { encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'], timeout: 20000 });
    rows.push([name, true, output.trim().split('\n')[0].slice(0, 90)]);
  } catch {
    rows.push([name, false, 'missing or failed to run']);
  }
}
console.log(`Archive workspace: ${ROOT}`);
for (const [name, ok, detail] of rows) console.log(`${ok ? 'ok' : 'MISSING'}  ${name}: ${detail}`);
console.log('New transcription uses Meta via creator-flow transcribe. Fonts are chosen during clip review.');
console.log('This checks local tools, not live YouTube access, speech weights or caption quality.');
process.exit(rows.every(([, ok]) => ok) ? 0 : 1);
