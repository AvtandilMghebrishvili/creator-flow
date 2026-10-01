/**
 * Check the toolchain before anything else. Run this first, and again whenever
 * something behaves oddly — a stale yt-dlp is the most common cause of sudden
 * failures, because YouTube changes break extraction.
 *
 *   node scripts/doctor.js
 */
import { execFileSync } from 'node:child_process';
import fs from 'node:fs';
import { TOOLS, FONTS, DATA, ROOT, ensureDirs, pickFont } from './lib/paths.js';

ensureDirs();

const rows = [];

function probe(name, cmd, versionArgs) {
  const bundled = cmd.includes('/') || cmd.includes('\\');
  if (bundled && !fs.existsSync(cmd)) return rows.push([name, 'MISSING', cmd]);
  try {
    const out = execFileSync(cmd, versionArgs, {
      encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'],
    });
    rows.push([name, 'ok', out.trim().split('\n')[0].slice(0, 58)]);
  } catch (e) {
    const out = ((e.stdout || '') + (e.stderr || '')).trim();
    // ffmpeg -version exits non-zero in some shells but still prints its banner.
    if (out) rows.push([name, 'ok', out.split('\n')[0].slice(0, 58)]);
    else rows.push([name, 'MISSING', bundled ? cmd : `${cmd} not on PATH`]);
  }
}

probe('ffmpeg',  TOOLS.ffmpeg,  ['-hide_banner', '-version']);
probe('ffprobe', TOOLS.ffprobe, ['-hide_banner', '-version']);
probe('yt-dlp',  TOOLS.ytdlp,   ['--version']);

// libass is required for the subtitles filter; without it captions silently vanish.
try {
  const cfg = execFileSync(TOOLS.ffmpeg, ['-hide_banner', '-filters'], { encoding: 'utf8' });
  rows.push(['libass (subtitles)', cfg.includes('subtitles') ? 'ok' : 'MISSING',
    cfg.includes('subtitles') ? 'subtitles filter present' : 'rebuild ffmpeg with libass']);
} catch { rows.push(['libass (subtitles)', 'unknown', '-']); }

try {
  const enc = execFileSync(TOOLS.ffmpeg, ['-hide_banner', '-encoders'], { encoding: 'utf8' });
  const gpu = enc.includes('h264_nvenc');
  rows.push(['GPU encode', gpu ? 'ok' : 'cpu only', gpu ? 'h264_nvenc' : 'falls back to libx264']);
} catch { rows.push(['GPU encode', 'unknown', '-']); }

const font = pickFont();
rows.push(['caption font', font.file ? 'ok' : 'MISSING',
  font.file ? `${font.family}` : `no .ttf in ${FONTS.dir}`]);

// Optional — only needed for footage not yet uploaded.
rows.push(['whisper (optional)', fs.existsSync(TOOLS.whisper) ? 'ok' : 'absent',
  fs.existsSync(TOOLS.model) ? 'model present' : 'not needed for uploaded video']);

const w = [0, 1].map((i) => Math.max(...rows.map((r) => String(r[i]).length)));
console.log(`\nproject root: ${ROOT}\n`);
for (const [n, s, d] of rows) {
  console.log(`  ${s === 'MISSING' ? 'x' : 'v'} ${String(n).padEnd(w[0])}  ${String(s).padEnd(w[1])}  ${d}`);
}

const missing = rows.filter((r) => r[1] === 'MISSING');
console.log(missing.length
  ? `\n${missing.length} missing — see references/setup.md\n`
  : '\nAll required tools present.\n');
process.exit(missing.length ? 1 : 0);
