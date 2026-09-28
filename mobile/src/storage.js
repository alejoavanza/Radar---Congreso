import { STATE_KEY, STATE_KEYS } from './config.js';

// A bounded snapshot, not a history database. Synchronous reads let the shared
// interface restore itself before its scripts run; writes are ordered on both platforms.
export async function createStorage(preferences, onFailure = () => {}) {
  let values = Object.create(null), queue = Promise.resolve(), clearing = false;
  try {
    const {value} = await preferences.get({key: STATE_KEY});
    const saved = JSON.parse(value || '{}');
    for (const key of STATE_KEYS) if (typeof saved?.[key] === 'string') values[key] = saved[key];
  } catch { onFailure('No se pudo recuperar la consulta guardada. Puedes hacer una nueva búsqueda.'); }
  function write() {
    const value = JSON.stringify(values);
    if (value.length > 3 * 1024 * 1024) {
      onFailure('La consulta es demasiado grande para guardarla en este dispositivo.');
      return;
    }
    queue = queue.then(() => preferences.set({key: STATE_KEY, value})).catch(() => {
      onFailure('No se pudo guardar la última consulta en este dispositivo.');
    });
  }
  return {
    getItem: key => values[key] ?? null,
    setItem(key, value) {
      if (clearing || !STATE_KEYS.includes(key)) return;
      // A large search cache must not prevent future report/tab snapshots.
      const candidate = {...values, [key]: String(value)};
      if (JSON.stringify(candidate).length > 3 * 1024 * 1024) {
        delete candidate['radar:evidence:v1'];
        if (JSON.stringify(candidate).length > 3 * 1024 * 1024) {
          onFailure('La consulta es demasiado grande para guardarla en este dispositivo.');
          return;
        }
        values = candidate; write(); return;
      }
      values[key] = String(value); write();
    },
    removeItem(key) {
      if (clearing || !STATE_KEYS.includes(key)) return;
      delete values[key]; write();
    },
    flush: () => queue,
    async clearSaved() {
      clearing = true;
      await queue;
      try {
        await preferences.remove({key: STATE_KEY});
        values = Object.create(null);
      } catch (error) {
        clearing = false;
        throw error;
      }
      // Ignore pagehide/background writes from the old report until reload.
    }
  };
}
