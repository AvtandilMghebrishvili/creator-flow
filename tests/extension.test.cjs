const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const C = require('../extensions/creator-flow/core.js');
const meta = {channel: 'https://www.youtube.com/@Example', start: '2026-09-01', end: '2026-09-30'};
const header = 'Content,Video title,Views,Impressions,Impressions click-through rate (%),Watch time (hours),Average view duration,Subscribers';
const csv = header + '\nTotal,Total,1100,11000,5,10,0:30,12\nabcdefghijk,"Quoted, video",100,1000,10,2,1:02,2\nlmnopqrstuv,Second,1000,10000,4,8,0:40,10';
test('YouTube identity excludes other origins and malformed IDs', () => {
  assert.equal(C.pageIdentity('https://www.youtube.com/watch?v=abcdefghijk&t=22').id, 'abcdefghijk');
  assert.equal(C.pageIdentity('https://www.youtube.com/shorts/abcdefghijk').format, 'short');
  assert.equal(C.pageIdentity('https://www.youtube.com/@Example/videos').url, meta.channel);
  assert.equal(C.pageIdentity('https://www.youtube.com.evil.test/watch?v=abcdefghijk'), null);
  assert.equal(C.pageIdentity('javascript:alert(1)'), null);
  assert.equal(C.pageIdentity('https://www.youtube.com/watch?v=short'), null);
});
test('public counts preserve missing/approximate values and locale units', () => {
  assert.equal(C.visibleCount('No views yet'), null);
  assert.equal(C.visibleCount('0 views').value, 0);
  assert.equal(C.visibleCount('1.2K views').value, 1200);
  assert.equal(C.visibleCount('1,2 ათ. ნახვა').value, 1200);
  assert.equal(C.visibleCount('12,345 views').value, 12345);
  assert.equal(C.visibleCount('unknown'), null);
  assert.equal(C.visibleCount('2 days ago'), null);
  assert.equal(C.visibleCount('2 მილიონი ნახვა').value, 2000000);
  assert.equal(C.visibleCount('4.8 thousand views').value, 4800);
  assert.equal(C.visibleCount('1.2 million views').value, 1200000);
});
test('even medians average the middle pair and formats stay separate', () => {
  assert.equal(C.median([1, 3, 10, 20]), 6.5);
  assert.equal(C.median([]), null);
  const stats = C.sampleStats([{format: 'short', views: 900}, {format: 'long', views: 10}, {format: 'long', views: null}]);
  assert.equal(stats[0].median, 10); assert.equal(stats[0].measured, 1); assert.equal(stats[1].median, 900);
});
test('CSV handles UTF-8, BOM, escaped quotes, commas, and multiline fields', () => {
  const rows = C.csvRows('\ufeffID,Title\r\na,"ქართული, ""ფრაზა""\nმეორე"\r\n');
  assert.deepEqual(rows, [['ID', 'Title'], ['a', 'ქართული, "ფრაზა"\nმეორე']]);
  assert.throws(() => C.csvRows('a,"unterminated'), /unclosed/);
  assert.throws(() => C.csvRows('a,"quoted"junk'), /Malformed/);
});
test('Studio import excludes total and weights CTR by impressions', () => {
  const data = C.importStudio(csv, meta); assert.equal(data.videos.length, 2); assert.equal(data.videos[0].averageSeconds, 62);
  const a = C.analytics(data); assert.equal(a.views.value, 1100); assert.ok(Math.abs(a.ctr.value - 50_000 / 11000) < .00001);
});
test('missing columns and zero impressions do not become zero CTR', () => {
  const data = C.importStudio('Video ID,Title,Views\nabcdefghijk,A,0', meta);
  const a = C.analytics(data); assert.equal(a.views.value, 0); assert.equal(a.ctr.value, null); assert.equal(a.watchHours.value, null);
  assert.equal(C.analytics({videos: [{views: 1, impressions: 0, ctr: 0}]}).ctr.value, null);
});
test('reject mismatched dates, duplicate IDs, percentages and malformed locale numbers', () => {
  assert.throws(() => C.importStudio(csv, {...meta, start: '2026-02-30'}), /date/);
  assert.throws(() => C.importStudio(csv, {...meta, end: '2026-01-01'}), /dates/);
  assert.throws(() => C.importStudio(csv.replace('lmnopqrstuv', 'abcdefghijk'), meta), /Duplicate/);
  assert.throws(() => C.importStudio(csv.replace(',1000,10,2', ',1000,101,2'), meta), /ctr/);
  assert.throws(() => C.importStudio(csv.replace('1000,10000', 'NaN,10000'), meta), /Invalid views/);
});
test('drafts are explicit templates, never evidence of predicted performance', () => {
  const d = C.drafts({title: 'რობოტები პრაქტიკაში'}, 'რობოტები', 'ka');
  assert.equal(d.titles.length, 3); assert.ok(d.ideas.every(x => x.why.includes('შაბლონი')));
  assert.equal(C.packaging({title: 'A'}).find(x => x.label === 'რეალური CTR').status, 'unknown');
});
test('AI context caps rows while retaining full aggregates/current video', () => {
  const videos = Array.from({length: 200}, (_, i) => ({id: String(i), title: 'Demo', views: i}));
  const ctx = C.context({id: '0'}, {...meta, videos}, 'en', 'Demo');
  assert.equal(ctx.analytics.videos.length, 100); assert.equal(ctx.analytics.videos[0].id, '0');
  assert.equal(ctx.analytics.summary.count, 200); assert.equal(ctx.analytics.summary.views.value, 19900);
});
test('reports are scoped to the exact context; unsafe structures are rejected', () => {
  const ctx = C.context({id: 'a'}, null, 'ka', ''), key = C.contextKey(ctx);
  const report = {schema: 'creator-flow-advice-v1', contextKey: key, summary: 'Summary', findings: [], titles: [], ideas: [], description: '', tags: []};
  assert.equal(C.validateReport(report, key), report);
  assert.throws(() => C.validateReport(report, C.contextKey({...ctx, topic: 'different'})), /match/);
  assert.throws(() => C.validateReport({...report, titles: [{}]}, key), /Invalid title/);
});
test('manifest does not request cookies/history or all-sites access', () => {
  const m = JSON.parse(fs.readFileSync(require.resolve('../extensions/creator-flow/manifest.json')));
  assert.equal(m.manifest_version, 3);
  assert.deepEqual(m.permissions, ['storage', 'activeTab']);
  assert.ok(m.content_scripts[0].matches.every(x => x.startsWith('https://') && x.includes('youtube.com/')));
  assert.equal(m.host_permissions, undefined);
});
