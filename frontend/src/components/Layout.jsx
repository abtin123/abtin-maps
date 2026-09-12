import React, { useState } from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import Icon from './Icon.jsx';
import { ROLES } from '../data/roles.js';
import { authApi } from '../api/auth.js';

export function Sidebar({ role, collapsed, onToggle, mobileOpen, onClose }) {
  const r = ROLES[role];
  return (
    <aside className={`sidebar ${collapsed ? 'collapsed' : ''} ${mobileOpen ? 'open' : ''}`}>
      <div className="sidebar-brand">
        <div className="brand-logo">A</div>
        <div className="brand-meta">
          <div className="brand-name">Abtin Distribution</div>
          <div className="brand-sub">مدیریت هوشمند پخش و توزیع</div>
        </div>
      </div>
      <nav className="side-nav">
        {r.nav.map((item, i) =>
          item.section ? (
            <div key={i} className="nav-section-title">{item.section}</div>
          ) : (
            <NavLink
              key={item.to}
              to={`/app/${role}${item.to}`}
              onClick={onClose}
              className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
            >
              <span className="nav-icon"><Icon name={item.icon} size={19} /></span>
              <span className="nav-label">{item.label}</span>
            </NavLink>
          )
        )}
      </nav>
      <div style={{ padding: 14, borderTop: '1px solid var(--border-soft)' }}>
        <div className="muted" style={{ textAlign: 'center' }}>نسخه ۱.۰.۰ · سیستم آنتین</div>
      </div>
    </aside>
  );
}

export function Topbar({ role, onToggle, onMobile }) {
  const r = ROLES[role];
  const nav = useNavigate();
  // اگر نشست واقعی (JWT) وجود دارد، نام و نقش از API نشان داده می‌شود
  const session = authApi.getSession();
  const displayName = session?.user?.full_name || r.name;
  const displayRole = session?.user?.role?.label || r.label;
  const toggleMenu = () => {
    if (window.matchMedia('(max-width: 900px)').matches) onMobile();
    else onToggle();
  };
  const logout = async () => {
    try {
      if (session?.tokens?.refresh) await authApi.logout(session.tokens.refresh, session.tokens.access);
    } catch { /* نادیده گرفته می‌شود */ }
    authApi.clearSession();
    nav('/');
  };
  return (
    <header className="topbar">
      <button className="topbar-toggle" aria-label="باز و بسته کردن منو" onClick={toggleMenu}><Icon name="menu" size={19} /></button>
      <div className="search-box">
        <Icon name="search" size={17} />
        <input placeholder="جستجو در فاکتورها، مشتریان، کالاها، کاربران…" />
      </div>
      <div className="topbar-right">
        <button className="icon-btn" title="اعلان‌ها" onClick={() => nav(`/app/${role}/notifications`)}>
          <Icon name="bell" size={19} /><i className="dot" />
        </button>
        <div className="user-chip" title="خروج از حساب" onClick={logout}>
          <div>
            <div className="u-name">{displayName}</div>
            <div className="u-role">{displayRole}{session ? ' · آنلاین' : ' · پیش‌نمایش'}</div>
          </div>
          <div className="avatar">{displayName[0]}</div>
        </div>
      </div>
    </header>
  );
}

export function AppShell({ role, children }) {
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const r = ROLES[role];
  return (
    <div className="app-shell">
      <Sidebar role={role} collapsed={collapsed} onToggle={() => setCollapsed(!collapsed)} mobileOpen={mobileOpen} onClose={() => setMobileOpen(false)} />
      <div className={`main-col ${collapsed ? 'collapsed' : ''}`}>
        <Topbar role={role} onToggle={() => setCollapsed(!collapsed)} onMobile={() => setMobileOpen(!mobileOpen)} />
        <main className="page-wrap">{children}</main>
      </div>
      {r.mobile && (
        <div className="mobile-bar">
          <div className="mobile-bar-inner">
            {r.nav.slice(0, 5).map((n) => (
              <NavLink key={n.to} to={`/app/${role}${n.to}`} className={({ isActive }) => `mb-item ${isActive ? 'active' : ''}`}>
                <Icon name={n.icon} size={20} />
                {n.label}
              </NavLink>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
