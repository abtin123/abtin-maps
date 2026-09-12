import React from 'react';

/* ---------- Area/Line chart (SVG, no dependency) ---------- */
export function AreaChart({ data = [], height = 220, color = '#2f7bff', labels = [] }) {
  const w = 600, h = height, pad = 24;
  const max = Math.max(...data, 1);
  const min = Math.min(...data, 0);
  const rng = max - min || 1;
  const pts = data.map((v, i) => {
    const x = pad + (i * (w - pad * 2)) / (data.length - 1 || 1);
    const y = h - pad - ((v - min) / rng) * (h - pad * 2);
    return [x, y];
  });
  const line = pts.map((p, i) => (i === 0 ? `M${p[0]},${p[1]}` : `L${p[0]},${p[1]}`)).join(' ');
  const area = `${line} L${pts[pts.length - 1]?.[0] ?? pad},${h - pad} L${pad},${h - pad} Z`;
  return (
    <svg viewBox={`0 0 ${w} ${h}`} className="chart-box" preserveAspectRatio="none">
      <defs>
        <linearGradient id="areaG" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity="0.45" />
          <stop offset="100%" stopColor={color} stopOpacity="0.02" />
        </linearGradient>
      </defs>
      {[0.25, 0.5, 0.75].map((g) => (
        <line key={g} x1={pad} x2={w - pad} y1={h * g} y2={h * g} stroke="rgba(120,150,200,0.12)" strokeDasharray="4 6" />
      ))}
      <path d={area} fill="url(#areaG)" />
      <path d={line} fill="none" stroke={color} strokeWidth="2.5" strokeLinecap="round" />
      {pts.map((p, i) => (
        <circle key={i} cx={p[0]} cy={p[1]} r={i === Math.floor(pts.length / 2) ? 5 : 0} fill="#fff" stroke={color} strokeWidth="3" />
      ))}
      {labels.map((l, i) => (
        <text key={i} x={pad + (i * (w - pad * 2)) / (labels.length - 1 || 1)} y={h - 4} fill="#6f819f" fontSize="11" textAnchor="middle">{l}</text>
      ))}
    </svg>
  );
}

/* ---------- Donut chart ---------- */
export function DonutChart({ segments = [], size = 190, thickness = 26, centerLabel, centerValue }) {
  const total = segments.reduce((s, x) => s + x.value, 0) || 1;
  const r = (size - thickness) / 2;
  const c = 2 * Math.PI * r;
  let offset = 0;
  return (
    <div style={{ position: 'relative', width: size, height: size, margin: '0 auto' }}>
      <svg width={size} height={size} style={{ transform: 'rotate(-90deg)' }}>
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="rgba(120,150,200,0.1)" strokeWidth={thickness} />
        {segments.map((s, i) => {
          const len = (s.value / total) * c;
          const el = (
            <circle
              key={i} cx={size / 2} cy={size / 2} r={r} fill="none"
              stroke={s.color} strokeWidth={thickness}
              strokeDasharray={`${len} ${c - len}`} strokeDashoffset={-offset}
              strokeLinecap="butt"
            />
          );
          offset += len;
          return el;
        })}
      </svg>
      <div style={{ position: 'absolute', inset: 0, display: 'grid', placeItems: 'center', textAlign: 'center' }}>
        <div>
          <div style={{ fontSize: 12, color: 'var(--text-3)' }}>{centerLabel}</div>
          <div style={{ fontSize: 22, fontWeight: 900 }}>{centerValue}</div>
        </div>
      </div>
    </div>
  );
}

/* ---------- Bar chart ---------- */
export function BarChart({ data = [], height = 220, color = '#2dd4bf' }) {
  const w = 600, h = height, pad = 26;
  const max = Math.max(...data.map((d) => d.value), 1);
  const bw = ((w - pad * 2) / data.length) * 0.55;
  return (
    <svg viewBox={`0 0 ${w} ${h}`} className="chart-box" preserveAspectRatio="none">
      {data.map((d, i) => {
        const bh = (d.value / max) * (h - pad * 2);
        const x = pad + (i * (w - pad * 2)) / data.length + bw * 0.4;
        return (
          <g key={i}>
            <rect x={x} y={h - pad - bh} width={bw} height={bh} rx="6" fill={d.color || color} opacity="0.9" />
            <text x={x + bw / 2} y={h - 6} fill="#6f819f" fontSize="11" textAnchor="middle">{d.label}</text>
          </g>
        );
      })}
    </svg>
  );
}

/* ---------- Horizontal progress bars ---------- */
export function ProgressList({ items = [] }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
      {items.map((it, i) => (
        <div key={i}>
          <div className="flex between" style={{ fontSize: 12, marginBottom: 5 }}>
            <span style={{ color: 'var(--text-2)' }}>{it.label}</span>
            <b className="num">{it.value}٪</b>
          </div>
          <div className="progress"><div style={{ width: `${it.value}%`, background: it.color || 'var(--brand-500)' }} /></div>
        </div>
      ))}
    </div>
  );
}
