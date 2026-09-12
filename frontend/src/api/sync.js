import { authApi } from './auth.js';

const DB_NAME = 'abtin-offline';
const STORE = 'operations';
function openDb() {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, 1);
    request.onupgradeneeded = () => request.result.createObjectStore(STORE, { keyPath: 'client_id' });
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}
async function allLocal() {
  const db = await openDb();
  return new Promise((resolve, reject) => { const r = db.transaction(STORE).objectStore(STORE).getAll(); r.onsuccess = () => resolve(r.result); r.onerror = () => reject(r.error); });
}
export const syncApi = {
  async enqueue(operation) {
    const item = { client_id: crypto.randomUUID(), client_updated_at: new Date().toISOString(), ...operation };
    const db = await openDb();
    await new Promise((resolve, reject) => { const r = db.transaction(STORE, 'readwrite').objectStore(STORE).put(item); r.onsuccess = resolve; r.onerror = () => reject(r.error); });
    return item;
  },
  pending: allLocal,
  async push() {
    const items = await allLocal();
    if (!items.length) return { accepted: [], conflicts: [] };
    const session = authApi.getSession();
    const res = await fetch('/api/sync/operations/push/', { method: 'POST', headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${session?.tokens?.access || ''}` }, body: JSON.stringify({ operations: items }) });
    if (!res.ok) throw new Error('همگام‌سازی ناموفق بود');
    const result = await res.json();
    const db = await openDb();
    const tx = db.transaction(STORE, 'readwrite');
    result.accepted.forEach((item) => tx.objectStore(STORE).delete(item.client_id));
    return result;
  },
};
