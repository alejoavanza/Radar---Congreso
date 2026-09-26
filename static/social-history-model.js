(function (root) {
  'use strict';
  const platforms = ['instagram', 'facebook', 'tiktok', 'youtube', 'x'];
  const metrics = ['followers', 'views', 'interactions', 'posts', 'impressions', 'reach'];
  const columns = ['member_id', 'platform', 'account', 'date', ...metrics, 'source'];
  const day = 86400000;
  function bogotaToday() {
    const parts = new Intl.DateTimeFormat('en-US', {timeZone: 'America/Bogota', year: 'numeric', month: '2-digit', day: '2-digit'}).formatToParts(new Date());
    const p = Object.fromEntries(parts.map(part => [part.type, part.value]));
    return `${p.year}-${p.month}-${p.day}`;
  }
  function windowStart(end, period) {
    const date = new Date(`${end}T00:00:00Z`);
    if (period === '1d') date.setUTCDate(date.getUTCDate());
    else if (period === '7d') date.setUTCDate(date.getUTCDate() - 6);
    else if (period === '60d') date.setUTCDate(date.getUTCDate() - 59);
    else {
      const months = {'1m': 1, '3m': 3, '6m': 6, '12m': 12}[period];
      if (!months) throw new Error('Periodo inválido');
      const originalDay = date.getUTCDate();
      date.setUTCDate(1);
      date.setUTCMonth(date.getUTCMonth() - months);
      const lastDay = new Date(Date.UTC(date.getUTCFullYear(), date.getUTCMonth() + 1, 0)).getUTCDate();
      date.setUTCDate(Math.min(originalDay, lastDay));
    }
    return date.toISOString().slice(0, 10);
  }
  function summary(points, metric) {
    const first = points[0], last = points.at(-1);
    const growth = metric === 'followers' && points.length >= 2 ? last.value - first.value : null;
    return {count: points.length, first, last, growth,
      percent: growth !== null && first.value > 0 ? growth / first.value * 100 : null};
  }
  function calculate(records, memberId, period, metric, selected = platforms, end = bogotaToday()) {
    if (!metrics.includes(metric)) throw new Error('Métrica inválida');
    const start = windowStart(end, period);
    const within = records.filter(row => row.member_id === memberId && row.date >= start && row.date <= end)
      .sort((a, b) => a.date.localeCompare(b.date));
    const series = Object.fromEntries(platforms.map(platform => {
      const points = within.filter(row => row.platform === platform && row[metric] !== null)
        .map(row => ({date: row.date, value: row[metric], source: row.source, account: row.account}));
      return [platform, {points, ...summary(points, metric)}];
    }));
    const dates = [...new Set(within.map(row => row.date))].sort();
    const chosen = [...new Set(selected.filter(platform => platforms.includes(platform)))];
    const indexed = Object.fromEntries(chosen.map(platform => [platform, new Map(series[platform].points.map(point => [point.date, point]))]));
    // Never fill gaps or change the cohort during a total's time series.
    const points = metric === 'reach' || !chosen.length ? [] : dates.flatMap(date => {
      const values = chosen.map(platform => indexed[platform].get(date));
      return values.every(Boolean) ? [{date, value: values.reduce((sum, point) => sum + point.value, 0)}] : [];
    });
    return {start, end, series, selected: chosen, total: {points, ...summary(points, metric)}, rows: within,
      expectedDays: Math.round((Date.parse(end) - Date.parse(start)) / day) + 1};
  }
  function csv(records) {
    const escape = value => '"' + String(value ?? '').replace(/"/g, '""') + '"';
    return [columns.join(','), ...records.map(row => columns.map(key => escape(row[key])).join(','))].join('\r\n') + '\r\n';
  }
  const api = {platforms, metrics, columns, bogotaToday, windowStart, calculate, csv};
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  root.RadarSocialModel = api;
})(typeof window === 'undefined' ? globalThis : window);
