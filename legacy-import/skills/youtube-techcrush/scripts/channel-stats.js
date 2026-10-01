/**
 * What has actually worked on this channel. No API key, no quota.
 *
 *   node scripts/channel-stats.js --channel "https://www.youtube.com/@Handle"
 *   node scripts/channel-stats.js --channel <url> --json stats.json
 *
 * Reports MEDIANS, not means: one viral clip drags a mean far enough to keep a dead
 * category on life support. Read the medians together with n — over 5 uploads a
 * median is a weak signal, over 25 it is strong.
 *
 * The topic buckets below are a starting point. Edit them for the channel at hand;
 * a bucket matching 3 titles tells you nothing, and one matching 80% tells you
 * nothing either. Aim for 4-7 buckets of 5-30 uploads each.
 */
import fs from 'node:fs';
import { listChannel } from './fetch-transcripts.js';
import { parseArgs, requireArg, isMain } from './lib/args.js';

export const TOPICS = [
  ['space / NASA',        /(?<![\p{L}\p{N}_])(ნასა|nasa|კოსმოს|რაკეტ|სკაფანდრ|სეიგან|ჩაკრულო|მარს|voyager|space|rocket|orbit)/iu],
  ['local identity',      /(?<![\p{L}\p{N}_])(ქართ|საქართველო|🇬🇪|ქვეყან|თბილის|georgian|georgia)/iu],
  ['robots / hardware',   /(?<![\p{L}\p{N}_])(რობოტ|დრონ|humanoid|robot|drone|unitree|hardware)/iu],
  ['abstract AI talk',    /(?<![\p{L}\p{N}_])(ai|ხელოვნურ|chatgpt|gemini|claude)/iu],
  ['career / education',  /(?<![\p{L}\p{N}_])(კარიერ|სკოლ|უნივერსიტეტ|სწავლ|career|school|university|student)/iu],
];

const median = (xs) => {
  const s = [...xs].sort((a, b) => a - b);
  return s.length ? s[Math.floor(s.length / 2)] : 0;
};

export function analyse(items) {
  const views = items.map((i) => i.views);
  const dist = { '10K+': 0, '2K-10K': 0, '700-2K': 0, '<700': 0 };
  for (const v of views) {
    if (v >= 10000) dist['10K+']++;
    else if (v >= 2000) dist['2K-10K']++;
    else if (v >= 700) dist['700-2K']++;
    else dist['<700']++;
  }

  // Assign each title to its FIRST matching bucket so counts stay disjoint and sum
  // to the total — overlapping buckets double-count and inflate weak categories.
  const buckets = [];
  for (const [name, re] of TOPICS) {
    const matched = items.filter((i) => re.test(i.title) &&
      !buckets.some((b) => b.items.includes(i)));
    if (matched.length) buckets.push({ name, items: matched });
  }

  return {
    n: items.length,
    median: median(views),
    mean: Math.round(views.reduce((a, b) => a + b, 0) / (views.length || 1)),
    max: Math.max(0, ...views),
    dist,
    topics: buckets
      .map((b) => ({
        name: b.name, n: b.items.length,
        median: median(b.items.map((i) => i.views)),
        max: Math.max(...b.items.map((i) => i.views)),
      }))
      .sort((a, b) => b.median - a.median),
  };
}

function printReport(label, r) {
  console.log(`\n=== ${label} ===`);
  console.log(`n=${r.n}  median=${r.median}  mean=${r.mean}  max=${r.max}`);
  console.log(`distribution: ${JSON.stringify(r.dist)}`);
  if (r.topics.length) {
    console.log('\n  topic                 n    median      max');
    for (const t of r.topics) {
      console.log(`  ${t.name.padEnd(20)} ${String(t.n).padStart(3)} ${String(t.median).padStart(9)} ${String(t.max).padStart(8)}`);
    }
  }
}

if (isMain(import.meta.url)) {
  const args = parseArgs();
  const channel = requireArg(args, 'channel', 'Usage: node scripts/channel-stats.js --channel <url> [--json out.json]');

  const shorts = listChannel(channel, 'shorts');
  const videos = listChannel(channel, 'videos');
  const rs = analyse(shorts), rv = analyse(videos);

  printReport('SHORTS', rs);
  printReport('LONG-FORM', rv);

  console.log('\n--- read this first ---');
  if (rs.median < rv.median) {
    console.log(`Shorts median (${rs.median}) is BELOW long-form median (${rv.median}).`);
    console.log('The Shorts are underperforming the videos they came from, so the');
    console.log('bottleneck is moment selection — not reach, format, or tooling.');
  }
  // Only draw a conclusion from buckets large enough to mean anything. A median over
  // 2 uploads is an anecdote, and presenting it as a finding is worse than silence.
  const MIN_N = 4;
  const solid = rs.topics.filter((t) => t.n >= MIN_N);
  const best = solid[0], worst = solid.at(-1);
  if (best && worst && best !== worst && worst.n > best.n && worst.median < best.median) {
    console.log(`\nEffort/return mismatch: "${worst.name}" has ${worst.n} uploads at median ${worst.median},`);
    console.log(`while "${best.name}" has only ${best.n} at median ${best.median}.`);
    console.log('Rebalancing the content mix is worth more than any tooling change.');
  }
  const thin = rs.topics.filter((t) => t.n < MIN_N).map((t) => `${t.name} (n=${t.n})`);
  if (thin.length) {
    console.log(`\nToo few uploads to judge: ${thin.join(', ')}.`);
    console.log('Buckets are assigned first-match-wins in TOPICS order, so a thin bucket');
    console.log('often means an earlier pattern absorbed its videos — check the order.');
  }

  if (typeof args.json === 'string') {
    fs.writeFileSync(args.json, JSON.stringify({ shorts: rs, videos: rv }, null, 2));
    console.log(`\nwrote ${args.json}`);
  }
}
