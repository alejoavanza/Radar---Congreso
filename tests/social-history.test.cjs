const {test} = require('node:test');
const assert = require('node:assert/strict');
const model = require('../static/social-history-model.js');
const row = (platform, date, followers, extra = {}) => ({member_id: 'alejandro', platform, date, followers, views: null, interactions: null, posts: null, impressions: null, reach: null, ...extra});

test('calendar periods clamp month ends and leap years; seven days are inclusive', () => {
  assert.equal(model.windowStart('2026-09-25', '7d'), '2026-09-19');
  assert.equal(model.windowStart('2026-03-31', '1m'), '2026-02-28');
  assert.equal(model.windowStart('2024-03-31', '1m'), '2024-02-29');
  assert.equal(model.windowStart('2024-02-29', '12m'), '2023-02-28');
  assert.equal(model.windowStart('2026-09-25', '3m'), '2026-06-25');
  assert.equal(model.windowStart('2026-09-25', '6m'), '2026-03-25');
});
test('missing networks never become zeros or misleading aggregate growth', () => {
  const records = [row('instagram', '2026-09-20', 100), row('instagram', '2026-09-25', 120), row('facebook', '2026-09-25', 200)];
  const result = model.calculate(records, 'alejandro', '7d', 'followers', ['instagram', 'facebook'], '2026-09-25');
  assert.deepEqual(result.total.points, [{date: '2026-09-25', value: 320}]);
  assert.equal(result.total.growth, null);
  assert.equal(result.series.instagram.growth, 20);
  assert.equal(result.series.instagram.percent, 20);
  assert.equal(result.expectedDays, 7);
  assert.deepEqual(model.calculate(records, 'alejandro', '7d', 'followers', model.platforms, '2026-09-25').total.points, []);
});
test('same-date totals maintain a fixed cohort; no stale carry-forward', () => {
  const records = [row('instagram', '2026-09-20', 100), row('facebook', '2026-09-20', 200), row('instagram', '2026-09-25', 150), row('facebook', '2026-09-24', 220)];
  const result = model.calculate(records, 'alejandro', '7d', 'followers', ['instagram', 'facebook'], '2026-09-25');
  assert.equal(result.total.count, 1);
  assert.equal(result.total.last.value, 300);
});
test('zero is measured; percentage with zero base is unavailable; declines are negative', () => {
  const records = [row('instagram', '2026-09-20', 0), row('instagram', '2026-09-25', 100)];
  let result = model.calculate(records, 'alejandro', '7d', 'followers', ['instagram'], '2026-09-25');
  assert.equal(result.total.growth, 100); assert.equal(result.total.percent, null);
  records[0].followers = 200;
  result = model.calculate(records, 'alejandro', '7d', 'followers', ['instagram'], '2026-09-25');
  assert.equal(result.total.percent, -50);
});
test('reach is never added across networks and daily activity is not follower growth', () => {
  const records = [row('instagram', '2026-09-25', 20, {reach: 10, views: 30}), row('facebook', '2026-09-25', 30, {reach: 15, views: 40})];
  const reach = model.calculate(records, 'alejandro', '7d', 'reach', ['instagram', 'facebook'], '2026-09-25');
  assert.equal(reach.total.count, 0); assert.equal(reach.series.facebook.last.value, 15);
  const views = model.calculate(records, 'alejandro', '7d', 'views', ['instagram', 'facebook'], '2026-09-25');
  assert.equal(views.total.last.value, 70); assert.equal(views.total.growth, null);
});
test('period and identity filters exclude unrelated, old and future records', () => {
  const records = [row('instagram', '2026-09-18', 1), row('instagram', '2026-09-19', 2), row('instagram', '2026-09-26', 3), row('instagram', '2026-09-25', 4, {member_id: 'other'})];
  const result = model.calculate(records, 'alejandro', '7d', 'followers', [], '2026-09-25');
  assert.equal(result.rows.length, 1); assert.equal(result.total.count, 0);
});
test('CSV exports preserve null, zero and quoted sources', () => {
  const output = model.csv([row('instagram', '2026-09-25', 0, {source: 'https://example.org/?x="a,b"'})]);
  assert.ok(output.includes('"0"')); assert.ok(output.includes('"https://example.org/?x=""a,b"""'));
  assert.ok(output.includes('"",""')); assert.ok(!output.includes('null'));
});
