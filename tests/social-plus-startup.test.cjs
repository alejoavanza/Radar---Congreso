const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = path.join(__dirname, '..');
const read = file => fs.readFileSync(path.join(root, file), 'utf8');

test('the directory, social model and UI scripts all parse before deployment', () => {
  for (const file of ['congress-search.js', 'social-history-model.js', 'social-history.js']) {
    assert.doesNotThrow(() => new vm.Script(read(`static/${file}`), {filename: file}));
  }
});

test('every literal UI DOM hook exists in the Plus template', () => {
  const template = read('templates/social_history.html');
  const ids = [...template.matchAll(/\bid="([^"]+)"/g)].map(match => match[1]);
  assert.equal(new Set(ids).size, ids.length, 'template IDs must be unique');
  const hooks = [...read('static/social-history.js').matchAll(/\$\('([^']+)'\)/g)].map(match => match[1]);
  for (const id of new Set(hooks)) assert.ok(ids.includes(id), `Missing Plus DOM hook: ${id}`);
  assert.ok(ids.includes('social-table'));
  assert.ok(ids.includes('social-table-caption'));
});

test('CSV rows use actual CRLF separators and escape quotes without corrupting scripts', () => {
  const model = require('../static/social-history-model.js');
  const row = {member_id: 'test-only', platform: 'instagram', account: '@example',
    date: '2026-09-26', followers: 0, source: 'https://example.org/?q="a,b"'};
  const output = model.csv([row]);
  assert.equal(output.split('\r\n').length, 3);
  assert.ok(output.endsWith('\r\n'));
  assert.ok(output.includes('"0"'));
  assert.ok(output.includes('"https://example.org/?q=""a,b"""'));
  assert.ok(!output.includes('undefined'));
  assert.ok(!output.includes('null'));
  assert.equal(model.csv([]), model.columns.join(',') + '\r\n');
});

test('each period currently offered by Plus initializes an empty report', () => {
  const model = require('../static/social-history-model.js');
  for (const period of ['1d', '7d', '1m', '60d', '3m']) {
    const report = model.calculate([], '', period, 'followers', model.platforms, '2026-09-26');
    assert.deepEqual(report.rows, []);
    assert.equal(report.total.count, 0);
    assert.equal(report.total.growth, null);
    assert.ok(report.expectedDays > 0);
  }
});
