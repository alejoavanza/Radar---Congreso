import test from 'node:test';
import assert from 'node:assert/strict';
import {createRequest, sourceURL} from '../src/transport.js';
import {createStorage} from '../src/storage.js';
import {reportText, comparisonText} from '../src/share.js';
import {API_ORIGIN, STATE_KEY} from '../src/config.js';

test('native report request preserves the body and goes only to the production JSON endpoint', async () => {
  let call;
  const request = createRequest({request: async value => { call = value; return {status: 200, data: {name: 'Persona'}}; }});
  const response = await request('/api/report', {method: 'POST', body: JSON.stringify({name: 'Persona', territory: 'Colombia', days: 1})});
  assert.equal(call.url, API_ORIGIN + '/api/report');
  assert.deepEqual(call.data, {name: 'Persona', territory: 'Colombia', days: 1});
  assert.equal(call.disableRedirects, true);
  assert.equal(call.connectTimeout, undefined, 'iOS must not override the report timeout with a short connection timeout');
  assert.equal(response.ok, true);
  assert.deepEqual(await response.json(), {name: 'Persona'});
  await assert.rejects(request('https://elsewhere.test/api/report', {method: 'POST'}), /no permitida/);
  await assert.rejects(request('/api/../report', {method: 'POST'}), /no permitida/);
});

test('offline requests, redirects, invalid JSON and server errors stay distinguishable', async () => {
  let calls = 0;
  const offline = createRequest({request: async () => calls++}, () => false);
  await assert.rejects(offline('/api/report', {method: 'POST'}), /Sin conexión/);
  assert.equal(calls, 0);
  for (const response of [{status: 302, data: {}}, {status: 200, data: '<html>error</html>'}, {status: 200, data: []}]) {
    await assert.rejects(createRequest({request: async () => response})('/api/report', {method: 'POST'}));
  }
  const response = await createRequest({request: async () => ({status: 502, data: '{"error":"Fuente no disponible"}'})})('/api/report', {method: 'POST'});
  assert.equal(response.ok, false);
  assert.equal((await response.json()).error, 'Fuente no disponible');
});

test('an aborted native request cannot deliver a late result to the interface', async () => {
  let finish;
  const signal = new AbortController();
  const request = createRequest({request: () => new Promise(resolve => { finish = resolve; })});
  const pending = request('/api/report', {method: 'POST', signal: signal.signal});
  signal.abort();
  await assert.rejects(pending, {name: 'AbortError'});
  finish({status: 200, data: {name: 'Old result'}});
  await assert.rejects(request('/api/report', {method: 'POST', signal: signal.signal}), {name: 'AbortError'});
});

function preferences(initial = null) {
  let value = initial;
  return {
    get: async () => ({value}),
    set: async data => { assert.equal(data.key, STATE_KEY); value = data.value; },
    remove: async data => { assert.equal(data.key, STATE_KEY); value = null; },
    value: () => value
  };
}

test('snapshots survive a fresh launch and deletion cannot be undone by background saves', async () => {
  const prefs = preferences();
  const storage = await createStorage(prefs);
  storage.setItem('radar:report:v1', '{"report":"saved"}');
  storage.setItem('radar:tab:v1', 'compare');
  storage.setItem('unrelated', 'never persist');
  await storage.flush();
  const reopened = await createStorage(prefs);
  assert.equal(reopened.getItem('radar:report:v1'), '{"report":"saved"}');
  assert.equal(reopened.getItem('radar:tab:v1'), 'compare');
  assert.equal(reopened.getItem('unrelated'), null);
  reopened.setItem('radar:tab:v1', 'report');
  const deleting = reopened.clearSaved();
  reopened.setItem('radar:report:v1', 'late pagehide');
  await deleting;
  await reopened.flush();
  assert.equal(prefs.value(), null);
  assert.equal(reopened.getItem('radar:report:v1'), null);
});

test('corrupt storage and write failures are reported without blocking new searches', async () => {
  const messages = [];
  const prefs = preferences('{corrupt');
  const storage = await createStorage(prefs, message => messages.push(message));
  assert.match(messages[0], /recuperar/);
  prefs.set = async () => { throw new Error('disk'); };
  storage.setItem('radar:tab:v1', 'compare');
  await storage.flush();
  assert.match(messages[1], /guardar/);
  prefs.set = async () => {};
  storage.setItem('radar:tab:v1', 'report');
  await storage.flush();
  assert.equal(storage.getItem('radar:tab:v1'), 'report');
});

test('share summaries retain evidence, limited counts and N/D without unsafe links', () => {
  assert.equal(sourceURL('javascript:alert(1)'), null);
  assert.equal(sourceURL('https://user:password@example.test/'), null);
  assert.equal(sourceURL('/relative'), null);
  const report = reportText({report: {name: 'Persona', summary: 'Resumen', items: [{title: 'Una fuente', link: 'https://example.test/news'}, {title: 'Mal enlace', url: 'javascript:alert(1)'}]}, query: {days: 1, territory: 'Antioquia'}});
  assert.match(report, /Últimas 24 horas/);
  assert.match(report, /https:\/\/example.test\/news/);
  assert.doesNotMatch(report, /javascript/);
  const comparison = comparisonText({snapshot: {meta: {territory: 'Colombia', start_time: '2026-09-05', end_time: '2026-09-06'}, rows: [
    {member: {search_name: 'Uno'}, sources: {Web: {status: 'available', count: 4, limited: true}}},
    {member: {search_name: 'Dos'}, sources: {Web: {status: 'unavailable', count: null}}}
  ]}});
  assert.match(comparison, /Uno: 4\+/);
  assert.match(comparison, /Dos: N\/D/);
});
