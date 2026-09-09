(function (root) {
  'use strict';
  const VERSION = 'radar:evidence:v1';
  const MINUTE = 60000, DAY = 86400000;
  const normalize = value => String(value || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim();
  function scope(query) {
    const terms = [query.name, ...(query.aliases || '').split(',')].map(normalize).filter(Boolean);
    return JSON.stringify([[...new Set(terms)].sort(), normalize(query.territory)]);
  }
  function urlKey(value) {
    try {
      const url = new URL(value);
      if (!['https:', 'http:'].includes(url.protocol) || url.username || url.password) return null;
      for (const key of [...url.searchParams.keys()]) if (/^utm_/i.test(key) || ['fbclid', 'gclid', 'oc', 'hl', 'gl', 'ceid'].includes(key)) url.searchParams.delete(key);
      url.searchParams.sort();
      return url.hostname.replace(/^www\./, '') + url.pathname.replace(/\/$/, '') + url.search;
    } catch (_) { return null; }
  }
  function createSession({storage, request, now = Date.now}) {
    let state = {scopes:{}, window:null};
    const pending = new Map();
    let windowPending = null;
    try {
      const saved = JSON.parse(storage?.getItem(VERSION));
      if (saved?.scopes && typeof saved.scopes === 'object') state = saved;
    } catch (_) { /* Storage is optional; in-memory continuity still works. */ }
    function save() {
      const entries = Object.entries(state.scopes).sort((a,b)=>b[1].touched-a[1].touched).slice(0,10);
      state.scopes = Object.fromEntries(entries);
      try { storage?.setItem(VERSION, JSON.stringify(state)); } catch (_) { /* Quota/private mode. */ }
    }
    async function cutoff(refresh = false) {
      if (!refresh && state.window && now() - state.window.at < 8*MINUTE) return state.window.end;
      if (windowPending) return windowPending;
      windowPending = (async () => {
        const response = await request('/api/search/window', {cache:'no-store'});
        const data = await response.json();
        if (!response.ok || !Number.isFinite(Date.parse(data.end_time))) throw new Error('No se pudo fijar la hora de corte. Intenta de nuevo.');
        state.window = {end:data.end_time, at:now()}; save();
        return data.end_time;
      })();
      try { return await windowPending; } finally { windowPending = null; }
    }
    function merge(query, result, cached) {
      const key = scope(query), entry = state.scopes[key] || {items:[], responses:{}};
      const fresh = new Set();
      const byUrl = new Map();
      for (const item of entry.items) {
        const url = urlKey(item.url);
        if (url && now() - item._seen < DAY) byUrl.set(url, item);
      }
      for (const item of result.items || []) {
        const url = urlKey(item.url);
        if (!url || typeof item.title !== 'string' || !Number.isFinite(Date.parse(item.published))) continue;
        fresh.add(url);
        const previous = byUrl.get(url);
        const seen = Date.parse(item.verified_at);
        byUrl.set(url, {...previous, ...item, _seen:Number.isFinite(seen) ? seen : previous?._seen || now()});
      }
      entry.items = [...byUrl.values()].sort((a,b)=>Date.parse(b.published)-Date.parse(a.published) || a.url.localeCompare(b.url)).slice(0,300);
      entry.touched = now(); state.scopes[key] = entry;
      const end = Date.parse(query.end_time), start = end-query.days*DAY;
      const titles = new Set(), matches = [];
      for (const item of entry.items) {
        const date = Date.parse(item.published);
        if (!(start <= date && date < end) || now()-item._seen >= DAY) continue;
        const title = JSON.stringify([normalize(item.title), normalize(item.publisher_domain || item.source), item.published.slice(0,10)]);
        if (titles.has(title)) continue;
        titles.add(title); matches.push(item);
      }
      const limit = query.limit || 100, retained = matches.filter(item=>!fresh.has(urlKey(item.url))).length;
      const items = matches.slice(0,limit).map(({_seen,...item})=>item);
      const unavailable = !items.length && (result.status === 'unavailable' || result.limited);
      let message = result.message || 'Cobertura parcial de medios web.';
      if (retained) message += ` Se conservan ${retained} noticias verificadas de consultas anteriores de esta sesión.`;
      if (cached) message += ' Consulta reciente reutilizada; puedes actualizar las fuentes.';
      if (matches.length > limit) message += ` Se muestran las ${limit} publicaciones más recientes.`;
      save();
      return {...result, items, count:unavailable ? null : items.length,
        status:unavailable ? 'unavailable' : 'available', limited:!!result.limited || !!retained || matches.length > limit,
        retained_count:retained, cache_hit:!!cached, message,
        start_time:new Date(start).toISOString(), end_time:query.end_time};
    }
    async function run(query, loader, refresh = false) {
      if (!Number.isFinite(Date.parse(query.end_time))) throw new Error('Falta una hora de corte válida.');
      const key = scope(query), responseKey = `${query.days}|${query.end_time}`;
      const entry = state.scopes[key], saved = entry?.responses?.[responseKey];
      if (!refresh && saved && now()-saved.at < 5*MINUTE) return merge(query, saved.result, true);
      const requestKey = key + responseKey;
      if (pending.has(requestKey)) return merge(query, await pending.get(requestKey), true);
      const task = (async () => {
        try {
          const result = await loader();
          // Only complete transport responses may populate the response cache.
          // Failed reads cannot replace positive evidence from another period.
          if (result.status === 'available' && Array.isArray(result.items)) {
            const current = state.scopes[key] || {items:[], responses:{}};
            current.responses[responseKey] = {at:now(), result};
            current.responses = Object.fromEntries(Object.entries(current.responses).sort((a,b)=>b[1].at-a[1].at).slice(0,5));
            state.scopes[key] = current;
          }
          return result;
        } catch (error) {
          return {status:'unavailable', count:null, items:[], limited:true, message:error.message || 'No se pudo completar la búsqueda.'};
        }
      })();
      pending.set(requestKey, task);
      try { return merge(query, await task, false); } finally { pending.delete(requestKey); }
    }
    return {cutoff, run, scope};
  }
  if (typeof module !== 'undefined' && module.exports) module.exports = {createSession, scope};
  if (root.document) root.RadarSearch = createSession({
    storage:root.RadarNative?.storage || root.sessionStorage,
    request:(...args)=>(root.RadarNative?.request || root.fetch)(...args)
  });
})(typeof window === 'undefined' ? globalThis : window);
