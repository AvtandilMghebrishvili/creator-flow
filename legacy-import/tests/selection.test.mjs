import test from 'node:test';
import assert from 'node:assert/strict';
import { score } from '../skills/youtube-techcrush/scripts/lib/segment.js';
import { analyse } from '../skills/youtube-techcrush/scripts/channel-stats.js';

test('Georgian stems match at Unicode word boundaries',()=>{
  assert.ok(score('ნასა კოსმოსში პირველად მახსოვს').score>0);
  assert.ok(score('საქართველო').hits.some(h=>h.startsWith('local identity')));
  assert.equal(score('xკოსმოსი').hits.some(h=>h.startsWith('space')),false);
  assert.ok(score('NASA rocket').score>0);
});
test('Georgian channel titles enter their actual topic buckets',()=>{
  const report=analyse([{title:'კოსმოსში მოგზაურობა',views:1000},{title:'კარიერა და სწავლა',views:500}]);
  assert.equal(report.topics.find(t=>t.name==='space / NASA').n,1);
  assert.equal(report.topics.find(t=>t.name==='career / education').n,1);
});
