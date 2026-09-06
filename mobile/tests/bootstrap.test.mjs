import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {JSDOM, VirtualConsole} from 'jsdom';

const asset = path => readFile(new URL('../www/' + path, import.meta.url));
const catalog = JSON.parse(await asset('static/congress-members.json'));
const tick = () => new Promise(resolve => setTimeout(resolve, 5));

test('real bundled bootstrap registers iOS plugins, opens a source without navigating away and shares its report', async () => {
  const html = (await asset('index.html')).toString().replace('<script src="/native.js"></script>', '');
  const native = (await asset('native.js')).toString();
  const callbacks = new Map(), calls = [], stored = new Map(), errors = [];
  const methods = {
    CapacitorHttp: ['request'], Preferences: ['get', 'set', 'remove'],
    Browser: ['open'], Share: ['share'], Network: ['getStatus'], App: []
  };
  const dom = new JSDOM(html, {url: 'capacitor://localhost/', runScripts: 'dangerously', pretendToBeVisual: true,
    virtualConsole: new VirtualConsole().on('jsdomError', e => errors.push(e)),
    beforeParse(w) {
      w.webkit = {messageHandlers: {bridge: {}}};
      w.scrollTo = () => {}; w.alert = message => calls.push({plugin: 'alert', message});
      w.fetch = async path => {assert.match(path, /^\/static\/congress-members/); return {ok: true, json: async () => catalog};};
      w.Capacitor = {
        PluginHeaders: Object.entries(methods).map(([name, list]) => ({name, methods: [
          ...list.map(name => ({name, rtype: 'promise'})), {name: 'addListener', rtype: 'callback'}, {name: 'removeListener', rtype: 'callback'}
        ]})),
        nativeCallback(plugin, method, args, callback) {callbacks.set(plugin + ':' + args.eventName, callback); return 'callback';},
        async nativePromise(plugin, method, args) {
          calls.push({plugin, method, args});
          if (plugin === 'Preferences') {
            if (method === 'get') return {value: stored.get(args.key) || null};
            if (method === 'set') stored.set(args.key, args.value);
            if (method === 'remove') stored.delete(args.key);
            return {};
          }
          if (plugin === 'Network') return {connected: true, connectionType: 'wifi'};
          if (plugin === 'CapacitorHttp') return {status: 200, data: {
            name: 'Persona de prueba', summary: 'Resumen de prueba', items: [{title: 'Una noticia', url: 'https://example.test/news', sentiment: 'Neutral'}],
            mentions: {web: 1, social: 0, combined: 1, platform_counts: {}, platform_status: {}}
          }};
          return {};
        }
      };
    }});
  try {
    const w = dom.window;
    // Model WKWebView's local asset handler; no network or browser is involved.
    const append = w.document.body.append.bind(w.document.body);
    w.document.body.append = (...nodes) => {
      for (const node of nodes) {
        if (node.tagName === 'SCRIPT') {
          assert.equal(node.src, 'capacitor://localhost/app.js');
          node.type = 'application/x-test-bundled-script';
          void asset('app.js').then(source => {w.eval(source.toString()); node.onload();}).catch(error => {errors.push(error); node.onerror();});
        }
      }
      append(...nodes);
    };
    w.eval(native);
    for (let n = 0; n < 100 && !w.document.getElementById('native-starting').hidden; n++) await tick();
    assert.equal(w.document.getElementById('native-starting').hidden, true, 'Native bootstrap should complete');
    await w.RadarCongress.catalogReady;
    w.document.getElementById('name').value = 'Persona de prueba';
    await w.go();
    w.document.querySelector('#items a').click();
    await tick();
    const opened = calls.find(call => call.plugin === 'Browser');
    assert.equal(opened.args.url, 'https://example.test/news');
    assert.equal(w.location.href, 'capacitor://localhost/');
    w.document.getElementById('native-share-report').click();
    await tick();
    const shared = calls.find(call => call.plugin === 'Share');
    assert.match(shared.args.text, /Resumen de prueba/);
    assert.match(shared.args.text, /https:\/\/example.test\/news/);
    callbacks.get('Network:networkStatusChange')({connected: false, connectionType: 'none'});
    assert.equal(w.document.getElementById('native-offline').hidden, false);
    const before = calls.filter(call => call.plugin === 'CapacitorHttp').length;
    await w.go();
    assert.equal(calls.filter(call => call.plugin === 'CapacitorHttp').length, before);
    assert.equal(w.document.getElementById('result').classList.contains('hide'), false);
    assert.equal(errors.length, 0, errors.map(e => e.message).join('\n'));
  } finally {dom.window.close();}
});
