import { authApi } from './auth.js';
const token = () => authApi.getSession()?.tokens?.access || '';
async function request(path, options = {}) {
  const response = await fetch(`/api/sales${path}`, { ...options, headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token()}`, ...(options.headers || {}) } });
  const data = await response.json().catch(() => null);
  if (!response.ok) throw new Error(data?.detail || Object.values(data || {})?.[0]?.[0] || 'عملیات فروش ناموفق بود');
  return data;
}
const list = (data) => data?.results ?? data ?? [];
export const salesApi = {
  customers: async () => list(await request('/customers/')),
  products: async () => list(await (async () => { const r = await fetch('/api/inventory/products/', { headers: { Authorization: `Bearer ${token()}` } }); const d = await r.json(); if (!r.ok) throw new Error(d.detail || 'دریافت کالا ناموفق بود'); return d; })()),
  invoices: async () => list(await request('/invoices/')),
  createInvoice: (payload) => request('/invoices/', { method: 'POST', body: JSON.stringify(payload) }),
  submit: (id) => request(`/invoices/${id}/submit/`, { method: 'POST', body: '{}' }),
};
