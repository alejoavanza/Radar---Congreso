(function () {
  'use strict';
  const $ = id => document.getElementById(id);
  if (!$('followers-search')) return;
  const number = value => new Intl.NumberFormat('es-CO').format(value);
  const date = value => new Date(value).toLocaleString('es-CO', {timeZone:'America/Bogota', dateStyle:'medium', timeStyle:'short'});
  let index = [], selected = null, suggestions = [], active = -1, choosing = false, ready = false;
  let revision = 0, pending = null, report = null, discoveryRevision = 0;
  function el(tag, text, className) {
    const node = document.createElement(tag);
    if (text !== undefined) node.textContent = text;
    if (className) node.className = className;
    return node;
  }
  function link(text, value) {
    const node = el('a', text);
    try {
      const url = new URL(value);
      if (url.protocol !== 'https:' || url.username || url.password) return el('span', text);
      node.href = url.href; node.target = '_blank'; node.rel = 'noopener noreferrer';
    } catch (_) { return el('span', text); }
    return node;
  }
  async function api(path, options = {}) {
    // New native packages must explicitly allow these JSON paths. Never fall
    // through to an arbitrary local WebView URL if its transport rejects them.
    const response = window.RadarNative?.request
      ? await window.RadarNative.request(path, options)
      : await fetch(path, {...options, cache:'no-store'});
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'No se pudo completar la consulta.');
    return data;
  }
  function close() {
    $('followers-options').hidden = true;
    $('followers-search').setAttribute('aria-expanded', 'false');
    $('followers-search').removeAttribute('aria-activedescendant');
    active = -1;
  }
  function cancel() {
    revision++; discoveryRevision++;
    pending?.abort(); pending = null; report = null;
    $('followers-results').replaceChildren(); $('followers-candidates').replaceChildren();
    for (const id of ['followers-progress','followers-error','followers-storage','followers-discovery-status']) $(id).textContent = '';
  }
  function showSuggestions() {
    if (selected) return close();
    if (!ready) { $('followers-search-status').textContent = 'Cargando directorio…'; return close(); }
    const result = window.RadarCongress.findMatches(index, $('followers-search').value);
    suggestions = result.members; active = -1;
    $('followers-options').replaceChildren(...suggestions.map((member, i) => {
      const option = el('li'); option.id = `followers-option-${i}`; option.dataset.index = i;
      option.setAttribute('role','option'); option.setAttribute('aria-selected','false');
      option.append(el('span',member.display_name,'congress-option-name'),
        el('span',`${member.chamber === 'camara' ? 'Cámara' : 'Senado'} · ${member.constituency || ''} · ${member.party || ''}`,'congress-option-detail'));
      return option;
    }));
    const short = window.RadarCongress.normalize($('followers-search').value).replace(/ /g,'').length < 2;
    $('followers-search-status').textContent = short ? 'Escribe al menos dos letras.' : suggestions.length
      ? `${suggestions.length} de ${result.total} coincidencias. Selecciona la persona.` : 'Sin coincidencias. Revisa el nombre.';
    if (!suggestions.length) return close();
    $('followers-options').hidden = false; $('followers-search').setAttribute('aria-expanded','true');
  }
  function choose(member) {
    cancel(); selected = member || null;
    $('followers-search').value = selected?.display_name || '';
    $('followers-search-status').textContent = selected ? `${selected.display_name} seleccionado.` : '';
    $('followers-refresh').disabled = !selected; $('followers-discover').disabled = !selected;
    $('followers-web-search').hidden = !selected;
    if (selected) $('followers-web-search').href = 'https://www.google.com/search?q=' + encodeURIComponent('"' + selected.full_name + '" Instagram Facebook TikTok YouTube X');
    close();
    if (selected) void consult();
  }
  function drawHistory(parent, rows) {
    if (!rows.length) { parent.append(el('p','Sin observaciones guardadas en este periodo.','note')); return; }
    const details = el('details',undefined,'methodology'); details.append(el('summary',`${rows.length} observaciones guardadas · ver fechas y cifras`));
    const list = el('ul');
    for (const row of rows) list.append(el('li', `${date(row.observed_at)}: ${number(row.followers)} suscriptores (conteo público redondeado)`));
    details.append(list); parent.append(details);
  }
  function render() {
    $('followers-results').replaceChildren();
    if (!report || !selected || report.member_id !== selected.id) return;
    const days = Number($('followers-period').value);
    const end = Date.parse(report.checked_at), start = end - days * 86400000;
    $('followers-storage').textContent = report.history_configured
      ? 'El guardado se indica por red. Las consultas fallidas no crean observaciones ni borran las anteriores.'
      : 'Historial central pendiente de conexión: estas consultas no quedan guardadas al cerrar o recargar.';
    for (const item of report.results) {
      const card = el('section',undefined,'social-network');
      const heading = el('div',undefined,'social-chart-heading');
      heading.append(el('h3',item.label));
      const measured = item.status === 'available' && Number.isSafeInteger(item.followers) && item.followers >= 0 && item.source_kind === 'official_api' && Number.isFinite(Date.parse(item.observed_at));
      if (measured) heading.append(el('strong',number(item.followers)));
      card.append(heading);
      if (!measured) card.append(el('p','Sin medición disponible','social-empty'));
      card.append(el('p', item.message || 'Fuente pendiente de conexión.','note'));
      if (measured) {
        card.append(link('Ver cuenta consultada',item.account_url));
        card.append(el('p', `${item.source_name} · obtenido ${date(item.observed_at)}${item.reused ? ' · respuesta reutilizada, no una medición nueva' : ''}`,'note'));
        card.append(el('p',item.persisted ? 'Registro diario confirmado en el historial central.' : 'Esta consulta no se guardó en el historial central.','note'));
      }
      if (item.account?.evidence_url) card.append(link('Evidencia de la cuenta registrada',item.account.evidence_url));
      if (item.history_status === 'unavailable') card.append(el('p','El historial no respondió. No se ha interpretado como vacío ni borrado.','note'));
      const rows = (item.history || []).filter(row => {
        const stamp = Date.parse(row.observed_at);
        return row.member_id === selected.id && row.account_id === item.account?.account_id && row.platform === item.platform &&
          row.source_kind === 'official_api' && Number.isSafeInteger(row.followers) && row.followers >= 0 &&
          stamp >= start && stamp <= end && Date.parse(row.expires_at) > Date.now();
      });
      if (item.platform === 'youtube') {
        drawHistory(card,rows);
        card.append(el('p',item.comparison_note || 'El historial comienza con mediciones obtenidas y guardadas; no reconstruye el pasado.','note'));
      }
      $('followers-results').append(card);
    }
  }
  async function consult() {
    if (!selected) return;
    pending?.abort(); pending = new AbortController();
    const token = ++revision, member = selected, controller = pending;
    $('followers-refresh').disabled = true; $('followers-error').textContent = '';
    $('followers-progress').textContent = 'Consultando las fuentes habilitadas…';
    const timer = setTimeout(() => controller.abort(),35000);
    try {
      const data = await api('/api/social/followers', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({member_id:member.id}),signal:controller.signal});
      if (token !== revision || selected?.id !== member.id) return;
      if (data.member_id !== member.id || data.simulated_data !== false || !Array.isArray(data.results)) throw new Error('La respuesta no corresponde a esta persona.');
      report = data; render();
      $('followers-progress').textContent = 'Consulta terminada. Revisa la disponibilidad y fecha de cada red.';
    } catch (error) {
      if (token !== revision) return;
      report = null; render(); $('followers-progress').textContent = '';
      $('followers-error').textContent = error.name === 'AbortError' ? 'La consulta tardó demasiado. Inténtalo de nuevo.' : error.message;
    } finally {
      clearTimeout(timer);
      if (token === revision) { pending = null; $('followers-refresh').disabled = !selected; }
    }
  }
  $('followers-search').addEventListener('input',() => { cancel(); selected = null; $('followers-refresh').disabled = true; $('followers-discover').disabled = true; $('followers-web-search').hidden = true; showSuggestions(); });
  $('followers-search').addEventListener('focus',showSuggestions);
  $('followers-search').addEventListener('blur',() => { if (!choosing) close(); });
  $('followers-search').addEventListener('keydown',event => {
    if (event.isComposing) return;
    if (event.key === 'Escape' || event.key === 'Tab') return close();
    if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
      if ($('followers-options').hidden) showSuggestions();
      if ($('followers-options').hidden) return;
      event.preventDefault();
      active = event.key === 'ArrowDown' ? (active + 1) % suggestions.length : (active <= 0 ? suggestions.length - 1 : active - 1);
      [...$('followers-options').children].forEach((option,i) => option.setAttribute('aria-selected',String(i === active)));
      const option = $('followers-options').children[active];
      $('followers-search').setAttribute('aria-activedescendant',option.id); option.scrollIntoView?.({block:'nearest'});
    } else if (event.key === 'Enter' && !$('followers-options').hidden && active >= 0) { event.preventDefault(); choose(suggestions[active]); }
  });
  $('followers-options').addEventListener('mousedown',event => event.preventDefault());
  $('followers-options').addEventListener('pointerdown',() => { choosing = true; });
  function finish() { choosing = false; setTimeout(() => { if (document.activeElement !== $('followers-search')) close(); },0); }
  document.addEventListener('pointerup',finish); document.addEventListener('pointercancel',finish);
  $('followers-options').addEventListener('click',event => { const option = event.target.closest('[role=option]'); if (option) choose(suggestions[Number(option.dataset.index)]); });
  document.addEventListener('pointerdown',event => { if (!event.target.closest('.social-combobox')) close(); });
  $('followers-clear').addEventListener('mousedown',event => event.preventDefault());
  $('followers-clear').addEventListener('click',() => { choose(null); $('followers-search').focus(); });
  $('followers-refresh').addEventListener('click',consult);
  $('followers-period').addEventListener('change',render);
  $('followers-discover').addEventListener('click',async () => {
    if (!selected) return;
    const token = ++discoveryRevision, member = selected;
    $('followers-discover').disabled = true; $('followers-candidates').replaceChildren();
    $('followers-discovery-status').textContent = 'Revisando la ficha institucional…';
    try {
      const data = await api('/api/social/discover',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({member_id:member.id})});
      if (token !== discoveryRevision || selected?.id !== member.id) return;
      if (data.member_id !== member.id || !Array.isArray(data.candidates)) throw new Error('La respuesta no corresponde a la persona.');
      $('followers-discovery-status').textContent = data.status === 'source_unavailable' ? 'No se pudo leer la ficha institucional. No se sortean bloqueos de acceso.' : data.candidates.length ? data.message : 'No se encontraron enlaces de perfiles compatibles. Puedes abrir el buscador; no se asignó ninguna cuenta.';
      for (const candidate of data.candidates) { const row = el('li'); row.append(link(candidate.platform + ' · candidato pendiente de corroboración',candidate.url)); $('followers-candidates').append(row); }
    } catch (_) { if (token === discoveryRevision) $('followers-discovery-status').textContent = 'No fue posible completar la búsqueda de cuentas.'; }
    finally { if (token === discoveryRevision) $('followers-discover').disabled = !selected; }
  });
  if (!window.RadarCongress?.catalogReady) { $('followers-search-status').textContent = 'No se pudo iniciar el directorio.'; return; }
  window.RadarCongress.catalogReady.then(catalog => {
    if (!catalog) throw new Error('No se pudo cargar el directorio. Recarga para reintentarlo.');
    index = window.RadarCongress.createIndex(catalog.members); ready = true;
    if (document.activeElement === $('followers-search')) showSuggestions();
    try { if ((window.RadarNative?.storage || sessionStorage).getItem('radar:tab:v1') === 'social') window.showTab('social'); } catch (_) { /* Optional view preference. */ }
  }).catch(error => { $('followers-search-status').textContent = error.message; });
  api('/api/social/status').then(state => {
    $('followers-service').textContent = state.youtube_configured
      ? 'Conexión YouTube configurada; cada consulta comprobará el acceso y el canal. Las demás redes siguen pendientes.'
      : 'Conexión pendiente: todavía no se obtienen seguidores automáticamente. Falta habilitar la clave de YouTube y corroborar las cuentas.';
  }).catch(() => { $('followers-service').textContent = 'No se pudo comprobar el estado de las conexiones. No se muestran cifras de sustitución.'; });
})();
