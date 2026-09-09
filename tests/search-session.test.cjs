const test = require('node:test');
const assert = require('node:assert/strict');
const {createSession, scope} = require('../static/search-session.js');
const END = '2026-09-09T07:00:00Z';
const at = Date.parse(END), DAY = 86400000;
const query = (days=1, extra={}) => ({name:'Alejandro Toro', aliases:'David Alejandro Toro Ramírez', territory:'Colombia', days, end_time:END, limit:60, ...extra});
const item = (name, age) => ({title:name,url:`https://medio.example/${name}`,source:'medio.example',publisher_domain:'medio.example',published:new Date(at-age).toISOString()});
const result = items => ({status:'available',count:items.length,items,limited:false,message:'Fuentes consultadas.'});
function setup() {
  const values = new Map(); let clock=at, calls=0;
  const storage={getItem:k=>values.get(k),setItem:(k,v)=>values.set(k,v)};
  const options={storage,now:()=>clock, request:async()=>{calls++; return {ok:true,json:async()=>({end_time:new Date(clock).toISOString()})};}};
  return {session:createSession(options), restart:()=>createSession(options), advance:ms=>clock+=ms, calls:()=>calls};
}

test('24h → 7d → 24h retains the recent note despite different index samples and avoids a third request', async () => {
  const {session}=setup(); let requests=0;
  const recent=item('reciente',3600000), older=item('anterior',3*DAY);
  const one=await session.run(query(), async()=>{requests++;return result([recent]);});
  const seven=await session.run(query(7), async()=>{requests++;return result([older]);});
  const again=await session.run(query(), async()=>{throw Error('must reuse the recent query');});
  assert.deepEqual(one.items.map(i=>i.url),again.items.map(i=>i.url));
  assert.ok(seven.items.some(i=>i.url===recent.url)); assert.equal(seven.count,2);
  assert.equal(again.cache_hit,true); assert.equal(requests,2);
  assert.equal(one.end_time,seven.end_time); assert.equal(seven.end_time,again.end_time);
});

test('a server failure after a reload preserves only verified notes within the requested period', async () => {
  const setupState=setup();
  await setupState.session.run(query(7), async()=>result([item('reciente',3600000),item('anterior',3*DAY)]));
  const reloaded=setupState.restart();
  const data=await reloaded.run(query(), async()=>{throw Error('HTTP 503');}, true);
  assert.equal(data.count,1); assert.equal(data.retained_count,1); assert.equal(data.limited,true);
  assert.match(data.message,/verificadas.*sesión/);
});

test('no evidence leaks between names, aliases or zones', async () => {
  const {session}=setup();
  await session.run(query(), async()=>result([item('nota',3600000)]));
  for (const different of [{name:'Otra persona'},{territory:'Antioquia'},{aliases:'Otra variante'},{territory:''}]) {
    const data=await session.run(query(1,different), async()=>result([]));
    assert.equal(data.count,0); assert.equal(data.items.length,0);
  }
  assert.equal(scope(query()),scope(query(7,{name:'ALEJANDRO TORO',aliases:'David Alejandro Toro Ramirez, Alejandro Toro'})));
});

test('a failed initial search is N/D, not zero, and is not cached as an empty search', async () => {
  const {session}=setup();
  const failed=await session.run(query(), async()=>{throw Error('HTTP 429');});
  assert.equal(failed.count,null); assert.equal(failed.status,'unavailable');
  const retry=await session.run(query(), async()=>result([item('nota',3600000)]));
  assert.equal(retry.count,1);
});

test('refresh advances the window and legitimately excludes notes older than 24h', async () => {
  const state=setup();
  const old=item('borde',DAY-120000);
  const firstEnd=await state.session.cutoff();
  const first=await state.session.run(query(), async()=>result([old]));
  state.advance(180000);
  assert.equal(await state.session.cutoff(),firstEnd); assert.equal(state.calls(),1);
  const nextEnd=await state.session.cutoff(true);
  const next=await state.session.run(query(1,{end_time:nextEnd}), async()=>result([]),true);
  assert.equal(first.count,1); assert.equal(next.count,0); assert.equal(state.calls(),2);
});

test('simultaneous identical clicks share one request and produce consistent counts', async () => {
  const {session}=setup(); let complete, calls=0;
  const loader=async()=>{calls++;return new Promise(resolve=>complete=resolve);};
  const a=session.run(query(),loader),b=session.run(query(),loader);
  complete(result([item('nota',3600000)]));
  const values=await Promise.all([a,b]);
  assert.equal(calls,1); assert.deepEqual(values.map(v=>v.count),[1,1]);
});

test('known notes expire after 24 hours and cannot be indefinitely recycled during failures', async () => {
  const state=setup();
  await state.session.run(query(7),async()=>result([item('nota',3600000)]));
  state.advance(DAY+1000);
  const data=await state.session.run(query(7,{end_time:new Date(at+DAY+1000).toISOString()}),async()=>{throw Error('down');},true);
  assert.equal(data.count,null); assert.equal(data.items.length,0);
});

test('tracking URLs and repeated headlines do not inflate the retained count', async () => {
  const {session}=setup(), news=item('nota',3600000);
  await session.run(query(),async()=>result([news]));
  const data=await session.run(query(7),async()=>result([{...news,url:news.url+'?utm_source=news'},item('vieja',3*DAY)]));
  assert.equal(data.count,2); assert.equal(data.retained_count,0);
});
