const reportStorageKey = 'radar:report:web:v3';
const reportStorage = window.RadarNative?.storage || sessionStorage;
let currentReport = null;
let currentQuery = null;
let currentForm = null;
let reportSearchSequence = 0;

function webOnlyReport(report) {
  const web = Number.isFinite(report.mentions?.web) ? report.mentions.web : Number(report.total) || 0;
  // Older clients may restore totals that included social networks.
  return {...report, total:web, mentions:{web, combined:web, note:'Publicaciones detectadas en medios web.'}};
}

async function showOfficialProfile(query, selectedId, searchSequence) {
  const card = $('official-profile');
  if (!card) return;
  card.replaceChildren();
  card.classList.add('hide');
  try {
    await window.RadarCongress?.catalogReady;
    if (searchSequence !== reportSearchSequence) return;
    const member = window.RadarCongress?.findMember(query.name, selectedId);
    if (!member) return;
    const individual = Boolean(member.profile_url);
    const url = new URL(individual ? member.profile_url : member.source_url);
    const host = member.chamber === 'camara' ? 'www.camara.gov.co' : 'www.senado.gov.co';
    if (url.protocol !== 'https:' || url.hostname !== host || url.username || url.password || url.port) return;
    if (!individual) url.hash = ':~:text=' + encodeURIComponent(`${member.surnames} ${member.given_names}`);
    const chamber = member.chamber === 'camara' ? 'Cámara de Representantes' : 'Senado de la República';
    const label = document.createElement('p');
    label.className = 'official-profile-label';
    label.textContent = `${individual ? 'Perfil oficial' : 'Ficha en el directorio oficial'} · ${chamber}`;
    const heading = document.createElement('h2');
    heading.id = 'official-profile-title';
    heading.textContent = member.full_name;
    const details = document.createElement('p');
    details.className = 'note';
    details.textContent = `${member.party} · ${member.constituency}`;
    const link = document.createElement('a');
    link.href = url.href;
    link.target = '_blank';
    link.rel = 'noopener noreferrer external';
    link.dataset.newsSource = 'true';
    link.textContent = individual ? `Ver perfil en ${chamber} →` : 'Ver ficha en el directorio del Senado →';
    link.setAttribute('aria-label', `${link.textContent.replace(' →', '')}: ${member.full_name} (abre en otra pestaña)`);
    card.append(label, heading, details, link);
    if (!individual) {
      const note = document.createElement('p');
      note.className = 'note';
      note.textContent = 'El directorio del Senado no enlaza una página individual para este registro.';
      card.append(note);
    }
    const note = document.createElement('p');
    note.className = 'note official-profile-footnote';
    note.textContent = 'Este perfil no se cuenta como una mención.';
    card.append(note);
    card.classList.remove('hide');
  } catch (_) {
    // Directory availability must not prevent the ordinary news search.
  }
}

function newsSourceLink(item) {
  for (const value of [item.url, item.link]) {
    if (typeof value !== 'string' || !value.trim()) continue;
    try {
      // Never resolve missing/relative values against the application's URL.
      const url = new URL(value.trim());
      if (!['https:', 'http:'].includes(url.protocol) || url.username || url.password) continue;
      const link = document.createElement('a');
      link.href = url.href;
      link.target = '_blank';
      link.rel = 'noopener noreferrer external';
      link.dataset.newsSource = 'true';
      link.textContent = 'Abrir fuente →';
      const destination = window.RadarNative ? 'abre en Safari; ciérralo para regresar' : 'abre en otra pestaña';
      link.setAttribute('aria-label', `Abrir fuente: ${item.title || 'noticia'} (${destination})`);
      return link.outerHTML;
    } catch (_) {
      // Older reports may have only `link`; try that before disabling the link.
    }
  }
  return '<span class="note">Enlace de la fuente no disponible</span>';
}

function newsItem(item) {
  const date = new Date(item.published);
  const published = Number.isNaN(date.getTime()) ? '' : new Intl.DateTimeFormat('es-CO', {day:'numeric', month:'short', year:'numeric', timeZone:'UTC'}).format(date);
  return `<div class="item"><b>${esc(item.title)}</b><br><span>${esc(item.sentiment)}</span> · ${esc(item.source)}${published ? ` · ${esc(published)}` : ''}<br>${newsSourceLink(item)}</div>`;
}

function saveReport() {
  if (!currentReport || !currentQuery || $('reporttab').classList.contains('hide') || $('result').classList.contains('hide')) return;
  try {
    reportStorage.setItem(reportStorageKey, JSON.stringify({
      report: currentReport,
      query: currentQuery,
      form: currentForm,
      scrollY: window.scrollY
    }));
  } catch (_) {
    // Private browsing or a full storage quota must not prevent opening a source.
  }
}

