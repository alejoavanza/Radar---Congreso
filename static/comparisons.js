(function (root) {
  'use strict';
  const isAvailable = source => source?.status === 'available' && Number.isFinite(source.count) && source.count >= 0;

  function summarize(rows) {
    return {
      rows: rows.map(row => ({
        ...row,
        // Saved comparisons may still contain social results; only web is displayed.
        sources: {Web: row.sources?.Web},
        web: isAvailable(row.sources?.Web) ? row.sources.Web.count : null,
        webLimited: !!row.sources?.Web?.limited
      }))
    };
  }

  function sortRows(rows, order) {
    const collator = new Intl.Collator('es', {sensitivity: 'base'});
    return [...rows].sort((a, b) => {
      const names = collator.compare(a.member.display_name, b.member.display_name);
      if (order === 'name') return names;
      const left = a.web, right = b.web;
      if (left === null) return right === null ? names : 1;
      if (right === null) return -1;
      return right - left || names;
    });
  }

  if (typeof module !== 'undefined' && module.exports) module.exports = {summarize, sortRows};
  if (!root.document) return;
  const $ = id => document.getElementById(id);
  if (!$('comparetab')) return;
  const input = $('compare-name'), list = $('compare-options'), status = $('compare-picker-status');
  const form = $('compare-form'), run = $('compare-run'), progress = $('compare-progress');
  const results = $('compare-results'), chart = $('compare-chart');
  const STORAGE = 'radar:comparison:web:v2';
  let selected = [], catalog = null, index = [], suggestions = [], active = -1;
  let snapshot = null, running = false, choosing = false;
  const fmt = value => new Intl.NumberFormat('es-CO').format(value);
  const valueText = (value, limited) => value === null ? 'No disponible' : fmt(value) + (limited ? '+' : '');

  function el(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  }

  function link(text, url) {
    try {
      const target = new URL(url);
      if (!['https:', 'http:'].includes(target.protocol) || target.username || target.password) return el('span', '', text);
      const node = el('a', '', text);
      node.href = target.href; node.target = '_blank'; node.rel = 'noopener noreferrer';
      return node;
    } catch (_) { return el('span', '', text); }
  }

  function persist() {
    try {
      sessionStorage.setItem(STORAGE, JSON.stringify({
        ids: selected.map(member => member.id), days: +$('compare-days').value,
        territory: $('compare-territory').value, order: $('compare-order').value, snapshot
      }));
    } catch (_) { /* Storage restrictions must not block a comparison. */ }
  }

  function dirty() {
    snapshot = null;
    results.hidden = true;
    progress.textContent = '';
    $('compare-error').textContent = '';
    persist();
  }

  function closePicker() {
    list.hidden = true;
    input.setAttribute('aria-expanded', 'false');
    input.removeAttribute('aria-activedescendant');
    active = -1;
  }

  function renderSelected() {
    const target = $('compare-selected');
    target.replaceChildren();
    for (const member of selected) {
      const row = el('li', 'compare-person');
      const name = el('div');
      name.append(el('strong', '', member.display_name), el('span', 'compare-person-detail', `${member.chamber === 'camara' ? 'Cámara' : 'Senado'} · ${member.constituency}`));
      const remove = el('button', 'compare-remove', 'Quitar');
      remove.type = 'button'; remove.disabled = running;
      remove.setAttribute('aria-label', `Quitar a ${member.display_name}`);
      remove.addEventListener('click', () => {
        selected = selected.filter(item => item.id !== member.id);
        renderSelected(); dirty(); input.focus();
      });
      row.append(name, remove); target.append(row);
    }
    $('compare-selection-count').textContent = `${selected.length} de 10 seleccionados. Puedes comparar entre 2 y 10 congresistas.`;
    input.disabled = running || !catalog || selected.length >= 10;
    run.disabled = running || !catalog || selected.length < 2;
  }

  function choose(member) {
    if (running || selected.length >= 10 || selected.some(item => item.id === member.id)) return;
    selected.push(member);
    input.value = '';
    closePicker(); renderSelected(); dirty();
    status.textContent = `${member.display_name} agregado. ${selected.length} seleccionados.`;
    if (!input.disabled) input.focus();
    else run.focus();
  }

  function renderPicker() {
    const available = index.filter(entry => !selected.some(member => member.id === entry.member.id));
    const match = root.RadarCongress.findMatches(available, input.value);
    suggestions = match.members;
    list.replaceChildren(); active = -1;
    input.removeAttribute('aria-activedescendant');
    if (!suggestions.length) {
      closePicker();
      status.textContent = input.value.trim().length >= 2 ? 'Sin coincidencias entre los congresistas que puedes agregar.' : '';
      return;
    }
    for (const [i, member] of suggestions.entries()) {
      const option = el('li');
      option.id = `compare-option-${i}`; option.dataset.index = i;
      option.setAttribute('role', 'option'); option.setAttribute('aria-selected', 'false');
      option.append(el('span', 'congress-option-name', member.display_name),
        el('span', 'congress-option-detail', `${member.chamber === 'camara' ? 'Cámara' : 'Senado'} · ${member.constituency}`));
      list.append(option);
    }
    list.hidden = false; input.setAttribute('aria-expanded', 'true');
    status.textContent = `${suggestions.length} de ${match.total} coincidencias. Elige un nombre para agregarlo.`;
  }

  input.addEventListener('input', renderPicker);
  for (const [field, buttonId] of [[input, 'clear-compare-name'], [$('compare-territory'), 'clear-compare-territory']]) {
    const button = $(buttonId);
    button?.addEventListener('mousedown', event => event.preventDefault());
    button?.addEventListener('click', () => {
      if (field.disabled) return;
      field.value = '';
      field.dispatchEvent(new Event('input', {bubbles: true}));
      field.focus();
    });
  }
  input.addEventListener('focus', renderPicker);
  input.addEventListener('blur', () => { if (!choosing) closePicker(); });
  input.addEventListener('keydown', event => {
    if (event.isComposing) return;
    if (event.key === 'Escape' || event.key === 'Tab') { closePicker(); return; }
    if (event.key === 'Enter') {
      event.preventDefault();
      if (!list.hidden && active >= 0) choose(suggestions[active]);
      return;
    }
    if (event.key !== 'ArrowDown' && event.key !== 'ArrowUp') return;
    if (list.hidden) renderPicker();
    if (list.hidden) return;
    event.preventDefault();
    active = event.key === 'ArrowDown' ? (active + 1) % suggestions.length : (active < 0 ? suggestions.length - 1 : (active - 1 + suggestions.length) % suggestions.length);
    [...list.children].forEach((option, i) => option.setAttribute('aria-selected', String(i === active)));
    input.setAttribute('aria-activedescendant', list.children[active].id);
    list.children[active].scrollIntoView?.({block: 'nearest'});
  });
  list.addEventListener('mousedown', event => event.preventDefault());
  list.addEventListener('pointerdown', () => { choosing = true; });
  function finishChoice() {
    if (!choosing) return;
    choosing = false;
    setTimeout(() => { if (document.activeElement !== input) closePicker(); }, 0);
  }
  document.addEventListener('pointerup', finishChoice);
  document.addEventListener('pointercancel', finishChoice);
  document.addEventListener('pointerdown', event => {
    if (!input.parentElement.contains(event.target)) closePicker();
  });
  list.addEventListener('click', event => {
    const option = event.target.closest('[role="option"]');
    if (option) choose(suggestions[Number(option.dataset.index)]);
  });

  function drawBar(label, count, limited, max, className) {
    const line = el('div', 'compare-bar-row');
    const track = el('div', 'compare-track');
    const value = valueText(count, limited);
    line.setAttribute('aria-label', `${label}: ${value}`);
    const fill = el('div', `compare-bar ${className}`);
    fill.style.width = `${count === null || !max ? 0 : count / max * 100}%`;
    track.append(fill);
    line.append(el('span', 'compare-bar-label', label), track, el('span', count === null ? 'compare-value unavailable' : 'compare-value', count === null ? 'N/D' : value));
    return line;
  }

  function renderDetails(rows) {
    const target = $('compare-source-details'); target.replaceChildren();
    for (const row of rows) {
      const detail = el('details', 'compare-evidence');
      detail.append(el('summary', '', row.member.display_name));
      const terms = catalog?.members.find(member => member.id === row.member.id);
      if (terms) detail.append(el('p', 'note', `Búsqueda: ${terms.search_name}. Incluye su nombre completo y las variantes del directorio.`));
      const data = row.sources.Web;
      const line = el('p', 'compare-source-line');
      line.append(el('strong', '', `Web: ${valueText(isAvailable(data) ? data.count : null, data?.limited)}. `));
      line.append(document.createTextNode(data?.message || 'La consulta no pudo completarse.'));
      if (data?.url) { line.append(document.createTextNode(' '), link('Abrir fuente ↗', data.url)); }
      detail.append(line);
      const items = data?.items || [];
      if (items.length) {
        const news = el('details', 'compare-news');
        news.append(el('summary', '', `Ver ${items.length} noticias detectadas`));
        const list = el('ul');
        for (const item of items) {
          const li = el('li'); li.append(link(item.title, item.url)); list.append(li);
        }
        news.append(list); detail.append(news);
      }
      target.append(detail);
    }
  }

  function renderSnapshot() {
    if (!snapshot) return;
    const {rows} = summarize(snapshot.rows);
    const ordered = sortRows(rows, $('compare-order').value);
    const max = Math.max(0, ...rows.map(row => row.web || 0));
    const when = new Intl.DateTimeFormat('es-CO', {timeZone: 'America/Bogota', dateStyle: 'medium', timeStyle: 'short'});
    $('compare-summary').textContent = `${rows.length} congresistas · ${snapshot.meta.days === 1 ? 'Últimas 24 horas' : snapshot.meta.days + ' días'} · Zona: ${snapshot.meta.territory || 'Sin filtro de zona'}.`;
    $('compare-window').textContent = `${when.format(new Date(snapshot.meta.start_time))} — ${when.format(new Date(snapshot.meta.end_time))} (hora de Colombia).`;
    chart.replaceChildren();
    for (const row of ordered) {
      const group = el('li', 'compare-chart-person');
      group.append(el('h3', '', row.member.search_name), el('p', 'compare-person-detail', `${row.member.chamber === 'camara' ? 'Cámara' : 'Senado'} · ${row.member.constituency}`));
      group.append(drawBar('Web', row.web, row.webLimited, max, 'web-bar'));
      chart.append(group);
    }
    $('compare-scale').textContent = `Escala común: 0 a ${fmt(max)} menciones detectadas en web. N/D = no disponible. + = resultado limitado; puede haber más menciones.`;
    const table = $('compare-table-body'); table.replaceChildren();
    for (const row of ordered) {
      const tr = el('tr'); const th = el('th', '', row.member.search_name); th.scope = 'row'; tr.append(th);
      tr.append(el('td', '', valueText(row.web, row.webLimited)));
      table.append(tr);
    }
    renderDetails(ordered); results.hidden = false;
  }

  async function post(url, body, milliseconds) {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), milliseconds);
    try {
      const response = await fetch(url, {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body), signal: controller.signal});
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || 'No se pudo completar la consulta.');
      return data;
    } finally { clearTimeout(timeout); }
  }

  function failedRow(member, message) {
    return {member, sources: {Web: {status: 'unavailable', count: null, message}}};
  }

  async function compare(event) {
    event.preventDefault();
    if (running || selected.length < 2 || selected.length > 10) return;
    running = true; form.setAttribute('aria-busy', 'true');
    closePicker(); renderSelected(); results.hidden = true;
    $('compare-days').disabled = true; $('compare-territory').disabled = true;
    run.textContent = 'CONSULTANDO…'; $('compare-error').textContent = '';
    progress.textContent = 'Preparando una misma ventana de tiempo para todos…';
    try {
      const meta = await post('/api/compare/start', {member_ids: selected.map(member => member.id), days: +$('compare-days').value, territory: $('compare-territory').value}, 15000);
      const rows = new Array(meta.members.length);
      let next = 0, complete = 0;
      async function worker() {
        while (next < meta.members.length) {
          const position = next++, member = meta.members[position];
          try {
            const row = await post('/api/compare/member', {member_id: member.id, days: meta.days, territory: meta.territory, end_time: meta.end_time}, 120000);
            if (row.member?.id !== member.id || !row.sources || row.end_time !== meta.end_time || row.start_time !== meta.start_time) throw new Error('La fuente no devolvió el periodo solicitado.');
            rows[position] = row;
          } catch (error) {
            rows[position] = failedRow(member, error.name === 'AbortError' ? 'La consulta superó el tiempo de espera.' : error.message);
          }
          complete++;
          progress.textContent = `${complete} de ${meta.members.length} congresistas consultados…`;
        }
      }
      // Two people at a time: bounded traffic, progress feedback and independent failures.
      await Promise.all([worker(), worker()]);
      snapshot = {meta, rows}; renderSnapshot(); persist();
      progress.textContent = `Comparativo web listo: ${rows.length} congresistas.`;
    } catch (error) {
      progress.textContent = '';
      $('compare-error').textContent = error.name === 'AbortError' ? 'La consulta tardó demasiado. Intenta de nuevo.' : error.message;
      if (snapshot) renderSnapshot();
    } finally {
      running = false; form.setAttribute('aria-busy', 'false');
      $('compare-days').disabled = false; $('compare-territory').disabled = false;
      run.textContent = 'COMPARAR MENCIONES'; renderSelected();
    }
  }

  form.addEventListener('submit', compare);
  $('compare-days').addEventListener('change', dirty);
  $('compare-territory').addEventListener('input', dirty);
  $('compare-order').addEventListener('change', () => { renderSnapshot(); persist(); });

  root.RadarCongress.catalogReady.then(data => {
    if (!data) { $('compare-error').textContent = 'No se pudo cargar el directorio. Recarga la página para elegir congresistas.'; return; }
    catalog = data; index = root.RadarCongress.createIndex(catalog.members);
    try {
      const saved = JSON.parse(sessionStorage.getItem(STORAGE));
      if (saved && Array.isArray(saved.ids)) {
        selected = [...new Set(saved.ids)].map(id => catalog.members.find(member => member.id === id)).filter(Boolean).slice(0, 10);
        if ([90, 60, 30, 7, 1].includes(saved.days)) $('compare-days').value = saved.days;
        if (typeof saved.territory === 'string') $('compare-territory').value = saved.territory;
        // Migrate the old social sort to web while preserving saved web results.
        $('compare-order').value = saved.order === 'name' ? 'name' : 'web';
        if (saved.snapshot?.meta && Array.isArray(saved.snapshot.rows) && saved.snapshot.rows.length === selected.length
          && saved.snapshot.meta.days === +$('compare-days').value && saved.snapshot.meta.territory === $('compare-territory').value.trim()
          && saved.snapshot.rows.every((row, i) => row.member?.id === selected[i].id && row.sources)
          && Number.isFinite(Date.parse(saved.snapshot.meta.start_time)) && Number.isFinite(Date.parse(saved.snapshot.meta.end_time))) {
          snapshot = saved.snapshot; renderSnapshot(); progress.textContent = 'Comparativo recuperado. Pulsa Comparar menciones para actualizarlo.';
        }
      }
    } catch (_) { /* Old or unavailable storage leaves a fresh form. */ }
    renderSelected();
  });
  try { if (sessionStorage.getItem('radar:tab:v1') === 'compare') root.showTab('compare'); } catch (_) { /* Optional state. */ }
})(typeof window === 'undefined' ? globalThis : window);
