import path from 'node:path';
import fs from 'node:fs';

/**
 * Project root = where the pipeline keeps tools/ and data/.
 * Defaults to the current working directory so the skill can be dropped into any
 * project; override with YTC_ROOT when running from elsewhere.
 */
export const ROOT = process.env.YTC_ROOT || process.cwd();

const exe = (n) => (process.platform === 'win32' ? `${n}.exe` : n);

/** Prefer a bundled portable tool, fall back to whatever is on PATH. */
function tool(relative, name) {
  const local = path.join(ROOT, relative);
  return fs.existsSync(local) ? local : name;
}

export const TOOLS = {
  ffmpeg:  tool(path.join('tools', 'ffmpeg', 'bin', exe('ffmpeg')), 'ffmpeg'),
  ffprobe: tool(path.join('tools', 'ffmpeg', 'bin', exe('ffprobe')), 'ffprobe'),
  ytdlp:   tool(path.join('tools', exe('yt-dlp')), 'yt-dlp'),
  whisper: path.join(ROOT, 'tools', 'whisper', 'Release', exe('whisper-cli')),
  model:   path.join(ROOT, 'tools', 'whisper', 'models', 'ggml-large-v3.bin'),
};

export const FONTS = { dir: path.join(ROOT, 'assets', 'fonts') };

/** First matching font family present in assets/fonts, for the ASS style. */
export function pickFont(preferred = ['NotoSansGeorgian-ExtraBold', 'NotoSansGeorgian-Black']) {
  if (!fs.existsSync(FONTS.dir)) return { file: null, family: 'Arial' };
  const files = fs.readdirSync(FONTS.dir).filter((f) => /\.(ttf|otf)$/i.test(f));
  const hit = preferred.find((p) => files.some((f) => f.startsWith(p))) ?? null;
  if (!hit) return { file: files[0] ?? null, family: 'Arial' };
  // libass matches on family name. Noto static instances name the family
  // "Noto Sans Georgian ExtraBold" — the base is camelCase, the weight suffix is not,
  // so only split the part before the hyphen.
  const [base, ...rest] = hit.split('-');
  const family = [base.replace(/([a-z])([A-Z])/g, '$1 $2'), ...rest].join(' ');
  return { file: path.join(FONTS.dir, `${hit}.ttf`), family };
}

export const DATA = {
  raw:         path.join(ROOT, 'data', 'raw'),
  audio:       path.join(ROOT, 'data', 'audio'),
  transcripts: path.join(ROOT, 'data', 'transcripts'),
  clips:       path.join(ROOT, 'data', 'clips'),
  out:         path.join(ROOT, 'data', 'out'),
};

export function ensureDirs() {
  for (const d of Object.values(DATA)) fs.mkdirSync(d, { recursive: true });
}

/** ffmpeg filter arguments need Windows paths escaped: D:\x -> D\:/x */
export const ffPath = (p) => p.replace(/\\/g, '/').replace(/:/g, '\\:');

export const ts = (ms) => {
  const s = Math.round(ms / 1000);
  return `${String(Math.floor(s / 60)).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`;
};
