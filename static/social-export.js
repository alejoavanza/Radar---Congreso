(function (root) {
  'use strict';
  const labels = {instagram: 'Instagram', facebook: 'Facebook', tiktok: 'TikTok', youtube: 'YouTube', x: 'X', total: 'Total seleccionado'};
  const palette = {instagram: '#c23b79', facebook: '#2674bd', tiktok: '#279768', youtube: '#d35827', x: '#7b5bc6', total: '#087e83'};
  const metrics = {followers: 'Seguidores / suscriptores', views: 'Visualizaciones diarias', interactions: 'Interacciones diarias', posts: 'Publicaciones diarias', impressions: 'Impresiones diarias', reach: 'Alcance diario por red'};
  const formats = {portrait: [1080, 1350], landscape: [1600, 900], story: [1080, 1920]};
  const num = value => new Intl.NumberFormat('es-CO', {maximumFractionDigits: 1}).format(value);
  const date = value => new Date(`${value}T12:00:00Z`).toLocaleDateString('es-CO', {day: 'numeric', month: 'short', year: '2-digit', timeZone: 'America/Bogota'});
  function prepare(current, member, metric, view, scale) {
    if (!member || !current || !metrics[metric]) throw new Error('Selecciona un congresista y una métrica.');
    let keys = view === 'comparison' ? current.selected : view === 'total' ? ['total'] : [view];
    if (!keys.length || keys.some(key => !labels[key])) throw new Error('Selecciona las redes que quieres comparar.');
    if (view === 'total' && metric === 'reach') throw new Error('El alcance se presenta por red, nunca como total.');
    const series = keys.map(key => ({key, label: labels[key], color: palette[key], ...(key === 'total' ? current.total : current.series[key])}));
    if (!series.some(item => item.points.length)) throw new Error('No hay datos para esta pieza. Importa registros o cambia el periodo y las redes.');
    let baseline = null;
    const indexed = scale === 'index' && view === 'comparison';
    if (indexed) {
      if (metric !== 'followers') throw new Error('La comparación base 100 está disponible para seguidores.');
      const maps = series.map(item => new Map(item.points.map(point => [point.date, point.value])));
      baseline = series[0].points.find(point => maps.every(map => map.has(point.date) && map.get(point.date) > 0))?.date;
      if (!baseline) throw new Error('Base 100 requiere una fecha común con seguidores mayores que cero en todas las redes seleccionadas. Usa cifras reales o ajusta las redes.');
    }
    const plotted = series.map(item => {
      const raw = item.points.filter(point => !baseline || point.date >= baseline);
      const first = raw[0], last = raw.at(-1);
      const percent = metric === 'followers' && raw.length > 1 && first.value > 0 ? (last.value / first.value - 1) * 100 : null;
      return {...item, raw, first, last, percent, points: raw.map(point => ({...point, value: indexed ? point.value / first.value * 100 : point.value}))};
    });
    const included = view === 'comparison' || view === 'total' ? current.selected : [view];
    const sources = [...new Set(current.rows.filter(row => included.includes(row.platform) && row[metric] !== null && (!baseline || row.date >= baseline)).map(row => row.source))];
    return {name: member.full_name, memberId: member.id, metric, view, indexed, baseline, series: plotted,
      start: current.start, end: current.end, included, sources,
      title: indexed ? 'El ritmo de crecimiento' : view === 'total' ? (metric === 'followers' ? 'Evolución de la audiencia' : `${metrics[metric]} · total`) : view === 'comparison' ? 'Tu evolución, red por red' : `Tu evolución en ${labels[view]}`,
      unit: indexed ? 'Índice de seguidores · base común = 100' : metrics[metric]};
  }
  function caption(report) {
    const lines = [`${report.name} · ${report.unit}`, `Periodo: ${date(report.start)} a ${date(report.end)}.`];
    if (report.baseline) lines.push(`Base 100: ${date(report.baseline)} para todas las redes.`);
    for (const item of report.series) lines.push(item.last ? `${item.label}: ${num(item.last.value)} al ${date(item.last.date)}${item.percent === null ? '' : `; ${item.percent >= 0 ? '+' : ''}${num(item.percent)} % entre ${date(item.first.date)} y ${date(item.last.date)}`}.` : `${item.label}: N/D.`);
    lines.push('Registros importados por el usuario; origen no verificado. Las líneas unen observaciones, no reconstruyen datos ausentes.');
    if (report.view === 'total') lines.push(`Redes incluidas: ${report.included.map(key => labels[key]).join(', ')}. Las cifras no representan personas únicas.`);
    if (report.metric !== 'followers') lines.push('Las definiciones de esta métrica pueden variar entre redes.');
    lines.push('Fuentes: ' + [...new Set(report.sources.map(source => new URL(source).hostname))].slice(0, 5).join(', ') + '.', 'Generado con Radar Político · Táctika Comunicaciones.');
    return lines.join('\n');
  }
  function exampleReport(formatView = 'comparison', scale = 'absolute') {
    const model = root.RadarSocialModel;
    const end = model.bogotaToday(), start = model.windowStart(end, '12m');
    const middle = model.windowStart(end, '6m');
    const records = model.platforms.flatMap((platform, i) => [start, middle, end].map((date, cut) => ({
      member_id: 'ejemplo', platform, account: 'ejemplo', date,
      followers: Math.round((i + 1) * 10000 * (1 + cut * [0.7, 0.25, 0.4, 0.2, 0.05][i])),
      source: 'https://example.org/datos-simulados'
    })));
    const current = model.calculate(records, 'ejemplo', '12m', 'followers', model.platforms, end);
    const report = prepare(current, {id: 'ejemplo', full_name: 'Ejemplo · datos simulados'}, 'followers', formatView, scale);
    report.demo = true;
    return report;
  }
  function paint(canvas, report, format = 'portrait', theme = 'light') {
    const [width, height] = formats[format] || formats.portrait;
    canvas.width = width; canvas.height = height;
    const ctx = canvas.getContext('2d');
    if (!ctx) throw new Error('Este navegador no permite generar la imagen.');
    const wide = width > height, dark = theme === 'dark';
    const c = dark ? {bg:'#131e2b',ink:'#f4f7fa',muted:'#b8c6d5',line:'#344251',soft:'#1c2a3a'} : {bg:'#ffffff',ink:'#122f33',muted:'#52666b',line:'#d9e4e6',soft:'#f0f5f4'};
    ctx.fillStyle = c.bg; ctx.fillRect(0, 0, width, height);
    const pad = 64, usable = width - 2 * pad;
    function text(value, x, y, size = 24, color = c.ink, weight = 400, maxWidth) {
      ctx.font = `${weight} ${size}px Arial, sans-serif`; ctx.fillStyle = color;
      ctx.fillText(value, x, y, maxWidth);
    }
    function wrap(value, x, y, maxWidth, size, lineHeight, maxLines = 3, color = c.muted, weight = 400) {
      ctx.font = `${weight} ${size}px Arial, sans-serif`;
      const words = value.split(/\s+/), lines = []; let line = '';
      for (const word of words) {
        if (ctx.measureText(line + (line ? ' ' : '') + word).width > maxWidth && line) { lines.push(line); line = word; } else line += (line ? ' ' : '') + word;
      }
      if (line) lines.push(line);
      lines.slice(0, maxLines).forEach((value, i) => {
        let rendered = value;
        if (i === maxLines - 1 && lines.length > maxLines) rendered += '…';
        text(rendered, x, y + i * lineHeight, size, color, weight, maxWidth);
      });
      return y + Math.min(lines.length, maxLines) * lineHeight;
    }
    ctx.fillStyle = '#ff5d00'; ctx.fillRect(pad, 46, 52, 6);
    text('RADAR POLÍTICO / PLUS', pad + 70, 56, 21, c.muted, 700);
    text('TÁCTIKA COMUNICACIONES', width - pad - 300, 56, 18, c.muted, 400, 300);
    wrap(report.name.toLocaleUpperCase('es'), pad, 112, usable, wide ? 30 : 32, 38, 2, c.ink, 700);
    text(report.title, pad, wide ? 190 : 218, wide ? 46 : 44, c.ink, 700, usable);
    text(`${date(report.start)} — ${date(report.end)}`, pad, wide ? 232 : 263, 24, c.muted);
    text(report.unit, pad, wide ? 270 : 301, 23, c.muted);
    const chart = {left: pad + 75, right: width - pad - 25, top: wide ? 337 : 395, bottom: wide ? 540 : format === 'story' ? 1090 : 730};
    const all = report.series.flatMap(item => item.points);
    const maximum = Math.max(1, ...all.map(point => point.value)) * 1.12;
    const plotX = d => chart.left + (Date.parse(d) - Date.parse(report.start)) / Math.max(86400000, Date.parse(report.end) - Date.parse(report.start)) * (chart.right - chart.left);
    const plotY = v => chart.bottom - v / maximum * (chart.bottom - chart.top);
    const compact = n => new Intl.NumberFormat('es-CO', {notation:'compact',maximumFractionDigits:1}).format(n);
    for (let i = 0; i <= 4; i++) {
      const v = maximum * i / 4, y = plotY(v);
      ctx.strokeStyle = c.line; ctx.lineWidth = 1; ctx.beginPath(); ctx.moveTo(chart.left, y); ctx.lineTo(chart.right, y); ctx.stroke();
      text(compact(v), pad, y + 7, 20, c.muted, 400, 68);
    }
    const endWidth = ctx.measureText(date(report.end)).width;
    text(date(report.start), chart.left, chart.bottom + 36, 21, c.muted);
    text(date(report.end), chart.right - Math.max(endWidth, 145), chart.bottom + 36, 21, c.muted);
    report.series.forEach((item, index) => {
      const lx = pad + index * usable / report.series.length;
      ctx.fillStyle = item.color; ctx.fillRect(lx, chart.top - 48, 22, 6);
      text(item.label, lx + 30, chart.top - 36, 21, c.ink, 700, usable / report.series.length - 34);
      ctx.strokeStyle = item.color; ctx.lineWidth = wide ? 3 : 4; ctx.setLineDash([9, 6]); ctx.beginPath();
      item.points.forEach((point, i) => { const x = plotX(point.date), y = plotY(point.value); if (i) ctx.lineTo(x, y); else ctx.moveTo(x, y); });
      ctx.stroke(); ctx.setLineDash([]);
      item.points.forEach(point => { ctx.fillStyle = item.color; ctx.beginPath(); ctx.arc(plotX(point.date), plotY(point.value), item.points.length > 60 ? 2.5 : 6, 0, Math.PI * 2); ctx.fill(); });
    });
    const statsY = chart.bottom + 88;
    if (wide) {
      const column = usable / report.series.length;
      report.series.forEach((item, i) => {
        const x = pad + i * column;
        ctx.fillStyle = item.color; ctx.fillRect(x, statsY - 20, column - 20, 4);
        text(item.label, x, statsY + 15, 23, c.ink, 700, column - 24);
        text(item.last ? num(item.last.value) : 'N/D', x, statsY + 52, 30, c.ink, 700, column - 24);
        text(item.percent === null ? 'Cambio: N/D' : `${item.percent >= 0 ? '+' : ''}${num(item.percent)} %`, x, statsY + 82, 22, item.color, 700, column - 24);
        text(item.last ? `${date(item.first.date)} → ${date(item.last.date)}` : 'Sin registros', x, statsY + 108, 17, c.muted, 400, column - 24);
        text(`${item.points.length} observaciones`, x, statsY + 131, 17, c.muted);
      });
    } else {
      report.series.forEach((item, i) => {
        const y = statsY + i * (format === 'story' ? 91 : 59);
        ctx.strokeStyle = c.line; ctx.beginPath(); ctx.moveTo(pad, y + 22); ctx.lineTo(width - pad, y + 22); ctx.stroke();
        text(item.label, pad, y, 25, item.color, 700, 205);
        text(item.last ? num(item.last.value) : 'N/D', pad + 225, y, 28, c.ink, 700, 225);
        text(item.percent === null ? 'Cambio: N/D' : `${item.percent >= 0 ? '+' : ''}${num(item.percent)} %`, pad + 470, y, 25, item.color, 700, 200);
        text(`${item.points.length} cortes`, width - pad - 180, y, 21, c.muted, 400, 180);
        text(item.last ? `${date(item.first.date)} → ${date(item.last.date)}` : 'Sin registros', pad + 225, y + 20, 15, c.muted);
      });
    }
    const footerY = height - (wide ? 91 : 211);
    const baseNote = report.baseline ? `Base común: ${date(report.baseline)} = 100. Abajo: seguidores en valores absolutos.` : report.view === 'total' ? `Total: ${report.included.map(key => labels[key]).join(', ')}. No son personas únicas.` : metrics[report.metric] + '. Sin datos no equivale a cero.';
    wrap(baseNote, pad, footerY, usable, wide ? 17 : 20, 25, 2);
    const noteY = footerY + (wide ? 27 : 52);
    wrap('Líneas entre observaciones; no hay mediciones en los huecos. Datos importados; origen no verificado.', pad, noteY, usable, wide ? 17 : 20, 25, 2);
    const domains = [...new Set(report.sources.map(source => new URL(source).hostname))];
    wrap(report.demo ? 'DEMOSTRACIÓN: cifras ficticias para mostrar el diseño. No corresponden a ninguna persona.' : 'Fuentes: ' + domains.slice(0, 5).join(' · ') + (domains.length > 5 ? ' · y otras' : '') + '. Detalle en CSV.', pad, noteY + (wide ? 26 : 57), usable, wide ? 16 : 18, 23, 2);
    if (!wide) text('AUDIENCIA DIGITAL · NO MIDE VOTOS NI IMPACTO LEGISLATIVO', pad, height - 32, 16, c.muted, 700, usable);
    return canvas;
  }
  const api = {prepare, caption, paint, formats, exampleReport};
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  root.RadarSocialExport = api;
  if (!root.document) return;
  const $ = id => document.getElementById(id);
  let snapshot = null, ready = null, previewUrl = null, revision = 0;
  const dialog = $('social-piece-dialog');
  function invalidate() {
    revision++; ready = null;
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    previewUrl = null; $('social-piece-image').removeAttribute('src');
    $('social-piece-caption').hidden = true; $('social-piece-caption').value = '';
    $('social-piece-download').disabled = true; $('social-piece-share').disabled = true; $('social-piece-copy').disabled = true;
    if (snapshot) $('social-piece-generate').disabled = snapshot.busy || !snapshot.member || !snapshot.current.rows.length;
    if (dialog.open) dialog.close();
  }
  api.update = value => {
    snapshot = value; invalidate();
    $('social-piece-generate').disabled = value.busy || !value.member || !value.current.rows.length;
    const indexOption = $('social-piece-scale').querySelector('option[value="index"]');
    indexOption.disabled = value.metric !== 'followers';
    if (indexOption.disabled) $('social-piece-scale').value = 'absolute';
    $('social-piece-status').textContent = value.current.rows.length ? 'La imagen incluirá las fechas y el origen de las cifras.' : 'Importa registros para generar una pieza con datos.';
  };
  for (const id of ['social-piece-view','social-piece-scale','social-piece-format','social-piece-theme']) $(id).addEventListener('change', () => {
    invalidate(); $('social-piece-scale').disabled = $('social-piece-view').value !== 'comparison';
  });
  async function generate(example = false) {
    if (!snapshot && !example) return;
    const token = ++revision;
    $('social-piece-generate').disabled = true; $('social-piece-status').textContent = 'Preparando la imagen…';
    try {
      const report = example ? exampleReport($('social-piece-view').value, $('social-piece-scale').value) : prepare(snapshot.current, snapshot.member, snapshot.metric, $('social-piece-view').value, $('social-piece-scale').value);
      const format = $('social-piece-format').value;
      const canvas = paint(document.createElement('canvas'), report, format, $('social-piece-theme').value);
      const blob = await new Promise((resolve, reject) => canvas.toBlob(value => value ? resolve(value) : reject(new Error('No se pudo generar el PNG.')), 'image/png'));
      if (token !== revision) return;
      const filename = `radar-${report.memberId}-${report.view}-${report.metric}-${format}-${report.end}.png`;
      ready = {file: new File([blob], filename, {type:'image/png'}), text:(example ? 'DEMOSTRACIÓN: cifras ficticias; no corresponden a ninguna persona.\n' : '') + caption(report)};
      if (previewUrl) URL.revokeObjectURL(previewUrl);
      previewUrl = URL.createObjectURL(blob); $('social-piece-image').src = previewUrl;
      $('social-piece-image').alt = ready.text;
      $('social-piece-download').href = previewUrl; $('social-piece-download').download = filename; $('social-piece-download').disabled = false;
      $('social-piece-copy').disabled = false;
      let shareable = false;
      try { shareable = !!navigator.share && !!navigator.canShare?.({files:[ready.file]}); } catch (_) { /* Download remains available. */ }
      $('social-piece-share').disabled = !shareable;
      $('social-piece-share-note').textContent = shareable ? 'Compartir abre las aplicaciones disponibles en tu dispositivo; tú eliges el destino y confirmas el envío.' : 'Este navegador no permite compartir archivos directamente. Descarga el PNG y adjúntalo en tu red o mensajería.';
      $('social-piece-status').textContent = `${example ? 'Ejemplo con cifras simuladas' : 'Imagen lista'} · ${canvas.width} × ${canvas.height} px`;
      $('social-piece-feedback').textContent = '';
      dialog.showModal();
    } catch (error) { $('social-piece-status').textContent = error.message; }
    finally { if (token === revision) $('social-piece-generate').disabled = !snapshot?.current.rows.length || snapshot?.busy; }
  }
  $('social-piece-generate').addEventListener('click', () => generate());
  $('social-piece-example').addEventListener('click', () => generate(true));
  $('social-piece-close').addEventListener('click', () => dialog.close());
  $('social-piece-download').addEventListener('click', () => { if (ready) $('social-piece-feedback').textContent = 'Descarga solicitada. Puedes adjuntar el PNG en tus redes.'; });
  $('social-piece-share').addEventListener('click', () => {
    if (!ready) return;
    // File is prepared before this click to preserve iOS transient user activation.
    navigator.share({files:[ready.file], title:'Radar Político · evolución digital', text:ready.text}).then(() => {
      $('social-piece-feedback').textContent = 'Imagen entregada al menú de compartir. Radar no verifica su publicación.';
    }).catch(error => { $('social-piece-feedback').textContent = error.name === 'AbortError' ? 'Envío cancelado; la imagen sigue disponible.' : 'No se pudo compartir. Descarga la imagen y adjúntala manualmente.'; });
  });
  $('social-piece-copy').addEventListener('click', async () => {
    if (!ready) return;
    try { await navigator.clipboard.writeText(ready.text); $('social-piece-feedback').textContent = 'Texto copiado.'; }
    catch (_) { $('social-piece-caption').value = ready.text; $('social-piece-caption').hidden = false; $('social-piece-caption').focus(); $('social-piece-caption').select(); $('social-piece-feedback').textContent = 'Selecciona y copia el texto de abajo.'; }
  });
})(typeof window === 'undefined' ? globalThis : window);
