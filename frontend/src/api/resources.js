import { authApi } from './auth.js';

function authHeaders() {
  const session = authApi.getSession();
  return { Authorization: `Bearer ${session?.tokens?.access || ''}` };
}

export async function fetchResource(path) {
  const response = await fetch(`/api${path}`, { headers: authHeaders() });
  const data = await response.json().catch(() => null);
  if (!response.ok) throw new Error(data?.detail || 'دریافت اطلاعات ناموفق بود');
  return data?.results ?? data ?? [];
}

export async function createResource(path, payload) {
  const response = await fetch(`/api${path}`, { method: 'POST', headers: { 'Content-Type': 'application/json', ...authHeaders() }, body: JSON.stringify(payload) });
  const data = await response.json().catch(() => null);
  if (!response.ok) throw new Error(data?.detail || Object.values(data || {})?.[0]?.[0] || 'ثبت اطلاعات ناموفق بود');
  return data;
}

export function flattenRow(row) {
  return Object.fromEntries(Object.entries(row).filter(([key, value]) => !['id', 'url'].includes(key) && (typeof value !== 'object' || value === null)).slice(0, 7));
}
