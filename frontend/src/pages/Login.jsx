import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import Icon from '../components/Icon.jsx';
import { ROLE_LIST } from '../data/roles.js';
import { authApi } from '../api/auth.js';

export default function Login() {
  const nav = useNavigate();
  const [tab, setTab] = useState('password'); // password | otp | preview
  const [username, setUsername] = useState('admin');
  const [password, setPassword] = useState('12345678');
  const [mobile, setMobile] = useState('');
  const [otpCode, setOtpCode] = useState('');
  const [otpSent, setOtpSent] = useState(false);
  const [devCode, setDevCode] = useState(null);
  const [role, setRole] = useState('super_admin');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const finishLogin = (data) => {
    authApi.saveSession(data);
    const code = data.user.role?.code || 'super_admin';
    nav(`/app/${code}/dashboard`);
  };

  const run = async (fn) => {
    setError('');
    setLoading(true);
    try { await fn(); } catch (e) { setError(e.message); } finally { setLoading(false); }
  };

  const submitPassword = () =>
    run(async () => finishLogin(await authApi.login(username.trim(), password)));

  const sendOtp = () =>
    run(async () => {
      const res = await authApi.otpRequest(mobile.trim());
      setOtpSent(true);
      if (res.dev_code) setDevCode(res.dev_code);
    });

  const verifyOtp = () =>
    run(async () => finishLogin(await authApi.otpVerify(mobile.trim(), otpCode.trim())));

  const tabBtn = (id, label) => (
    <button
      className={tab === id ? 'sel' : ''}
      style={{ flex: 1, padding: '9px 6px' }}
      onClick={() => { setTab(id); setError(''); }}
    >
      {label}
    </button>
  );

  return (
    <div className="login-page">
      <div className="card login-card">
        <div className="login-logo">
          <div className="brand-logo">A</div>
          <div>
            <div style={{ fontWeight: 900, fontSize: 18 }}>Abtin Distribution</div>
            <div className="muted">سامانه یکپارچه مدیریت پخش و توزیع</div>
          </div>
        </div>

        <div className="role-pick" style={{ display: 'flex', gap: 6, marginBottom: 14 }}>
          {tabBtn('password', 'ورود با رمز عبور')}
          {tabBtn('otp', 'ورود با موبایل (OTP)')}
          {tabBtn('preview', 'پیش‌نمایش نقش‌ها')}
        </div>

        {tab === 'password' && (
          <>
            <div className="field">
              <label>نام کاربری</label>
              <input value={username} onChange={(e) => setUsername(e.target.value)} placeholder="مثلاً admin" />
            </div>
            <div className="field">
              <label>رمز عبور</label>
              <input type="password" value={password} onChange={(e) => setPassword(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && submitPassword()} placeholder="••••••••" />
            </div>
            <button className="btn btn-primary" disabled={loading}
              style={{ width: '100%', justifyContent: 'center', marginTop: 6 }} onClick={submitPassword}>
              <Icon name="logout" size={17} /> {loading ? 'در حال ورود…' : 'ورود به پنل'}
            </button>
          </>
        )}

        {tab === 'otp' && (
          <>
            <div className="field">
              <label>شماره موبایل</label>
              <input value={mobile} onChange={(e) => setMobile(e.target.value)}
                placeholder="09xxxxxxxxx" dir="ltr" style={{ textAlign: 'right' }} />
            </div>
            {otpSent && (
              <div className="field">
                <label>کد تأیید</label>
                <input value={otpCode} onChange={(e) => setOtpCode(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && verifyOtp()} placeholder="کد ۶ رقمی" dir="ltr" style={{ textAlign: 'right' }} />
                {devCode && <div className="muted" style={{ marginTop: 6 }}>حالت dev — کد: <b dir="ltr">{devCode}</b></div>}
              </div>
            )}
            <button className="btn btn-primary" disabled={loading}
              style={{ width: '100%', justifyContent: 'center', marginTop: 6 }}
              onClick={otpSent ? verifyOtp : sendOtp}>
              <Icon name="bell" size={17} /> {loading ? 'لطفاً صبر کنید…' : otpSent ? 'تأیید و ورود' : 'ارسال کد تأیید'}
            </button>
            {otpSent && (
              <button className="btn" style={{ width: '100%', justifyContent: 'center', marginTop: 8 }}
                onClick={sendOtp} disabled={loading}>ارسال مجدد کد</button>
            )}
          </>
        )}

        {tab === 'preview' && (
          <>
            <div className="field">
              <label>ورود به عنوان (پیش‌نمایش UI هر نقش — بدون احراز هویت)</label>
              <div className="role-pick">
                {ROLE_LIST.map((r) => (
                  <button key={r.id} className={role === r.id ? 'sel' : ''} onClick={() => setRole(r.id)}>
                    {r.label}
                  </button>
                ))}
              </div>
            </div>
            <button className="btn btn-primary" style={{ width: '100%', justifyContent: 'center', marginTop: 6 }}
              onClick={() => { authApi.clearSession(); nav(`/app/${role}/dashboard`); }}>
              <Icon name="logout" size={17} /> ورود پیش‌نمایش
            </button>
          </>
        )}

        {error && <div style={{ color: 'var(--danger, #ef4444)', textAlign: 'center', marginTop: 12 }}>{error}</div>}
        <div className="muted" style={{ textAlign: 'center', marginTop: 14 }}>
          احراز هویت واقعی (JWT + OTP) متصل است — کاربران نمونه با رمز 12345678
        </div>
      </div>
    </div>
  );
}
