// کلاینت API احراز هویت — اتصال فرانت به بک‌اند جنگو (فاز ۲)
const BASE = '/api/auth';

async function req(path, { method = 'GET', body, token } = {}) {
  const res = await fetch(`${BASE}${path}`, {
    method,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: body ? JSON.stringify(body) : undefined,
  });
  let data = null;
  try { data = await res.json(); } catch { /* empty body */ }
  if (!res.ok) {
    const msg =
      data?.non_field_errors?.[0] ||
      data?.detail ||
      Object.values(data || {})?.[0]?.[0] ||
      'خطا در ارتباط با سرور';
    throw new Error(msg);
  }
  return data;
}

const store = {
  load() {
    try { return JSON.parse(localStorage.getItem('abtin_auth') || 'null'); } catch { return null; }
  },
  save(auth) { localStorage.setItem('abtin_auth', JSON.stringify(auth)); },
  clear() { localStorage.removeItem('abtin_auth'); },
};

export const authApi = {
  /** ورود با نام کاربری + رمز عبور → { user, tokens } */
  login: (username, password) => req('/login/', { method: 'POST', body: { username, password } }),
  /** درخواست OTP موبایل */
  otpRequest: (mobile) => req('/otp/request/', { method: 'POST', body: { mobile } }),
  /** تأیید OTP → { user, tokens } */
  otpVerify: (mobile, code) => req('/otp/verify/', { method: 'POST', body: { mobile, code } }),
  /** پروفایل کاربر جاری */
  me: (token) => req('/me/', { token }),
  /** سوییچ نقش (مدیر کل) */
  switchRole: (role, token) => req('/switch-role/', { method: 'POST', body: { role }, token }),
  /** خروج (blacklist refresh) */
  logout: (refresh, token) => req('/logout/', { method: 'POST', body: { refresh }, token }),

  getSession: store.load,
  saveSession: store.save,
  clearSession: store.clear,
};
