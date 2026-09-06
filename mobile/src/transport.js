import { API_ORIGIN, API_PATHS } from './config.js';

export function sourceURL(value) {
  try {
    const url = new URL(value);
    return ['https:', 'http:'].includes(url.protocol) && !url.username && !url.password ? url.href : null;
  } catch { return null; }
}

// Native HTTP is used only for the three existing JSON endpoints. Bundled
// assets still use WKWebView's local loader; arbitrary URLs never reach this bridge.
export function createRequest(http, connected = () => true) {
  return async function request(path, options = {}) {
    if (!API_PATHS.has(path) || options.method !== 'POST') throw new Error('Consulta no permitida.');
    if (!connected()) throw new Error('Sin conexión. Revisa tu conexión e intenta de nuevo.');
    if (options.signal?.aborted) throw new DOMException('Consulta cancelada.', 'AbortError');
    const data = JSON.parse(options.body || '{}');
    let timer, onAbort;
    const stopped = new Promise((_, reject) => {
      onAbort = () => reject(new DOMException('Consulta cancelada.', 'AbortError'));
      options.signal?.addEventListener('abort', onAbort, {once: true});
      timer = setTimeout(() => reject(new Error('La consulta tardó demasiado. Intenta de nuevo.')), 90000);
    });
    try {
      // Native requests already sent cannot be cancelled by AbortController.
      // Race the response so a timed-out/older request never replaces current UI.
      const response = await Promise.race([http.request({
        url: API_ORIGIN + path,
        method: 'POST',
        headers: {'Content-Type': 'application/json', 'Accept': 'application/json'},
        // iOS uses connectTimeout as the entire request timeout when supplied.
        // Keep the report window long enough for the existing source queries.
        data, responseType: 'json', readTimeout: 85000,
        disableRedirects: true
      }), stopped]);
      if (!response || !Number.isInteger(response.status)) throw new Error('El servidor no devolvió una respuesta válida.');
      if (response.status >= 300 && response.status < 400) throw new Error('El servidor cambió de dirección. Intenta más tarde.');
      let payload = response.data;
      if (typeof payload === 'string') {
        try { payload = JSON.parse(payload); } catch { throw new Error('El servidor no devolvió un reporte válido.'); }
      }
      if (!payload || typeof payload !== 'object' || Array.isArray(payload)) throw new Error('El servidor no devolvió un reporte válido.');
      return {ok: response.status >= 200 && response.status < 300, status: response.status, json: async () => payload};
    } catch (error) {
      if (error instanceof Error) throw error;
      throw new Error('No se pudo conectar con Radar. Intenta de nuevo.');
    } finally {
      clearTimeout(timer);
      options.signal?.removeEventListener('abort', onAbort);
    }
  };
}
