/**
 * Render a clip to 1080x1920 with burned-in word-by-word captions.
 *
 *   node scripts/render-short.js --video <id> --start 605 --end 652 \
 *        --hook "First line|Second line" --out clip-name [--layout blur|crop]
 *
 * Default layout is 'blur': blurred background with the complete 16:9 frame inset.
 * A centre crop looks better on close-ups but amputates both speakers on the wide
 * two-shots every podcast edit contains — use --layout crop only for single-speaker
 * source. See references/rendering.md.
 */
import { execFileSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import { TOOLS, FONTS, DATA, ensureDirs, ffPath, pickFont } from './lib/paths.js';
import { loadTranscript } from './lib/segment.js';
import { toLines, buildAss, hookEvent, cleanWords } from './lib/ass.js';
import { parseArgs, requireArg, isMain } from './lib/args.js';

const HOOK_MS = 2600;
const PAD = 6;   // download a little either side so keyframe cuts do not clip speech

function hasNvenc() {
  try {
    return execFileSync(TOOLS.ffmpeg, ['-hide_banner', '-encoders'], { encoding: 'utf8' })
      .includes('h264_nvenc');
  } catch { return false; }
}

function filters(layout, assFile) {
  const subs = `subtitles='${ffPath(assFile)}':fontsdir='${ffPath(FONTS.dir)}'`;
  if (layout === 'crop') {
    return `[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920[base];[base]${subs}[v]`;
  }
  return [
    `[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,gblur=sigma=42,eq=brightness=-0.22[bg]`,
    `[0:v]scale=1080:-2[fg]`,
    `[bg][fg]overlay=(W-w)/2:430[base]`,
    `[base]${subs}[v]`,
  ].join(';');
}

export function render({ videoId, startSec, endSec, hook = '', outName, layout = 'blur' }) {
  ensureDirs();
  const dur = endSec - startSec;
  if (!(dur > 0)) throw new Error('--end must be greater than --start');

  const dlStart = Math.max(0, startSec - PAD);
  const src = path.join(DATA.raw, `${videoId}_${dlStart}.mp4`);

  if (!fs.existsSync(src)) {
    console.log(`downloading ${dlStart}-${endSec + PAD}s ...`);
    execFileSync(TOOLS.ytdlp, [
      '-f', 'bv*[height<=1080][ext=mp4]+ba[ext=m4a]/b[height<=1080]',
      '--download-sections', `*${dlStart}-${endSec + PAD}`, '--force-keyframes-at-cuts',
      '--ffmpeg-location', path.dirname(TOOLS.ffmpeg),
      '--merge-output-format', 'mp4', '--no-warnings', '--quiet', '--no-progress',
      '-o', src.replace(/\.mp4$/, '.%(ext)s'),
      `https://www.youtube.com/watch?v=${videoId}`,
    ], { stdio: 'inherit' });
  }

  // Words for this clip, rebased to zero and stripped of caption artifacts.
  const { words } = loadTranscript(videoId);
  const inClip = cleanWords(
    words
      .filter((w) => w.ms >= startSec * 1000 && w.ms < endSec * 1000)
      .map((w) => ({ ...w, ms: w.ms - startSec * 1000 }))
  );

  const font = pickFont();
  const { header, events } = buildAss(toLines(inClip), dur * 1000, { fontName: font.family });
  const ass = path.join(DATA.clips, `${outName}.ass`);
  const body = hook ? [hookEvent(hook, 0, HOOK_MS), ...events] : events;
  fs.writeFileSync(ass, header + body.join('\n') + '\n', 'utf8');

  const out = path.join(DATA.out, `${outName}.mp4`);
  const vcodec = hasNvenc()
    ? ['-c:v', 'h264_nvenc', '-preset', 'p5', '-cq', '20']
    : ['-c:v', 'libx264', '-preset', 'medium', '-crf', '20'];

  console.log(`rendering -> ${out}  [${layout}, ${vcodec[1]}, font: ${font.family}]`);
  execFileSync(TOOLS.ffmpeg, [
    '-y', '-v', 'error', '-stats',
    '-ss', String(startSec - dlStart), '-t', String(dur), '-i', src,
    '-filter_complex', filters(layout, ass), '-map', '[v]', '-map', '0:a',
    ...vcodec, '-pix_fmt', 'yuv420p',
    '-c:a', 'aac', '-b:a', '192k', '-ar', '48000',
    '-movflags', '+faststart', out,
  ], { stdio: 'inherit' });

  return out;
}

/** Pull frames so the result can actually be looked at before anyone sees it. */
export function extractFrames(mp4, times = [1, 8, 20, 33], dir = DATA.out) {
  const made = [];
  for (const t of times) {
    const jpg = path.join(dir, `${path.basename(mp4, '.mp4')}_f${t}.jpg`);
    try {
      execFileSync(TOOLS.ffmpeg, ['-y', '-v', 'error', '-ss', String(t), '-i', mp4,
        '-frames:v', '1', '-vf', 'scale=460:-1', jpg]);
      made.push(jpg);
    } catch { /* past the end of the clip */ }
  }
  return made;
}

if (isMain(import.meta.url)) {
  const args = parseArgs();
  const usage = 'Usage: node scripts/render-short.js --video <id> --start <sec> --end <sec> [--hook "a|b"] [--out name] [--layout blur|crop]';
  const videoId = requireArg(args, 'video', usage);
  const startSec = Number(requireArg(args, 'start', usage));
  const endSec = Number(requireArg(args, 'end', usage));

  const out = render({
    videoId, startSec, endSec,
    hook: typeof args.hook === 'string' ? args.hook : '',
    outName: typeof args.out === 'string' ? args.out : `${videoId}_${startSec}-${endSec}`,
    layout: args.layout === 'crop' ? 'crop' : 'blur',
  });

  const mb = (fs.statSync(out).size / 1024 / 1024).toFixed(1);
  const frames = extractFrames(out);
  console.log(`\ndone: ${out}  (${mb} MB)`);
  console.log(`frames for review:\n  ${frames.join('\n  ')}`);
  console.log('\nLook at the frames before showing this to anyone. Text overflow, caption');
  console.log('collisions and wrong font weight are silent failures — ffmpeg exits 0 anyway.');
}
