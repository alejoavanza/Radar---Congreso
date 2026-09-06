(function (root) {
  'use strict';

  function normalize(value) {
    return String(value || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '')
      .toLocaleLowerCase('es').replace(/[^a-z0-9]+/g, ' ').trim();
  }

  function createIndex(members) {
    const collator = new Intl.Collator('es', {sensitivity: 'base'});
    return [...members].sort((a, b) => collator.compare(a.display_name, b.display_name))
      .map(member => ({member, words: [...new Set(normalize([
        member.full_name, member.search_name, ...member.aliases
      ].join(' ')).split(' '))]}));
  }

  function findMatches(index, value, limit = 8) {
    const query = normalize(value);
    if (query.replace(/ /g, '').length < 2) return {members: [], total: 0};
    const tokens = query.split(' ');
    const matches = index.filter(entry => tokens.every(token => entry.words.some(word => word.startsWith(token))));
    return {members: matches.slice(0, limit).map(entry => entry.member), total: matches.length};
  }

  function buildSearch(name, manualAliases, member) {
    if (!member || normalize(name) !== normalize(member.display_name)) {
      return {name: name.trim(), aliases: manualAliases};
    }
    const seen = new Set([normalize(member.search_name)]);
    const aliases = [manualAliases, ...member.aliases, member.full_name].join(',').split(',')
      .map(value => value.trim()).filter(value => {
        const key = normalize(value);
        if (!key || seen.has(key)) return false;
        seen.add(key);
        return true;
      });
    return {name: member.search_name, aliases: aliases.join(', ')};
  }

  function resolveMember(index, value, selectedId = null) {
    // Resolve complete known names, not the first autocomplete suggestion.
    // Sorting words also accepts surnames first, with or without the comma.
    const key = name => normalize(name).split(' ').sort().join(' ');
    const query = key(value);
    if (!query || query.split(' ').length < 2) return null;
    const matches = index.filter(({member}) => [
      member.full_name, member.display_name, member.search_name, ...member.aliases
    ].some(name => key(name) === query)).map(({member}) => member);
    const selected = matches.find(member => member.id === selectedId);
    return selected || (matches.length === 1 ? matches[0] : null);
  }

  const api = {normalize, createIndex, findMatches, buildSearch, resolveMember};
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  if (!root.document) return;

  const input = document.getElementById('name');
  const list = document.getElementById('congress-options');
  const status = document.getElementById('congress-status');
  const selectedNote = document.getElementById('congress-selected');
  const catalogNote = document.getElementById('congress-catalog');
  if (!input || !list) return;
  let index = [], suggestions = [], active = -1, selected = null;
  let ready = false, failed = false, pendingRestore = null, choosing = false;

  function close() {
    list.hidden = true;
    input.setAttribute('aria-expanded', 'false');
    input.removeAttribute('aria-activedescendant');
    active = -1;
  }

  function clearSelection() {
    selected = null;
    pendingRestore = null;
    selectedNote.textContent = '';
    selectedNote.hidden = true;
  }

  function select(member) {
    selected = member;
    input.value = member.display_name;
    selectedNote.textContent = `${member.chamber === 'camara' ? 'Cámara de Representantes' : 'Senado'} · ${member.constituency}. Búsqueda: ${member.search_name}; incluye su nombre completo.`;
    selectedNote.hidden = false;
    status.textContent = `${member.display_name} seleccionado.`;
    close();
  }

  function render() {
    if (selected && normalize(input.value) === normalize(selected.display_name)) return close();
    list.replaceChildren();
    active = -1;
    input.removeAttribute('aria-activedescendant');
    const result = findMatches(index, input.value);
    suggestions = result.members;
    if (normalize(input.value).replace(/ /g, '').length < 2) {
      status.textContent = '';
      return close();
    }
    if (!ready || failed) {
      status.textContent = failed ? 'Puedes continuar escribiendo y generar el reporte.' : 'Cargando nombres…';
      return close();
    }
    if (!suggestions.length) {
      status.textContent = 'Sin coincidencias en el directorio. Puedes buscar el nombre que escribiste.';
      return close();
    }
    for (const [i, member] of suggestions.entries()) {
      const option = document.createElement('li');
      option.id = `congress-option-${i}`;
      option.setAttribute('role', 'option');
      option.setAttribute('aria-selected', 'false');
      option.dataset.index = i;
      const name = document.createElement('span');
      name.className = 'congress-option-name';
      name.textContent = member.display_name;
      const detail = document.createElement('span');
      detail.className = 'congress-option-detail';
      detail.textContent = `${member.chamber === 'camara' ? 'Cámara' : 'Senado'} · ${member.constituency} · ${member.party}`;
      option.append(name, detail);
      list.append(option);
    }
    list.hidden = false;
    input.setAttribute('aria-expanded', 'true');
    status.textContent = result.total > suggestions.length
      ? `${suggestions.length} de ${result.total} coincidencias. Sigue escribiendo para precisar.`
      : `${result.total} ${result.total === 1 ? 'coincidencia' : 'coincidencias'}. Elige una o continúa con tu búsqueda.`;
  }

  function setActive(i) {
    active = i;
    for (const [j, option] of [...list.children].entries()) option.setAttribute('aria-selected', String(j === i));
    const option = list.children[i];
    input.setAttribute('aria-activedescendant', option.id);
    option.scrollIntoView?.({block: 'nearest'});
  }

  input.addEventListener('input', () => { clearSelection(); render(); });
  input.addEventListener('focus', render);
  input.addEventListener('blur', () => { if (!choosing) close(); });
  input.addEventListener('keydown', event => {
    if (event.isComposing) return;
    if (event.key === 'Escape') {
      close();
      status.textContent = '';
      return;
    }
    if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
      if (list.hidden) render();
      if (list.hidden) return;
      event.preventDefault();
      setActive(event.key === 'ArrowDown' ? (active + 1) % suggestions.length : (active < 0 ? suggestions.length - 1 : (active - 1 + suggestions.length) % suggestions.length));
    } else if (event.key === 'Enter' && !list.hidden && active >= 0) {
      event.preventDefault();
      select(suggestions[active]);
    } else if (event.key === 'Tab') {
      close();
    }
  });
  // Keep input focus for a mouse/touch choice; a touch scroll never selects a name.
  list.addEventListener('mousedown', event => event.preventDefault());
  list.addEventListener('pointerdown', () => { choosing = true; });
  function finishChoice() {
    if (!choosing) return;
    choosing = false;
    setTimeout(() => { if (document.activeElement !== input) close(); }, 0);
  }
  document.addEventListener('pointercancel', finishChoice);
  document.addEventListener('pointerup', finishChoice);
  list.addEventListener('click', event => {
    const option = event.target.closest('[role="option"]');
    if (!option) return;
    const member = suggestions[Number(option.dataset.index)];
    if (member) { select(member); input.focus(); }
  });
  document.addEventListener('pointerdown', event => {
    if (!event.target.closest('.congress-combobox')) close();
  });

  root.RadarCongress = {
    ...api,
    query: () => buildSearch(input.value, document.getElementById('aliases').value, selected),
    selectedId: () => selected?.id || null,
    findMember: (name, selectedId) => resolveMember(index, name, selectedId),
    restore: id => {
      if (!ready) { pendingRestore = {id, value: input.value}; return; }
      const member = index.find(entry => entry.member.id === id)?.member;
      if (member && [member.display_name, member.search_name].some(name => normalize(input.value) === normalize(name))) select(member);
    }
  };

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 10000);
  root.RadarCongress.catalogReady = fetch('/static/congress-members.json?v=profiles-2026-09-06', {signal: controller.signal})
    .then(response => { if (!response.ok) throw new Error('Directory unavailable'); return response.json(); })
    .then(catalog => {
      if (!Array.isArray(catalog.members) || !catalog.members.length || catalog.members.some(member =>
        !member.id || !member.display_name || !member.full_name || !member.search_name || !Array.isArray(member.aliases))) throw new Error('Invalid directory');
      index = createIndex(catalog.members);
      ready = true;
      const [year, month, day] = catalog.checked_at.split('-');
      catalogNote.textContent = `${catalog.members.length} nombres · Directorios oficiales consultados el ${day}/${month}/${year}.`;
      if (pendingRestore && pendingRestore.value === input.value) root.RadarCongress.restore(pendingRestore.id);
      pendingRestore = null;
      if (document.activeElement === input) render();
      return catalog;
    })
    .catch(() => {
      failed = true;
      catalogNote.textContent = 'El directorio no está disponible. La búsqueda libre sigue funcionando.';
      if (document.activeElement === input) render();
      return null;
    })
    .finally(() => clearTimeout(timeout));
})(typeof window === 'undefined' ? globalThis : window);
