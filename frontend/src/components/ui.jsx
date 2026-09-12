import React from 'react';
import Icon from './Icon.jsx';

/* ---------- Card ---------- */
export function Card({ title, sub, action, children, className = '', style }) {
  return (
    <div className={`card ${className}`} style={style}>
      {(title || action) && (
        <div className="card-title">
          <span>{title} {sub && <small>· {sub}</small>}</span>
          {action}
        </div>
      )}
      {children}
    </div>
  );
}

/* ---------- KPI card ---------- */
const TINTS = {
  blue: ['rgba(47,123,255,0.15)', '#5b97ff'],
  teal: ['rgba(45,212,191,0.15)', '#2dd4bf'],
  violet: ['rgba(167,139,250,0.15)', '#a78bfa'],
  amber: ['rgba(251,191,36,0.15)', '#fbbf24'],
  rose: ['rgba(251,113,133,0.15)', '#fb7185'],
  green: ['rgba(74,222,128,0.15)', '#4ade80'],
  orange: ['rgba(251,146,60,0.15)', '#fb923c'],
  pink: ['rgba(244,114,182,0.15)', '#f472b6'],
};
export function Kpi({ icon, label, value, delta, dir = 'up', tint = 'blue' }) {
  const [bg, fg] = TINTS[tint] || TINTS.blue;
  return (
    <div className="card kpi">
      <div className="kpi-top">
        <div className="kpi-icon" style={{ background: bg, color: fg }}><Icon name={icon} size={21} /></div>
        {delta && <span className={`kpi-delta ${dir}`}>{dir === 'up' ? '↑' : '↓'} {delta}</span>}
      </div>
      <div className="kpi-label">{label}</div>
      <div className="kpi-value num">{value}</div>
    </div>
  );
}

/* ---------- Status badge ---------- */
const STATUS = {
  DRAFT: ['پیش‌نویس', 'var(--st-draft)'],
  PENDING: ['در انتظار تأیید', 'var(--st-pending)'],
  RESERVED: ['رزرو شده', 'var(--st-reserved)'],
  CONFIRMED: ['تأیید شده', 'var(--st-confirmed)'],
  WAREHOUSE_PENDING: ['در صف انبار', 'var(--st-warehouse)'],
  PREPARING: ['در حال آماده‌سازی', 'var(--st-warehouse)'],
  READY_FOR_DELIVERY: ['آماده پخش', 'var(--violet-400)'],
  OUT_FOR_DELIVERY: ['در حال ارسال', 'var(--st-delivering)'],
  DELIVERED: ['تحویل شده', 'var(--st-delivered)'],
  PARTIALLY_DELIVERED: ['تحویل ناقص', 'var(--amber-400)'],
  PAID: ['تسویه شده', 'var(--st-paid)'],
  PARTIALLY_PAID: ['پرداخت ناقص', 'var(--amber-400)'],
  UNPAID: ['پرداخت نشده', 'var(--st-rejected)'],
  CANCELLED: ['لغو شده', 'var(--st-cancelled)'],
  REJECTED: ['رد شده', 'var(--st-rejected)'],
  RETURNED: ['برگشتی', 'var(--st-returned)'],
};
export function StatusBadge({ status }) {
  const [label, color] = STATUS[status] || [status, 'var(--text-3)'];
  return (
    <span className="badge" style={{ color, background: `color-mix(in srgb, ${color} 12%, transparent)` }}>
      <i className="b-dot" />{label}
    </span>
  );
}

/* ---------- Table ---------- */
export function Table({ columns = [], rows = [], render }) {
  return (
    <div className="table-wrap">
      <table className="tbl">
        <thead>
          <tr>{columns.map((c) => <th key={c.key}>{c.label}</th>)}</tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={i}>{columns.map((c) => <td key={c.key} className={c.num ? 'num' : ''}>{render ? render(c.key, r) : r[c.key]}</td>)}</tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/* ---------- Page header ---------- */
export function PageHead({ title, sub, actions }) {
  return (
    <div className="page-head">
      <div>
        <div className="page-title">{title}</div>
        {sub && <div className="page-sub">{sub}</div>}
      </div>
      {actions && <div className="page-actions">{actions}</div>}
    </div>
  );
}

/* ---------- Mock map ---------- */
export function MockMap({ pins = [], height = 340 }) {
  const path = 'M 40 260 C 120 200, 150 240, 210 170 S 330 120, 380 150 S 480 90, 560 60';
  return (
    <div className="map-mock" style={{ minHeight: height }}>
      <svg className="map-route-line" viewBox="0 0 600 320" preserveAspectRatio="none">
        <path d={path} fill="none" stroke="#2f7bff" strokeWidth="3" strokeDasharray="8 7" strokeLinecap="round" opacity="0.9" />
        <path d={path} fill="none" stroke="#2dd4bf" strokeWidth="3" strokeLinecap="round" opacity="0.55" strokeDasharray="0 14 120 999" />
      </svg>
      {pins.map((p, i) => (
        <div className="map-pin" key={i} style={{ top: `${p.y}%`, left: `${p.x}%` }}>
          <span>{p.label}</span>
          <div className="pin" style={{ background: p.color || 'var(--brand-500)' }} />
        </div>
      ))}
    </div>
  );
}

/* ---------- Timeline item ---------- */
export function TlItem({ icon, tint = 'blue', title, desc, time }) {
  const [bg, fg] = TINTS[tint] || TINTS.blue;
  return (
    <div className="tl-item">
      <div className="tl-icon" style={{ background: bg, color: fg }}><Icon name={icon} size={17} /></div>
      <div className="tl-body">
        <div className="tl-title">{title}</div>
        {desc && <div className="muted">{desc}</div>}
      </div>
      <div className="tl-time num">{time}</div>
    </div>
  );
}

/* ---------- Empty state ---------- */
export function EmptyState({ title = 'داده‌ای یافت نشد', desc = 'با تغییر فیلترها دوباره تلاش کنید.' }) {
  return (
    <div className="empty-state">
      <div className="e-icon"><Icon name="search" size={28} /></div>
      <b>{title}</b>
      <div>{desc}</div>
    </div>
  );
}
