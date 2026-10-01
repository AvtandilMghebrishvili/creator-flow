import fs from 'node:fs';
import path from 'node:path';
import { DATA } from './paths.js';

/** Slide a window across the word stream. Overlapping by design — a good moment
 *  rarely aligns to a fixed grid, so we oversample and dedupe later. */
export function windows(words, { lenMs = 42_000, stepMs = 12_000, minWords = 25 } = {}) {
  if (!words.length) return [];
  const end = words.at(-1).ms;
  const out = [];
  for (let s = 0; s + lenMs <= end + stepMs; s += stepMs) {
    const w = words.filter((x) => x.ms >= s && x.ms < s + lenMs);
    if (w.length < minWords) continue;
    out.push({ startMs: s, endMs: s + lenMs, text: w.map((x) => x.t).join(' '), n: w.length });
  }
  return out;
}

/**
 * Scoring signals. These are a *starting point* — edit them per channel using what
 * channel-stats.js reports, because the whole point is to weight toward what has
 * actually worked rather than what sounds interesting.
 *
 * Weights below are tuned for a Georgian tech/space podcast: concrete story and
 * space/NASA content outperformed abstract technology commentary by ~6x, so
 * abstract commentary carries a penalty rather than merely a low weight.
 */
export const DEFAULT_SIGNALS = [
  { k: 'space/NASA',     w: 5.0, re: /(?<![\p{L}\p{N}_])(ნასა|nasa|კოსმოს|რაკეტ|ვოიაჯერ|მარს|პლანეტ|სკაფანდრ|ორბიტ|ასტრონავტ|სატელიტ|ტელესკოპ|გალაქტიკ|ვარსკვლავ|jpl|voyager|rocket|orbit|astronaut)/iu },
  { k: 'local identity', w: 3.0, re: /(?<![\p{L}\p{N}_])(ქართველ|ქართულ|საქართველო|თბილის|ჩაკრულო|ერისიონ|სამშობლო|ჩვენი ქვეყ)/iu },
  { k: 'concrete story', w: 2.5, re: /(?<![\p{L}\p{N}_])(მახსოვს|პირველად|იმ დღეს|ბავშვობა|მაშინ როცა|არასდროს დამავიწყდ|შემეშინდა|ვიტირე|გამიკვირდა|i remember|the first time|that day)/iu },
  { k: 'conflict/drama', w: 2.5, re: /(?<![\p{L}\p{N}_])(პანიკა|შეცდომ|ჩავარდ|დამარცხ|უარი|აკრძალ|ომ[იმს]|დაანგრი|დაწვ|საშიშ|რისკ|კრიზის|წააგ|panic|refused|banned|failed|crisis)/iu },
  { k: 'number/scale',   w: 1.5, re: /(?<![\p{L}\p{N}_])\d{2,}\s?(მილიონ|მილიარდ|ათას|წლ|კილომეტრ|პროცენტ|ჯერ|million|billion|thousand|percent|years)/iu },
  { k: 'direct address', w: 1.2, re: /\?|წარმოიდგინე|იცოდ[ით]|გინდა|imagine|did you know/iu },
  { k: 'named authority', w: 1.2, re: /(?<![\p{L}\p{N}_])(სეიგან|მასკ|ალტმან|sagan|musk|altman|google|nvidia|openai|princeton|harvard|mit)/iu },
  { k: 'abstract (penalty)', w: -2.0, re: /(?<![\p{L}\p{N}_])(ხელოვნური ინტელექტი (განვითარდ|ვითარდ)|ტექნოლოგიები ვითარდება|მომავალი იქნება|უნდა ვისწავლოთ|ai is developing|the future will be|we need to learn)/iu },
];

export function score(text, signals = DEFAULT_SIGNALS) {
  const hits = [];
  let s = 0;
  for (const sig of signals) {
    const m = text.match(new RegExp(sig.re.source, 'giu'));
    if (!m) continue;
    // Saturate: three mentions of "NASA" is not three times as good as one.
    const n = Math.min(m.length, 3);
    s += sig.w * (1 + (n - 1) * 0.35);
    hits.push(`${sig.k}x${m.length}`);
  }
  // Speaker changes mark live exchange; too many mark a fragmented conversation
  // that will not read as a single coherent clip.
  const turns = (text.match(/>>/g) || []).length;
  if (turns >= 1 && turns <= 3) s += 1.0;
  if (turns > 4) s -= 1.5;
  return { score: +s.toFixed(2), hits };
}

export const loadTranscript = (id) =>
  JSON.parse(fs.readFileSync(path.join(DATA.transcripts, `${id}.json`), 'utf8'));

export const loadIndex = () =>
  JSON.parse(fs.readFileSync(path.join(DATA.transcripts, '_index.json'), 'utf8'));
