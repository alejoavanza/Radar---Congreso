const reportStorageKey = 'radar:report:v1';
let currentReport = null;
let currentQuery = null;

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
  if (!currentReport || !currentQuery || $('reporttab').classList.contains('hide')) return;
  try {
    sessionStorage.setItem(reportStorageKey, JSON.stringify({
      report: currentReport,
      query: currentQuery,
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
    for (const field of ['name', 'aliases', 'territory', 'days']) {
      if (currentQuery[field] !== undefined) $(field).value = currentQuery[field];
    }
    renderReport(currentReport);
    $('report-restored').classList.remove('hide');
    requestAnimationFrame(() => window.scrollTo(0, Number(saved.scrollY) || 0));
  } catch (_) {
    // An unavailable or outdated saved report leaves the normal search form usable.
  }
}

async function go() {
  const name = $('name').value.trim();
  if (!name) return alert('Escribe un nombre');
  const query = {name, aliases: $('aliases').value, territory: $('territory').value, days: +$('days').value, limit: 60};
  $('loading').classList.remove('hide');
  $('result').classList.add('hide');
  try {
    const response = await fetch('/api/report', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(query)
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Error');
    renderReport(data);
    currentReport = data;
    currentQuery = query;
    $('report-restored').classList.add('hide');
    saveReport();
  } catch (error) {
    if (currentReport) $('result').classList.remove('hide');
    alert(error.message);
  } finally {
    $('loading').classList.add('hide');
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
