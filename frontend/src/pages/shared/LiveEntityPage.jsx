import React, { useEffect, useState } from 'react';
import { Card, PageHead, Table } from '../../components/ui.jsx';
import Icon from '../../components/Icon.jsx';
import { createResource, fetchResource, flattenRow } from '../../api/resources.js';

export default function LiveEntityPage({ title, sub, endpoint }) {
  const [rows, setRows] = useState([]); const [json, setJson] = useState('{}'); const [open, setOpen] = useState(false); const [error, setError] = useState(''); const [busy, setBusy] = useState(false);
  const load = () => fetchResource(endpoint).then((items) => setRows(items.map(flattenRow))).catch((e) => setError(e.message));
  useEffect(load, [endpoint]);
  const save = async () => { setBusy(true); setError(''); try { await createResource(endpoint, JSON.parse(json)); setJson('{}'); setOpen(false); await load(); } catch (e) { setError(e.message || 'Payload JSON نامعتبر است'); } finally { setBusy(false); } };
  const cols = rows[0] ? Object.keys(rows[0]).map((key) => ({ key, label: key })) : [{ key: 'state', label: 'وضعیت' }];
  return <><PageHead title={title} sub={`${sub} — اتصال مستقیم به Backend`} actions={<><button className="btn btn-primary btn-sm" onClick={() => setOpen(!open)}><Icon name="plus" size={15} /> ایجاد رکورد</button><button className="btn btn-ghost btn-sm" onClick={load}>به‌روزرسانی</button></>} />{open && <Card title="فرم ثبت واقعی"><p className="muted">اطلاعات را مطابق فیلدهای API به صورت JSON وارد کنید؛ ثبت با POST انجام می‌شود.</p><textarea value={json} onChange={(e) => setJson(e.target.value)} dir="ltr" rows={7} style={{ width: '100%', fontFamily: 'monospace', marginBottom: 10 }} /><button className="btn btn-primary" onClick={save} disabled={busy}>{busy ? 'در حال ثبت…' : 'ذخیره در دیتابیس'}</button></Card>}{error && <div className="badge" style={{ color: 'var(--amber-400)', marginBottom: 12 }}>API: {error}</div>}<Card><Table columns={cols} rows={rows.length ? rows : [{ state: 'رکوردی ثبت نشده است' }]} render={(key, row) => String(row[key] ?? '—')} /></Card></>;
}
