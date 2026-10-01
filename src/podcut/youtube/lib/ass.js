/**
 * ASS subtitle generation with word-by-word highlighting (the TikTok/Shorts look).
 *
 * Each line emits one dialogue event per word, re-colouring the active word inline,
 * rather than using \k karaoke timing. It is more verbose but far more predictable
 * in libass and gives full control over colours.
 *
 * ASS colours are &HBBGGRR& — blue and red are swapped relative to the hex you would
 * write for CSS. This trips everyone up once.
 */

const HL = '&H0027E1F5&';   // amber highlight
const FG = '&H00FFFFFF&';   // white

/** Group words into short lines. 3-4 words is the readable maximum at Shorts size. */
export function toLines(words, perLine = 4, maxGapMs = 1400) {
  const lines = [];
  let cur = [];
  for (const w of words) {
    const gap = cur.length ? w.ms - cur.at(-1).ms : 0;
    // Break on a long pause too — it usually marks a sentence boundary.
    if (cur.length >= perLine || (cur.length && gap > maxGapMs)) { lines.push(cur); cur = []; }
    cur.push(w);
  }
  if (cur.length) lines.push(cur);
  return lines;
}

const cs = (ms) => {
  const t = Math.max(0, Math.round(ms / 10));
  const h = Math.floor(t / 360000), m = Math.floor((t % 360000) / 6000);
  const s = Math.floor((t % 6000) / 100), c = t % 100;
  return `${h}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}.${String(c).padStart(2, '0')}`;
};

const esc = (s) => s.replace(/[{}\\]/g, '').replace(/\n/g, ' ');

/**
 * YouTube caption tracks carry '>>' speaker-change markers and bracketed sound tags
 * like [laughter]. Both are useful for scoring clips and embarrassing on screen.
 */
export function cleanWords(words) {
  return words
    .map((w) => ({ ...w, t: w.t.replace(/>>/g, '').replace(/\[[^\]]*\]/g, '').trim() }))
    .filter((w) => w.t.length > 0);
}

/**
 * @param {Array<Array<{t:string,ms:number}>>} lines  from toLines(); ms relative to clip start
 * @param {number} endMs                              clip duration in ms
 */
export function buildAss(lines, endMs, {
  fontName = 'Noto Sans Georgian ExtraBold',
  fontSize = 74,
  // Measured from the bottom. Below ~500 the captions collide with the Shorts UI
  // (like/comment/share rail, channel name, description).
  marginV = 580,
  playResX = 1080, playResY = 1920,
} = {}) {
  const header = `[Script Info]
ScriptType: v4.00+
PlayResX: ${playResX}
PlayResY: ${playResY}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,${fontName},${fontSize},${FG},${FG},&H00000000&,&H96000000&,0,0,0,0,100,100,0,0,1,6,3,2,60,60,${marginV},1
Style: Hook,${fontName},62,${FG},${FG},&H00000000&,&HC8000000&,0,0,0,0,100,100,0,0,3,26,0,5,110,110,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
`;

  const events = [];
  for (let i = 0; i < lines.length; i++) {
    const ln = lines[i];
    // Hold the finished line briefly, but never past the next line's first word.
    const lineEnd = i + 1 < lines.length
      ? Math.min(lines[i + 1][0].ms, ln.at(-1).ms + 1500)
      : endMs;
    for (let j = 0; j < ln.length; j++) {
      const st = ln[j].ms;
      const en = j + 1 < ln.length ? ln[j + 1].ms : lineEnd;
      if (en <= st) continue;
      const txt = ln
        .map((w, k) => (k === j ? `{\\c${HL}}${esc(w.t)}{\\c${FG}}` : esc(w.t)))
        .join(' ');
      events.push(`Dialogue: 0,${cs(st)},${cs(en)},Cap,,0,0,0,,${txt}`);
    }
  }
  return { header, events };
}

/** Centred hook overlay for the opening seconds. Use '|' to force a line break. */
export function hookEvent(text, fromMs, toMs) {
  const t = esc(text).replace(/\|/g, '\\N');
  return `Dialogue: 1,${cs(fromMs)},${cs(toMs)},Hook,,0,0,0,,{\\fad(200,250)}${t}`;
}
