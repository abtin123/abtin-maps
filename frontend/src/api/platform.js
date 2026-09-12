import { authApi } from './auth.js';
async function get(path) {
  const session = authApi.getSession();
  const res = await fetch(`/api${path}`, { headers: { Authorization: `Bearer ${session?.tokens?.access || ''}` } });
  const data = await res.json().catch(() => null);
  if (!res.ok) throw new Error(data?.detail || 'خطا در دریافت اطلاعات');
  return data?.results ?? data ?? [];
}
export const platformApi = {
  notifications: () => get('/notifications/notifications/'),
  markAllRead: () => fetch('/api/notifications/notifications/mark_all_read/', { method: 'POST', headers: { Authorization: `Bearer ${authApi.getSession()?.tokens?.access || ''}` } }),
  auditLogs: () => get('/audit/logs/'),
};
