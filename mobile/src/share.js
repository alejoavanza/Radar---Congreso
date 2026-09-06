import { sourceURL } from './transport.js';

export function reportText(saved) {
  if (!saved?.report || !saved?.query) return null;
  const {report, query} = saved;
  const lines = ['Radar Político · ' + report.name,
    `${query.days === 1 ? 'Últimas 24 horas' : query.days + ' días'} · Zona: ${query.territory || 'Sin filtro de zona'}`,
    report.summary || '', '', 'Fuentes:'];
  for (const item of (report.items || []).slice(0, 10)) {
    const url = sourceURL(item.url) || sourceURL(item.link);
    if (url) lines.push(`${item.title}\n${url}`);
  }
  lines.push('', 'Muestra de fuentes públicas; no es una encuesta ni un censo de todas las menciones.', 'Táctika Comunicaciones');
  return lines.join('\n');
}

export function comparisonText(saved) {
  const snapshot = saved?.snapshot;
  if (!snapshot?.meta || !Array.isArray(snapshot.rows)) return null;
  const {meta, rows} = snapshot;
  const lines = ['Radar Político · Comparativo de menciones en web',
    `Zona: ${meta.territory || 'Sin filtro de zona'}`,
    `Periodo: ${meta.start_time} — ${meta.end_time}`, ''];
  for (const row of rows) {
    const web = row.sources?.Web;
    const available = web?.status === 'available' && Number.isFinite(web.count) && web.count >= 0;
    lines.push(`${row.member?.search_name || row.member?.display_name}: ${available ? web.count + (web.limited ? '+' : '') : 'N/D'}`);
    const url = sourceURL(web?.url);
    if (url) lines.push(url);
  }
  lines.push('', 'Menciones detectadas, no alcance ni personas únicas. N/D = no disponible. + = cobertura limitada.', 'Táctika Comunicaciones');
  return lines.join('\n');
}
