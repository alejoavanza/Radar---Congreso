const {test} = require('node:test');
const assert = require('node:assert/strict');
const model = require('../static/social-history-model.js');
const pieces = require('../static/social-export.js');
const member = {id:'test',full_name:'Persona de prueba'};
const row = (platform,date,followers) => ({member_id:'test',platform,date,followers,views:10,reach:5,source:'https://example.org/datos',account:'test'});
function current(rows) { return model.calculate(rows,'test','1m','followers',['instagram','facebook'],'2026-09-25'); }
test('comparison index uses a shared measured date, not each networks first date',()=>{
  const result = pieces.prepare(current([row('instagram','2026-08-25',50),row('instagram','2026-09-01',100),row('facebook','2026-09-01',200),row('instagram','2026-09-25',150),row('facebook','2026-09-25',600)]),member,'followers','comparison','index');
  assert.equal(result.baseline,'2026-09-01');
  assert.deepEqual(result.series.map(s=>s.points.map(p=>p.value)),[[100,150],[100,300]]);
  assert.equal(result.series[0].last.value,150);
  assert.equal(result.series[1].percent,200);
  assert.equal(result.series[0].points.length,2);
});
test('reject absent common baselines and zero bases instead of inventing a comparison',()=>{
  for(const rows of [[row('instagram','2026-09-01',100),row('facebook','2026-09-02',200)],[row('instagram','2026-09-01',0),row('facebook','2026-09-01',200)]]) {
    assert.throws(()=>pieces.prepare(current(rows),member,'followers','comparison','index'),/fecha común/);
  }
});
test('absolute series retain zeros and unavailable networks, no manufactured observations',()=>{
  const result = pieces.prepare(current([row('instagram','2026-09-01',0)]),member,'followers','comparison','absolute');
  assert.equal(result.series[0].points[0].value,0);
  assert.equal(result.series[1].points.length,0);
  assert.match(pieces.caption(result),/Facebook: N\/D/);
});
test('individual exports ignore total network selection and preserve exact source and dates',()=>{
  const input = current([row('instagram','2026-09-01',100),row('instagram','2026-09-25',50),row('facebook','2026-09-01',200)]);
  input.selected=['facebook'];
  const result=pieces.prepare(input,member,'followers','instagram','index');
  assert.equal(result.indexed,false);
  assert.equal(result.series.length,1);
  assert.equal(result.series[0].percent,-50);
  assert.match(pieces.caption(result),/-50 %/);
  assert.ok(pieces.caption(result).includes('origen no verificado'));
  assert.deepEqual(result.sources,['https://example.org/datos']);
});
test('total needs complete same-date data; reach can never be exported as a total',()=>{
  const input=current([row('instagram','2026-09-01',100),row('facebook','2026-09-02',200)]);
  assert.throws(()=>pieces.prepare(input,member,'followers','total','absolute'),/No hay datos/);
  assert.throws(()=>pieces.prepare(input,member,'reach','total','absolute'),/nunca como total/);
  assert.throws(()=>pieces.prepare(input,member,'views','comparison','index'),/para seguidores/);
});
test('image dimensions match publication, horizontal and story formats',()=>{
  assert.deepEqual(pieces.formats,{portrait:[1080,1350],landscape:[1600,900],story:[1080,1920]});
});
test('illustrative example is labelled and never assigned to a real politician',()=>{
  const report=pieces.exampleReport('comparison','index');
  assert.equal(report.demo,true);
  assert.equal(report.memberId,'ejemplo');
  assert.match(report.name,/datos simulados/);
  assert.equal(report.series.length,5);
  assert.ok(report.series.every(s=>s.points[0].value===100));
});