function restoreReport() {
  // Every opening starts the next Radar search in Colombia, even after a saved
  // search elsewhere. Keep the original query attached to the recovered report.
  $('territory').value = 'Colombia';
  try {
    const saved = JSON.parse(reportStorage.getItem(reportStorageKey));
    if (!saved?.query || !saved.report?.mentions || !Array.isArray(saved.report.items)) return;
    currentReport = webOnlyReport(saved.report);
    currentQuery = saved.query;
    currentForm = saved.form || null;
    for (const field of ['name', 'aliases', 'days']) {
      if (currentQuery[field] !== undefined) $(field).value = currentQuery[field];
    }
    if (currentForm) {
      // Keep a usable news query while the directory is loading or unavailable.
      $('name').value = currentForm.congress_id ? currentQuery.name : currentForm.name;
      $('aliases').value = currentForm.aliases;
      if (currentForm.congress_id) window.RadarCongress?.restore(currentForm.congress_id);
    }
    const searchSequence = ++reportSearchSequence;
    const profileReady = showOfficialProfile(currentQuery, currentForm?.congress_id, searchSequence);
    renderReport(currentReport);
    const savedZone = typeof currentQuery.territory === 'string' ? currentQuery.territory.trim() : 'Colombia';
    $('report-restored').textContent = `Consulta recuperada · Zona consultada: ${savedZone || 'Sin filtro de zona'}. Genera otro reporte para actualizarla.`;
    $('report-restored').classList.remove('hide');
    profileReady.then(() => {
      if (searchSequence === reportSearchSequence) requestAnimationFrame(() => window.scrollTo(0, Number(saved.scrollY) || 0));
    });
  } catch (_) {
    // An unavailable or outdated saved report leaves the normal search form usable.
  }
}

async function go() {
  const name = $('name').value.trim();
  if (!name) return alert('Escribe un nombre');
  const search = window.RadarCongress?.query() || {name, aliases: $('aliases').value};
  const form = {name: $('name').value, aliases: $('aliases').value, congress_id: window.RadarCongress?.selectedId() || null};
  const query = {...search, territory: $('territory').value, days: +$('days').value, limit: 60};
  const searchSequence = ++reportSearchSequence;
  $('loading').classList.remove('hide');
  $('result').classList.add('hide');
  showOfficialProfile(query, form.congress_id, searchSequence);
  try {
    const response = await (window.RadarNative?.request || fetch)('/api/report', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(query)
    });
    const data = await response.json();
    if (searchSequence !== reportSearchSequence) return;
    if (!response.ok) throw new Error(data.error || 'Error');
    const reportData = webOnlyReport(data);
    renderReport(reportData);
    currentReport = reportData;
    currentQuery = query;
    currentForm = form;
    $('report-restored').classList.add('hide');
    saveReport();
  } catch (error) {
    if (searchSequence === reportSearchSequence) {
      if (window.RadarNative && currentReport) {
        renderReport(currentReport);
        const zone = currentQuery?.territory || 'Sin filtro de zona';
        $('report-restored').textContent = `No se pudo actualizar. Se muestra la consulta anterior · Zona consultada: ${zone}.`;
        $('report-restored').classList.remove('hide');
      }
      alert(error.message);
    }
  } finally {
    if (searchSequence === reportSearchSequence) $('loading').classList.add('hide');
  }
}

document.addEventListener('click', event => {
  if (event.target.closest?.('a[data-news-source]')) saveReport();
});
window.addEventListener('pagehide', saveReport);
document.addEventListener('visibilitychange', () => {
  if (document.visibilityState === 'hidden') saveReport();
});

function renderReport(d) {
  $('mweb').textContent = d.mentions.web;
  const coverage = $('report-coverage');
  if (coverage) coverage.textContent = d.web_coverage?.message || 'Publicaciones detectadas en medios web. La cobertura es parcial; pueden existir otras publicaciones.';
  $('rname').textContent = d.name;
  $('summary').textContent = d.summary;
  $('items').innerHTML = (d.items || []).map(newsItem).join('');
  $('result').classList.remove('hide');
}

const radarZone = $('territory');
const clearZoneButton = $('clear-territory');
clearZoneButton?.addEventListener('mousedown', event => event.preventDefault());
clearZoneButton?.addEventListener('click', () => {
  radarZone.value = '';
  radarZone.dispatchEvent(new Event('input', {bubbles: true}));
  radarZone.focus();
});

restoreReport();
