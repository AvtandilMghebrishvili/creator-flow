# Reading channel performance data

## Measure before advising

```bash
node scripts/channel-stats.js --channel "https://www.youtube.com/@Handle"
```

Pulls every Short and long-form video with view counts via `yt-dlp` — no API key, no
quota — and reports the distribution plus per-topic medians.

Generic YouTube advice is abundant and mostly untestable. A channel's own back
catalogue is a controlled experiment that already ran: same creator, same audience,
same production quality, different topics. Use it.

## Use medians, not means

One viral clip drags a mean far enough to keep a dead category on life support. On the
channel this skill was built for, a single outlier Short pulled the mean to more than
twice the median — the mean described one clip, the median described the channel.

Report medians, and report `n` alongside them. A median over 5 uploads is an anecdote;
over 25 it is a signal. `channel-stats.js` refuses to draw conclusions from buckets
smaller than 4 for this reason.

## Look for the effort/return mismatch

The most valuable pattern is rarely "what works" — creators usually have a rough sense
of that. It is **the gap between what they publish most and what performs best.**

The shape to look for:

| | uploads | median views |
|---|---|---|
| Strongest topic | few | high |
| Middle topics | some | middling |
| **Weakest topic** | **the most** | **the lowest** |

When the bottom row has the largest `n`, the channel is spending most of its effort on
its worst-performing category. That was exactly the case on the reference channel, and
no amount of rendering speed fixes it. Say so directly.

Two other things worth checking:

- **Shorts median versus long-form median.** If the Shorts underperform the videos they
  were cut from, the bottleneck is moment selection rather than format or reach. This is
  the single most diagnostic comparison the script produces.
- **The shape of the distribution.** A channel where a large share of Shorts sit in the
  bottom bucket has a selection problem, not a reach problem.

## Suggested content mix

Derived from the pattern above; adapt to whatever the channel's own data shows.

Per 5 Shorts: **3** in the top-performing topic, **1** in the second, **at most 1** in
the weak category — and that one only if it is a concrete story rather than commentary.

## Categorising topics

`channel-stats.js` buckets titles with keyword regexes in `TOPICS`. Assignment is
**first match wins** so buckets stay disjoint and sum to the total — overlapping buckets
double-count and inflate weak categories.

This makes **order significant**. If a bucket comes back surprisingly thin, an earlier
pattern probably absorbed its videos; reorder rather than concluding the topic is rare.
The script flags thin buckets for this reason.

Edit `TOPICS` per channel. A bucket matching 3 titles tells you nothing, and one
matching 80% tells you nothing either. Aim for 4–7 buckets of 5–30 uploads each.

Titles are a lossy proxy for content. When a bucket's result is surprising, read the
actual titles in it before acting on the number.

## Measuring whether the intervention worked

Track one number: **median views of the next 20 Shorts, versus the previous median.**

Not total views, which grow with upload count regardless of quality. Not the best clip,
which is noise. The median moving is the only evidence that selection improved.

If it has not moved after 20 uploads, the selection rules are wrong. Change the rules,
not the tooling.
