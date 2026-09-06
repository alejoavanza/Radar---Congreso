const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

const context = vm.createContext({
  window: {addEventListener() {}},
  document: {addEventListener() {}},
  sessionStorage: {getItem: () => null},
  $: () => ({value: '', addEventListener() {}})
});
vm.runInContext(fs.readFileSync(require.resolve('../static/report.js'), 'utf8'), context);
const withoutX = report => JSON.parse(JSON.stringify(context.withoutX(report)));

test('restored reports exclude X data and recompute totals from remaining active sources', () => {
  const report = {name: 'Persona', items: [{title: 'Noticia', url: 'https://example.org/a'}], mentions: {
    web: 10, social: 105, combined: 115,
    platform_counts: {X: 100, Bluesky: 3, Reddit: 2, Instagram: 40},
    platform_status: {X: 'active', Bluesky: 'active', Reddit: 'active', Instagram: 'restricted_access'},
    active_sources: ['X', 'Bluesky', 'Reddit'],
    diagnostics: {X: {label: 'X conectado'}, Bluesky: {label: 'Disponible'}},
    x_intelligence: {total: 100, top_posts: [{text: 'Una publicación'}]}
  }};
  const clean = withoutX(report);
  assert.equal(clean.mentions.web, 10);
  assert.equal(clean.mentions.social, 5);
  assert.equal(clean.mentions.combined, 15);
  assert.deepEqual(clean.mentions.active_sources, ['Bluesky', 'Reddit']);
  assert.equal('X' in clean.mentions.platform_counts, false);
  assert.equal('X' in clean.mentions.platform_status, false);
  assert.deepEqual(clean.mentions.diagnostics, {Bluesky: {label: 'Disponible'}});
  assert.equal('x_intelligence' in clean.mentions, false);
  assert.deepEqual(clean.items, report.items);
  assert.equal(report.mentions.platform_counts.X, 100, 'Normalization does not mutate its input');
});

test('removing unavailable X preserves the counts of remaining sources', () => {
  const report = {mentions: {web: 6, social: 4, combined: 10,
    platform_counts: {X: 0, Bluesky: 4}, platform_status: {X: 'error', Bluesky: 'active'},
    active_sources: ['Bluesky'], diagnostics: {X: {label: 'Requiere créditos'}}, x_intelligence: null}};
  const clean = withoutX(report);
  assert.equal(clean.mentions.social, 4);
  assert.equal(clean.mentions.combined, 10);
  assert.equal('diagnostics' in clean.mentions, false);
  assert.equal('x_intelligence' in clean.mentions, false);
  assert.deepEqual(withoutX(clean), clean, 'New reports stay stable after recovery');
});
