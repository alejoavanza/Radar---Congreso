(function () {
  'use strict';
  const model = window.RadarSocialModel, $ = id => document.getElementById(id);
  const labels = {instagram: 'Instagram', facebook: 'Facebook', tiktok: 'TikTok', youtube: 'YouTube', x: 'X'};
  const metricLabels = {followers: 'Seguidores / suscriptores', views: 'Visualizaciones diarias', interactions: 'Interacciones diarias', posts: 'Publicaciones diarias', impressions: 'Impresiones diarias', reach: 'Alcance diario'};
  const colors = {instagram: '#a23c69', facebook: '#2166b0', tiktok: '#263e43', youtube: '#b72e35', x: '#59636b'};
  const number = value => new Intl.NumberFormat('es-CO', {maximumFractionDigits: 1}).format(value);
  const dateLabel = date => new Date(`${date}T12:00:00Z`).toLocaleDateString('es-CO', {day: 'numeric', month: 'short', year: 'numeric', timeZone: 'America/Bogota'});
  const shortDate = date => new Date(`${date}T12:00:00Z`).toLocaleDateString('es-CO', {day: 'numeric', month: 'short', timeZone: 'America/Bogota'});
  const compact = value => new Intl.NumberFormat('es-CO', {notation: 'compact', maximumFractionDigits: 1}).format(value);
  let records = [], members = [], current = null, busy = false;
  let memberIndex = [], suggestions = [], active = -1, choosing = false;
  function el(tag, text, className) {
    const node = document.createElement(tag);
    if (text !== undefined) node.textContent = text;
    if (className) node.className = className;
    return node;
  }
  function svgEl(tag, attrs = {}, text) {
    const node = document.createElementNS('http://www.w3.org/2000/svg', tag);
    for (const [key, value] of Object.entries(attrs)) node.setAttribute(key, value);
    if (text !== undefined) node.textContent = text;
    return node;
  }
  function draw(container, points, start, end, color, label, empty) {
    container.replaceChildren();
    if (!points.length) { container.append(el('p', empty, 'social-empty')); return; }
    const width = 600, height = 210, left = 65, right = 568, top = 22, bottom = 176;
    const svg = svgEl('svg', {viewBox: `0 0 ${width} ${height}`, role: 'img', 'aria-label': label});
    svg.append(svgEl('title', {}, label), svgEl('desc', {}, 'Puntos observados sin interpolación. Cifras exactas disponibles en la tabla de fuentes.'));
    const max = Math.max(1, ...points.map(point => point.value)) * 1.12;
    const x = date => left + (Date.parse(date) - Date.parse(start)) / Math.max(86400000, Date.parse(end) - Date.parse(start)) * (right - left);
    const y = value => bottom - value / max * (bottom - top);
    for (const value of [0, max / 2, max]) {
      svg.append(svgEl('line', {x1: left, x2: right, y1: y(value), y2: y(value), stroke: '#c4d3d2'}));
      svg.append(svgEl('text', {x: left - 8, y: y(value) + 4, 'text-anchor': 'end', 'font-size': 13, fill: '#526568'}, compact(value)));
    }
    svg.append(svgEl('text', {x: left, y: 203, 'font-size': 13, fill: '#526568'}, shortDate(start)));
    svg.append(svgEl('text', {x: right, y: 203, 'text-anchor': 'end', 'font-size': 13, fill: '#526568'}, shortDate(end)));
    for (const point of points) {
      const dot = svgEl('circle', {cx: x(point.date), cy: y(point.value), r: points.length > 80 ? 2.5 : 4, fill: color});
      dot.append(svgEl('title', {}, `${dateLabel(point.date)}: ${number(point.value)}`));
      svg.append(dot);
    }
    container.append(svg);
  }
  function description(series, metric, expectedDays) {
    if (!series.last) return 'Sin registros para este periodo.';
    return `${series.count} de ${expectedDays} fechas con datos. Última observación: ${dateLabel(series.last.date)}.`;
  }
  function changeDescription(series, metric) {
    if (metric !== 'followers') return 'La cifra corresponde al último día observado, no al acumulado del periodo.';
    if (series.growth === null) return 'Crecimiento: N/D. Se necesitan al menos dos fechas con datos.';
    const change = `${series.growth > 0 ? '+' : ''}${number(series.growth)}`;
    const percent = series.percent === null ? 'porcentaje N/D: base cero' : `${series.percent > 0 ? '+' : ''}${number(series.percent)} %`;
    return `Cambio observado: ${change} (${percent}), entre ${dateLabel(series.first.date)} y ${dateLabel(series.last.date)}.`;
  }
  function render() {
    if (!members.length) return;
    const memberId = $('social-member').value;
    const metric = $('social-metric').value;
    const period = $('social-period').value;
    const selected = [...document.querySelectorAll('.social-networks input:checked')].map(input => input.value);
    current = model.calculate(records, memberId, period, metric, selected);
    $('social-window').textContent = `${dateLabel(current.start)} a ${dateLabel(current.end)} · Corte diario de Colombia`;
    $('social-member-id').textContent = memberId ? `Identificador para la plantilla: ${memberId}` : 'Selecciona un congresista para descargar su plantilla.';
    $('social-total-title').textContent = metric === 'followers' ? 'Seguidores sumados · última fecha común' : metric === 'reach' ? 'Alcance: consulta cada red' : `${metricLabels[metric]} · total`;
    $('social-total-value').textContent = current.total.last ? number(current.total.last.value) : 'N/D';
    const totalNote = metric === 'reach' ? 'El alcance no se suma: una persona puede estar en varias redes.' : `${selected.length} redes seleccionadas. ${description(current.total, metric, current.expectedDays)} ${metric === 'followers' ? 'La suma no representa personas únicas.' : 'Las definiciones pueden variar entre redes.'}`;
    $('social-total-note').textContent = totalNote;
    $('social-total-change').textContent = metric === 'reach' ? 'Consulta el alcance individual de cada red.' : changeDescription(current.total, metric);
    $('social-data-state').textContent = !records.length
      ? 'Sin datos importados. Este buscador selecciona una persona; no consulta sus redes automáticamente. Los ejemplos son simulados.'
      : !memberId ? 'Selecciona una persona para consultar los registros importados. El origen de las cifras no ha sido verificado.'
      : !current.rows.length ? 'Sin registros para esta persona y periodo. N/D significa dato no disponible, no cero.'
      : `${current.rows.length} registros importados para esta persona y periodo. Origen no verificado; no son datos obtenidos automáticamente.`;
    $('social-charts').hidden = !current.rows.length;
    draw($('social-total-chart'), current.total.points, current.start, current.end, '#075056', $('social-total-title').textContent,
      metric === 'reach' ? 'Revisa el alcance individual en los gráficos de abajo.' : !selected.length ? 'Selecciona al menos una red para calcular el total.' : 'No hay fechas con datos en todas las redes seleccionadas. Importa registros o ajusta las redes del total.');
    $('social-charts').replaceChildren();
    for (const platform of model.platforms) {
      const series = current.series[platform];
      const section = el('section', undefined, 'social-network');
      const heading = el('div', undefined, 'social-chart-heading');
      heading.append(el('h3', labels[platform]), el('strong', series.last ? number(series.last.value) : 'N/D'));
      const chart = el('div', undefined, 'social-chart');
      section.append(heading, el('p', metric === 'followers' ? 'Seguidores / suscriptores al último registro' : metricLabels[metric], 'note'), el('p', changeDescription(series, metric), 'social-change'), chart, el('p', description(series, metric, current.expectedDays), 'note'));
      draw(chart, series.points, current.start, current.end, colors[platform], `${labels[platform]}: ${metricLabels[metric]}`, 'Sin datos en este rango. No equivale a cero.');
      $('social-charts').append(section);
    }
    $('social-table').replaceChildren();
    // Keep the DOM bounded while the complete imported set remains exportable.
    for (const row of current.rows.slice(-500).reverse()) {
      const tr = el('tr');
      tr.append(el('td', dateLabel(row.date)), el('td', labels[row.platform]), el('td', row.account), el('td', row[metric] === null ? 'N/D' : number(row[metric])));
      const cell = el('td'), link = el('a', 'Ver fuente');
      link.href = row.source; link.target = '_blank'; link.rel = 'noopener noreferrer';
      cell.append(link); tr.append(cell); $('social-table').append(tr);
    }
    if (!current.rows.length) { const cell = el('td', 'Sin registros importados para esta persona y periodo.'); cell.colSpan = 5; const row = el('tr'); row.append(cell); $('social-table').append(row); }
    $('social-table-caption').textContent = `${metricLabels[metric]} · ${current.rows.length} registros importados, origen no verificado${current.rows.length > 500 ? ' · se muestran los 500 más recientes; la exportación incluye todos' : ''}`;
    $('social-export').disabled = !records.length || busy;
    $('social-clear').disabled = !records.length || busy;
    $('social-template').disabled = !memberId || busy;
    window.RadarSocialExport?.update({current, member: members.find(member => member.id === memberId), metric, busy});
  }
  function closeSuggestions() {
    $('social-options').hidden = true;
    $('social-search').setAttribute('aria-expanded', 'false');
    $('social-search').removeAttribute('aria-activedescendant');
    active = -1;
  }
  function selectMember(member) {
    $('social-member').value = member?.id || '';
    $('social-search').value = member?.display_name || '';
    $('social-search-status').textContent = member
      ? `${member.display_name} · ${member.chamber === 'camara' ? 'Cámara' : 'Senado'} · ${member.constituency || ''}`
      : 'Escribe al menos dos letras y selecciona una coincidencia.';
    closeSuggestions();
    render();
  }
  function showSuggestions() {
    if ($('social-member').value) return closeSuggestions();
    const result = window.RadarCongress.findMatches(memberIndex, $('social-search').value);
    suggestions = result.members;
    active = -1;
    $('social-search').removeAttribute('aria-activedescendant');
    $('social-options').replaceChildren(...suggestions.map((member, i) => {
      const option = el('li');
      option.id = `social-option-${i}`;
      option.dataset.index = i;
      option.setAttribute('role', 'option');
      option.setAttribute('aria-selected', 'false');
      option.append(el('span', member.display_name, 'social-option-name'),
        el('span', `${member.chamber === 'camara' ? 'Cámara' : 'Senado'} · ${member.constituency || ''}`, 'social-option-detail'));
      return option;
    }));
    if (!suggestions.length) {
      $('social-search-status').textContent = window.RadarCongress.normalize($('social-search').value).replace(/ /g, '').length < 2
        ? 'Escribe al menos dos letras y selecciona una coincidencia.'
        : 'Sin coincidencias en el directorio. Revisa el nombre; no se seleccionó otra persona.';
      return closeSuggestions();
    }
    $('social-options').hidden = false;
    $('social-search').setAttribute('aria-expanded', 'true');
    $('social-search-status').textContent = `${suggestions.length} de ${result.total} coincidencias. Selecciona la persona que buscas.`;
  }
  function setActive(i) {
    active = i;
    [...$('social-options').children].forEach((option, j) => option.setAttribute('aria-selected', String(j === i)));
    const option = $('social-options').children[i];
    $('social-search').setAttribute('aria-activedescendant', option.id);
    option.scrollIntoView?.({block: 'nearest'});
  }
  function download(text, filename) {
    const url = URL.createObjectURL(new Blob(['\ufeff', text], {type: 'text/csv;charset=utf-8'}));
    const link = el('a'); link.href = url; link.download = filename; document.body.append(link); link.click(); link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  $('social-search').addEventListener('input', () => {
    // A partial name must never display another person's previously selected data.
    $('social-member').value = '';
    showSuggestions();
    render();
  });
  $('social-search').addEventListener('focus', showSuggestions);
  $('social-search').addEventListener('blur', () => { if (!choosing) closeSuggestions(); });
  $('social-search').addEventListener('keydown', event => {
    if (event.isComposing) return;
    if (event.key === 'Escape' || event.key === 'Tab') { closeSuggestions(); return; }
    if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
      if ($('social-options').hidden) showSuggestions();
      if ($('social-options').hidden) return;
      event.preventDefault();
      setActive(event.key === 'ArrowDown' ? (active + 1) % suggestions.length : (active < 0 ? suggestions.length - 1 : (active - 1 + suggestions.length) % suggestions.length));
    } else if (event.key === 'Enter' && !$('social-options').hidden && active >= 0) {
      event.preventDefault();
      selectMember(suggestions[active]);
    }
  });
  $('social-search-clear').addEventListener('mousedown', event => event.preventDefault());
  $('social-search-clear').addEventListener('click', () => {
    selectMember(null); $('social-search').focus();
  });
  $('social-options').addEventListener('mousedown', event => event.preventDefault());
  $('social-options').addEventListener('pointerdown', () => { choosing = true; });
  function finishChoice() {
    if (!choosing) return;
    choosing = false;
    setTimeout(() => { if (document.activeElement !== $('social-search')) closeSuggestions(); }, 0);
  }
  document.addEventListener('pointerup', finishChoice);
  document.addEventListener('pointercancel', finishChoice);
  $('social-options').addEventListener('click', event => {
    const option = event.target.closest('[role="option"]');
    const member = option && suggestions[Number(option.dataset.index)];
    if (member) { selectMember(member); $('social-search').focus(); }
  });
  document.addEventListener('pointerdown', event => {
    if (!event.target.closest('.social-combobox')) closeSuggestions();
  });
  $('social-metric').addEventListener('change', render);
  $('social-period').addEventListener('change', render);
  for (const input of document.querySelectorAll('.social-networks input')) input.addEventListener('change', render);
  $('social-template').addEventListener('click', () => {
    const template = model.platforms.map(platform => ({member_id: $('social-member').value, platform, date: model.bogotaToday()}));
    download(model.csv(template), 'radar-plus-plantilla.csv');
  });
  $('social-export').addEventListener('click', () => download(model.csv(records), `radar-plus-registros-${model.bogotaToday()}.csv`));
  $('social-clear').addEventListener('click', () => {
    records = []; $('social-file').value = ''; $('social-import-status').textContent = 'Carga borrada de esta pestaña.'; $('social-error').textContent = ''; render();
  });
  $('social-file').addEventListener('change', async () => {
    const file = $('social-file').files[0];
    if (!file || busy) return;
    $('social-error').textContent = '';
    if (file.size > 2 * 1024 * 1024) { $('social-error').textContent = 'El archivo supera los 2 MB.'; $('social-file').value = ''; return; }
    busy = true; $('social-file').disabled = true; render();
    $('social-import-status').textContent = 'Validando registros…';
    const controller = new AbortController(), timeout = setTimeout(() => controller.abort(), 20000);
    try {
      const form = new FormData(); form.append('file', file);
      const response = await fetch('/api/social/import', {method: 'POST', body: form, signal: controller.signal, cache: 'no-store'});
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || 'No se pudo importar el archivo.');
      const start = model.windowStart(data.as_of, '12m');
      const retained = data.records.filter(row => row.date >= start && row.date <= data.as_of);
      if (!retained.length) throw new Error('No hay registros dentro de los últimos 12 meses. Se conserva la carga anterior.');
      records = retained;
      const skipped = data.records.length - records.length;
      selectMember(members.find(member => member.id === records[0].member_id));
      $('social-import-status').textContent = `${records.length} registros importados en esta pestaña. Origen no verificado por la plataforma.${skipped ? ` ${skipped} registros anteriores a 12 meses excluidos.` : ''} Exporta una copia antes de cerrar.`;
    } catch (error) {
      $('social-error').textContent = error.name === 'AbortError' ? 'La importación tardó demasiado. Inténtalo de nuevo.' : error.message;
      $('social-import-status').textContent = `No se reemplazó la carga anterior: ${records.length} registros conservados.`;
    } finally { clearTimeout(timeout); busy = false; $('social-file').disabled = false; $('social-file').value = ''; render(); }
  });
  window.addEventListener('beforeunload', event => { if (records.length) { event.preventDefault(); event.returnValue = ''; } });
  const catalogReady = window.RadarCongress?.catalogReady;
  if (!catalogReady) { $('social-error').textContent = 'No se pudo iniciar el directorio de congresistas.'; return; }
  catalogReady.then(data => {
    if (!data) throw new Error('No se pudo cargar el directorio. Recarga la página.');
    members = data.members;
    $('social-directory').textContent = `${members.length} personas en el directorio · revisión: ${dateLabel(data.checked_at)}. Puede requerir actualización por cambios de curul.`;
    memberIndex = window.RadarCongress.createIndex(members);
    $('social-search').disabled = false; $('social-search-clear').disabled = false; $('social-file').disabled = false;
    selectMember(members.find(member => member.id === window.RadarCongress.selectedId?.()));
    try { if ((window.RadarNative?.storage || sessionStorage).getItem('radar:tab:v1') === 'social') window.showTab('social'); } catch (_) { /* Optional view preference. */ }
  }).catch(error => { $('social-error').textContent = error.message; $('social-search-status').textContent = 'El directorio no está disponible. Inténtalo de nuevo al recargar.'; });
})();
