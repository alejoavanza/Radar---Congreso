import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {JSDOM} from 'jsdom';
import {createStorage} from '../src/storage.js';

const html = await readFile(new URL('../www/index.html', import.meta.url), 'utf8');
const scripts = await readFile(new URL('../www/app.js', import.meta.url), 'utf8');
const catalog = JSON.parse(await readFile(new URL('../www/static/congress-members.json', import.meta.url), 'utf8'));
const tick = () => new Promise(resolve => setTimeout(resolve, 0));

async function open(storage, request) {
  const dom = new JSDOM(html, {url: 'https://localhost/', runScripts: 'outside-only', pretendToBeVisual: true});
  const w = dom.window;
  w.scrollTo = () => {};
  w.alerts = []; w.alert = text => w.alerts.push(text);
  Object.defineProperty(w.navigator, 'serviceWorker', {value: {register() { throw new Error('Native app must not register a service worker'); }}});
  w.fetch = async url => {
    assert.match(url, /^\/static\/congress-members\.json/, 'Only the bundled directory can use the web fetch path');
    return {ok: true, json: async () => catalog};
  };
  w.RadarNative = {storage, request};
  w.eval(scripts);
  await w.RadarCongress.catalogReady;
  await tick();
  return dom;
}

test('packaged Radar queries the native API, restores offline, and keeps the result after a failed refresh', async () => {
  let saved = null, calls = 0;
  const prefs = {get: async () => ({value: saved}), set: async ({value}) => {saved = value;}, remove: async () => {saved = null;}};
  const storage = await createStorage(prefs);
  const report = {name: 'Persona de prueba', days: 1, summary: 'Reporte de prueba', items: [{title: 'Fuente de prueba', url: 'https://example.test/article', sentiment: 'Neutral', source: 'Medio'}], mentions: {web: 1, social: 0, combined: 1, platform_counts: {}, platform_status: {}}};
  const first = await open(storage, async (path, options) => {
    calls++;
    assert.equal(path, '/api/report');
    assert.equal(JSON.parse(options.body).territory, 'Antioquia');
    return {ok: true, json: async () => report};
  });
  try {
    const w = first.window;
    w.document.getElementById('name').value = 'Persona de prueba';
    w.document.getElementById('territory').value = 'Antioquia';
    w.document.getElementById('days').value = '1';
    await w.go();
    assert.equal(calls, 1);
    assert.equal(w.document.getElementById('mweb').textContent, '1');
    const source = w.document.querySelector('#items a');
    assert.equal(source.href, 'https://example.test/article');
    assert.equal(source.target, '_blank');
    await storage.flush();
  } finally { first.window.close(); }
  const reopened = await open(await createStorage(prefs), async () => {throw new Error('Sin conexión.');});
  try {
    const w = reopened.window;
    assert.equal(w.document.getElementById('territory').value, 'Colombia');
    assert.match(w.document.getElementById('report-restored').textContent, /Antioquia/);
    assert.equal(w.document.getElementById('result').classList.contains('hide'), false);
    await w.go();
    assert.equal(w.document.getElementById('mweb').textContent, '1');
    assert.equal(w.document.getElementById('result').classList.contains('hide'), false);
    assert.match(w.alerts[0], /Sin conexión/);
  } finally { reopened.window.close(); }
});

test('packaged Comparativos keeps the common window and distinguishes a failed member from zero', async () => {
  const members = catalog.members.slice(0, 2);
  const state = new Map([['radar:comparison:v1', JSON.stringify({ids: members.map(m => m.id), days: 1, territory: 'Colombia', order: 'web'})]]);
  const storage = {getItem: key => state.get(key) || null, setItem: (key, value) => state.set(key, value)};
  const start = '2026-09-05T12:00:00Z', end = '2026-09-06T12:00:00Z';
  const calls = [];
  const dom = await open(storage, async (path, options) => {
    const body = JSON.parse(options.body); calls.push({path, body});
    if (path === '/api/compare/start') return {ok: true, json: async () => ({members, days: 1, territory: 'Colombia', start_time: start, end_time: end})};
    assert.equal(path, '/api/compare/member');
    assert.equal(body.end_time, end);
    if (body.member_id === members[1].id) throw new Error('Fuente no disponible');
    return {ok: true, json: async () => ({member: members[0], sources: {Web: {status: 'available', count: 0, limited: false, items: []}}, start_time: start, end_time: end})};
  });
  try {
    const w = dom.window;
    w.showTab('compare');
    w.document.getElementById('compare-form').dispatchEvent(new w.Event('submit', {cancelable: true}));
    for (let i = 0; i < 20 && w.document.getElementById('compare-form').getAttribute('aria-busy') === 'true'; i++) await tick();
    assert.equal(calls.length, 3);
    const cells = [...w.document.querySelectorAll('#compare-table-body td')].map(node => node.textContent);
    assert.deepEqual(cells, ['0', 'No disponible']);
    assert.equal(JSON.parse(state.get('radar:comparison:v1')).snapshot.meta.end_time, end);
    assert.equal(state.get('radar:tab:v1'), 'compare');
  } finally { dom.window.close(); }
});
