const reportStorageKey = 'radar:report:v1';
let currentReport = null;
let currentQuery = null;
let currentForm = null;
let reportSearchSequence = 0;

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
      link.setAttribute('aria-label', `Abrir fuente: ${item.title || 'noticia'} (abre en otra pestaña)`);
      return link.outerHTML;
    } catch (_) {
      // Older reports may have only `link`; try that before disabling the link.
    }
  }
  return '<span class="note">Enlace de la fuente no disponible</span>';
}

function newsItem(item) {
  return `<div class="item"><b>${esc(item.title)}</b><br><span>${esc(item.sentiment)}</span> · ${esc(item.source)}<br>${newsSourceLink(item)}</div>`;
}

function saveReport() {
  if (!currentReport || !currentQuery || $('reporttab').classList.contains('hide') || $('result').classList.contains('hide')) return;
  try {
    sessionStorage.setItem(reportStorageKey, JSON.stringify({
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
  try {
    const saved = JSON.parse(sessionStorage.getItem(reportStorageKey));
    if (!saved?.query || !saved.report?.mentions || !Array.isArray(saved.report.items)) return;
    currentReport = saved.report;
    currentQuery = saved.query;
    currentForm = saved.form || null;
    for (const field of ['name', 'aliases', 'territory', 'days']) {
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
    const response = await fetch('/api/report', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(query)
    });
    const data = await response.json();
    if (searchSequence !== reportSearchSequence) return;
    if (!response.ok) throw new Error(data.error || 'Error');
    renderReport(data);
    currentReport = data;
    currentQuery = query;
    currentForm = form;
    $('report-restored').classList.add('hide');
    saveReport();
  } catch (error) {
    if (searchSequence === reportSearchSequence) alert(error.message);
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
  $('mweb').textContent=d.mentions.web;$('msocial').textContent=d.mentions.social;$('mcombined').textContent=d.mentions.combined;$('xstatus').textContent=d.mentions.diagnostics?.X?.label||'';const x=d.mentions.x_intelligence;if(x){$('xintel').classList.remove('hide');$('xtotal').textContent=x.total;$('xbalance').textContent=x.balance;$('xeng').textContent=fmt(x.engagement);$('xavg').textContent=fmt(x.avg_engagement);$('xaccounts').innerHTML=(x.top_accounts||[]).map(accountRow).join('');$('xposts').innerHTML=(x.top_posts||[]).map(postRow).join('');$('xauthors').innerHTML=(x.top_authors||[]).map(a=>`<div class="author"><div class="name">${a.profile_url?`<a href="${a.profile_url}" target="_blank">${esc(a.name)} ${a.username?'@'+esc(a.username):''}</a>`:esc(a.name)}${vb(a)}</div><div class="stats">${a.count} apariciones · ${fmt(a.followers)} seguidores · ${fmt(a.engagement)} interacciones</div>${(a.top_posts||[]).map((p,j)=>`<div class="author-post"><span class="stats">#${j+1} · ${fmt(p.engagement)} interacciones</span><div>${esc(p.text)}</div>${p.post_url?`<a href="${p.post_url}" target="_blank">Abrir publicación →</a>`:''}</div>`).join('')}</div>`).join('');$('xtopics').innerHTML=(x.topics||[]).map(t=>`<span class="topic">${esc(t.term)} · ${t.count}</span>`).join('');$('xdaily').innerHTML=(x.daily||[]).map(v=>`${esc(v.date)} · ${v.count} menciones · ${fmt(v.engagement)} interacciones`).join('<br>')}else $('xintel').classList.add('hide');$('rname').textContent=d.name;$('summary').textContent=d.summary;$('items').innerHTML=(d.items||[]).map(newsItem).join('');$('result').classList.remove('hide')
}

restoreReport();
