import { Capacitor, CapacitorHttp } from '@capacitor/core';
import { App } from '@capacitor/app';
import { Browser } from '@capacitor/browser';
import { Network } from '@capacitor/network';
import { Preferences } from '@capacitor/preferences';
import { Share } from '@capacitor/share';
import { createRequest, sourceURL } from './transport.js';
import { createStorage } from './storage.js';
import { reportText, comparisonText } from './share.js';

const $ = id => document.getElementById(id);
function notice(message) {
  const node = $('native-message');
  if (node) { node.textContent = message; node.hidden = !message; }
}
function button(label, id, parent, action) {
  const node = document.createElement('button');
  node.type = 'button'; node.id = id; node.className = 'secondary native-action';
  node.textContent = label;
  node.addEventListener('click', async () => {
    node.disabled = true;
    try { await action(); } finally { node.disabled = false; }
  });
  parent.append(node);
}

async function start() {
  if (!Capacitor.isNativePlatform()) throw new Error('Abre este proyecto desde la aplicación de iPhone.');
  let connected = true;
  const storage = await createStorage(Preferences, notice);
  window.RadarNative = {storage, request: createRequest(CapacitorHttp, () => connected)};
  function connection(status) {
    connected = status.connected;
    const banner = $('native-offline');
    banner.hidden = connected;
  }
  try {
    await Network.addListener('networkStatusChange', connection);
    connection(await Network.getStatus());
  } catch { /* The HTTP call still reports connection failures. */ }

  await new Promise((resolve, reject) => {
    const script = document.createElement('script');
    script.src = '/app.js'; script.onload = resolve;
    script.onerror = () => reject(new Error('No se pudo abrir Radar. Cierra y vuelve a abrir la aplicación.'));
    document.body.append(script);
  });

  async function share(key, format) {
    let text;
    try { text = format(JSON.parse(storage.getItem(key))); } catch { /* Invalid cached state. */ }
    if (!text) { notice('Genera una consulta antes de compartirla.'); return; }
    try { await Share.share({title: 'Radar Político', text, dialogTitle: 'Compartir resultado'}); }
    catch (error) {
      // Cancelling the system sheet is an ordinary user action.
      if (!/cancel|dismiss/i.test(String(error?.message || error))) notice('No se pudo compartir el resultado. Intenta de nuevo.');
    }
  }
  button('Compartir reporte', 'native-share-report', $('result'), () => share('radar:report:v1', reportText));
  button('Compartir comparativo', 'native-share-comparison', $('compare-results'), () => share('radar:comparison:v1', comparisonText));
  button('Borrar consultas guardadas', 'native-clear-saved', $('native-settings'), async () => {
    if (!window.confirm('¿Borrar el reporte y el comparativo guardados en este iPhone?')) return;
    try { await storage.clearSaved(); window.location.reload(); }
    catch { notice('No se pudieron borrar las consultas. Intenta de nuevo.'); }
  });

  document.addEventListener('click', event => {
    const anchor = event.target.closest?.('a[href]');
    if (!anchor) return;
    const url = sourceURL(anchor.href);
    if (!url) return; // Local capacitor:// pages retain their own return link.
    event.preventDefault();
    window.saveReport?.();
    Browser.open({url, presentationStyle: 'fullscreen', toolbarColor: '#075056'}).catch(() => {
      notice('No se pudo abrir el enlace. Tu consulta sigue disponible; intenta de nuevo.');
    });
  }, true);
  try {
    await App.addListener('appStateChange', ({isActive}) => {
      if (!isActive) { window.saveReport?.(); void storage.flush(); }
      else void Network.getStatus().then(connection).catch(() => {});
    });
  } catch { /* Reports are also saved as soon as they finish. */ }
  $('native-starting').hidden = true;
}

start().catch(error => {
  $('native-starting').textContent = error.message || 'No se pudo abrir Radar. Intenta de nuevo.';
  document.getElementById('splash')?.remove();
});
