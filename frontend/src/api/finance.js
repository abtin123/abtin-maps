import { authApi } from './auth.js';

async function request(path, { method = 'GET', body } = {}) {
  const session = authApi.getSession();
  const res = await fetch(`/api${path}`, {
    method,
    headers: {
      'Content-Type': 'application/json',
      ...(session?.tokens?.access ? { Authorization: `Bearer ${session.tokens.access}` } : {}),
    },
    body: body ? JSON.stringify(body) : undefined,
  });
  const data = await res.json().catch(() => null);
  if (!res.ok) throw new Error(data?.detail || 'خطا در دریافت اطلاعات');
  return data;
}

const list = (path) => request(path).then((data) => data?.results ?? data ?? []);

export const financeApi = {
  summary: () => request('/finance/reports/summary/'),
  journalEntries: () => list('/finance/journal-entries/'),
  cheques: () => list('/finance/cheques/'),
  dueCheques: () => list('/finance/cheques/due/?days=7'),
  employees: () => list('/hr/employees/'),
  attendance: () => list('/hr/attendance/'),
  leaveRequests: () => list('/hr/leave-requests/'),
  payroll: () => list('/finance/payroll/'),
  csvUrl: '/api/finance/reports/csv/',
  async downloadCsv() {
    const session = authApi.getSession();
    const res = await fetch(this.csvUrl, { headers: { Authorization: `Bearer ${session?.tokens?.access || ''}` } });
    if (!res.ok) throw new Error('دریافت CSV ناموفق بود');
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a'); link.href = url; link.download = 'finance-journal.csv'; link.click();
    URL.revokeObjectURL(url);
  },
};
