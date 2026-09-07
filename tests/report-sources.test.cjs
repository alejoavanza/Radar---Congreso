const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

const context = vm.createContext({
  window: {addEventListener() {}}, document: {addEventListener() {}},
  sessionStorage: {getItem: () => null}, $: () => ({value:'', addEventListener() {}})
});
vm.runInContext(fs.readFileSync(require.resolve('../static/report.js'), 'utf8'), context);
const normalize = report => JSON.parse(JSON.stringify(context.webOnlyReport(report)));

test('a saved report with social totals becomes a web-only report without mutating its source', () => {
  const report = {name:'Persona', total:115, items:[{title:'Noticia',url:'https://example.org/a'}], mentions:{
    web:10, social:105, combined:115,
    platform_counts:{X:100,Bluesky:3,Reddit:2},
    platform_status:{X:'active',Bluesky:'active',Reddit:'active'},
    active_sources:['X','Bluesky','Reddit'], x_intelligence:{total:100}
  }};
  const clean = normalize(report);
  assert.equal(clean.total, 10);
  assert.equal(clean.mentions.web, 10);
  assert.equal(clean.mentions.combined, 10);
  for (const key of ['social','platform_counts','platform_status','active_sources','x_intelligence']) {
    assert.equal(key in clean.mentions, false);
  }
  assert.deepEqual(clean.items, report.items);
  assert.equal(report.mentions.combined, 115);
  assert.deepEqual(normalize(clean), clean);
});

test('rendering needs no social controls and describes only web coverage', () => {
  const nodes = new Map();
  context.$ = id => {
    assert.ok(!['msocial','mcombined'].includes(id), 'No social or combined metric exists');
    if (!nodes.has(id)) nodes.set(id, {classList:{remove() {}}});
    return nodes.get(id);
  };
  context.renderReport({name:'Persona',summary:'Resumen',items:[],mentions:{web:4,combined:4},
    web_coverage:{message:'Fuentes consultadas: Google Noticias. Cobertura parcial de la web.'}});
  assert.equal(nodes.get('mweb').textContent, 4);
  assert.match(nodes.get('report-coverage').textContent, /Cobertura parcial/);
  assert.doesNotMatch(nodes.get('report-coverage').textContent, /Redes|N\/D/);
});
