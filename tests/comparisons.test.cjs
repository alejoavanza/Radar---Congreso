const test = require('node:test');
const assert = require('node:assert/strict');
const {summarize, sortRows} = require('../static/comparisons.js');
const available = (count, limited = false) => ({status: 'available', count, limited});
const unavailable = () => ({status: 'unavailable', count: null});
const row = (name, web, x, bsky, reddit) => ({member: {id: name, display_name: name}, sources: {Web: web, X: x, Bluesky: bsky, Reddit: reddit}});

test('five-member comparison sums only social sources available to all', () => {
  const rows = Array.from({length: 5}, (_, i) => row('Member ' + i, available(i * 10), i === 0 ? unavailable() : available(100), available(i), available(2)));
  const result = summarize(rows);
  assert.deepEqual(result.common, ['Bluesky', 'Reddit']);
  assert.deepEqual(result.rows.map(r => r.social), [2, 3, 4, 5, 6]);
});

test('unavailable data never creates a zero, including a failed whole member', () => {
  const rows = [row('A', available(0), unavailable(), available(0), unavailable()), row('B', unavailable(), unavailable(), unavailable(), unavailable())];
  const result = summarize(rows);
  assert.deepEqual(result.common, []);
  assert.deepEqual(result.rows.map(r => r.social), [null, null]);
  assert.deepEqual(result.rows.map(r => r.web), [0, null]);
});

test('limited source labels propagate and unavailable rows sort last', () => {
  const result = summarize([row('B', available(20, true), available(15), available(3, true), unavailable()), row('A', unavailable(), available(10), available(0), unavailable())]);
  assert.equal(result.rows[0].social, 18);
  assert.equal(result.rows[0].socialLimited, true);
  assert.equal(result.rows[0].webLimited, true);
  assert.deepEqual(sortRows(result.rows, 'web').map(r => r.member.id), ['B', 'A']);
  assert.deepEqual(sortRows(result.rows, 'name').map(r => r.member.id), ['A', 'B']);
});

test('non-numeric source results cannot enter a chart', () => {
  for (const count of [null, undefined, NaN, Infinity, -1, '12', false]) {
    const data = summarize([row('A', available(count), available(count), unavailable(), unavailable())]);
    assert.equal(data.rows[0].web, null);
    assert.equal(data.rows[0].social, null);
  }
});
