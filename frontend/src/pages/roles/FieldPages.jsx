import React, { useEffect, useMemo, useState } from 'react';
import { Card, PageHead, Table, StatusBadge } from '../../components/ui.jsx';
import Icon from '../../components/Icon.jsx';
import { customers, products, invoices, deliveries } from '../../data/mock.js';
import { currentPosition, deliveryApi } from '../../api/delivery.js';
import RealMap from '../../components/RealMap.jsx';
import { formatDistance, formatDuration, planRoute } from '../../api/routing.js';
import { syncApi } from '../../api/sync.js';
import { salesApi } from '../../api/sales.js';

function useDeliveryData(loader, fallback) {
  const [data, setData] = useState(fallback);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const reload = async () => {
    setLoading(true); setError('');
    try { setData(await loader()); } catch (e) { setError(e.message); }
    finally { setLoading(false); }
  };
  useEffect(() => { reload(); }, []);
  return { data, setData, loading, error, reload };
}

function ApiNotice({ loading, error, onRetry }) {
  if (loading) return <div className="muted" style={{ marginBottom: 12 }}>در حال دریافت اطلاعات واقعی پخش…</div>;
  if (error) return <div className="badge" style={{ color: 'var(--amber-400)', marginBottom: 12 }}>API در دسترس نیست؛ دادهٔ پیش‌نمایش نمایش داده شد. <button className="btn btn-ghost btn-sm" onClick={onRetry}>تلاش مجدد</button></div>;
  return null;
}

/* ---------- ثبت سفارش واقعی بازاریاب ---------- */
export function NewOrderPage() {
  const [customers, setCustomers] = useState([]); const [products, setProducts] = useState([]); const [customer, setCustomer] = useState(''); const [product, setProduct] = useState(''); const [qty, setQty] = useState(1); const [saving, setSaving] = useState(false); const [message, setMessage] = useState('');
  useEffect(() => { Promise.all([salesApi.customers(), salesApi.products()]).then(([c, p]) => { setCustomers(c); setProducts(p); setCustomer(c[0]?.id || ''); setProduct(p[0]?.id || ''); }).catch((e) => setMessage(e.message)); }, []);
  const submit = async () => { if (!customer || !product || Number(qty) < 1) return setMessage('مشتری، کالا و تعداد معتبر الزامی است.'); setSaving(true); setMessage(''); try { const invoice = await salesApi.createInvoice({ number: `WEB-${Date.now()}`, customer: Number(customer), warehouse: 1, items: [{ product: Number(product), qty: Number(qty) }] }); setMessage(`سفارش ${invoice.number} با موفقیت در دیتابیس ثبت شد.`); } catch (e) { setMessage(e.message); } finally { setSaving(false); } };
  return <><PageHead title="ثبت سفارش جدید" sub="فرآیند واقعی — ثبت مستقیم در API و دیتابیس" />{message && <div className="badge" style={{ color: message.includes('موفقیت') ? 'var(--green-400)' : 'var(--amber-400)', marginBottom: 12 }}>{message}</div>}<div className="grid cols-2"><Card title="اطلاعات سفارش"><div className="field"><label>مشتری</label><select value={customer} onChange={(e) => setCustomer(e.target.value)}><option value="">انتخاب مشتری</option>{customers.map((c) => <option key={c.id} value={c.id}>{c.code} — {c.name}</option>)}</select></div><div className="field"><label>کالا</label><select value={product} onChange={(e) => setProduct(e.target.value)}><option value="">انتخاب کالا</option>{products.map((p) => <option key={p.id} value={p.id}>{p.sku} — {p.name}</option>)}</select></div><div className="field"><label>تعداد</label><input type="number" min="1" value={qty} onChange={(e) => setQty(e.target.value)} /></div><button className="btn btn-primary" onClick={submit} disabled={saving}>{saving ? 'در حال ثبت…' : 'ثبت سفارش واقعی'}</button></Card><Card title="چرخه ثبت"><p className="muted">پس از ثبت، فاکتور در وضعیت پیش‌نویس ایجاد می‌شود و در API قابل مشاهده است. ادامهٔ چرخه شامل ارسال برای تأیید، رزرو موجودی و تأیید نهایی است.</p></Card></div></>;
}

function InvoiceEditor({ customerId = '', customerName = '', onCreated }) {
  const [productsList, setProductsList] = useState([]); const [lines, setLines] = useState([{ product: '', qty: 1 }]); const [saving, setSaving] = useState(false); const [message, setMessage] = useState('');
  useEffect(() => { salesApi.products().then((items) => { setProductsList(items); setLines([{ product: items[0]?.id || '', qty: 1 }]); }).catch((e) => setMessage(e.message)); }, []);
  const updateLine = (index, key, value) => setLines((items) => items.map((item, i) => i === index ? { ...item, [key]: value } : item));
  const save = async () => { if (!customerId || lines.some((line) => !line.product || Number(line.qty) < 1)) return setMessage('مشتری و حداقل یک قلم معتبر الزامی است.'); setSaving(true); setMessage(''); try { const invoice = await salesApi.createInvoice({ number: `VISIT-${Date.now()}`, customer: Number(customerId), warehouse: 1, items: lines.map((line) => ({ product: Number(line.product), qty: Number(line.qty) })) }); setMessage(`فاکتور ${invoice.number} ثبت شد.`); onCreated?.(invoice); } catch (e) { setMessage(e.message); } finally { setSaving(false); } };
  return <Card title="فاکتور و سفارش مشتری" sub={customerName ? `مشتری: ${customerName}` : 'انتخاب مشتری از ویزیت'}><div className="table-wrap"><table className="tbl"><thead><tr><th>کالا</th><th>تعداد</th><th /></tr></thead><tbody>{lines.map((line, index) => <tr key={index}><td><select value={line.product} onChange={(e) => updateLine(index, 'product', e.target.value)}>{productsList.map((p) => <option key={p.id} value={p.id}>{p.sku} — {p.name}</option>)}</select></td><td><input type="number" min="1" value={line.qty} onChange={(e) => updateLine(index, 'qty', e.target.value)} /></td><td><button className="btn btn-ghost btn-sm" onClick={() => setLines((items) => items.filter((_, i) => i !== index))}>حذف</button></td></tr>)}</tbody></table></div><div className="flex mt"><button className="btn btn-ghost btn-sm" onClick={() => setLines((items) => [...items, { product: productsList[0]?.id || '', qty: 1 }])}>افزودن قلم</button><button className="btn btn-primary btn-sm" onClick={save} disabled={saving}>{saving ? 'در حال ثبت…' : 'ثبت فاکتور در دیتابیس'}</button></div>{message && <div className="muted mt">{message}</div>}</Card>;
}

function DeliveryInvoiceCard({ stop }) {
  return <Card title={`فاکتور ${stop.invoice_number || '—'}`} sub="سند تحویل مامور پخش"><div className="grid cols-3"><div><span className="muted">مشتری</span><b>{stop.customer_name || '—'}</b></div><div><span className="muted">وضعیت فاکتور</span><b>{stop.invoice_status || '—'}</b></div><div><span className="muted">مبلغ کل</span><b>{stop.invoice_total || 0} ریال</b></div></div><div className="table-wrap mt"><table className="tbl"><thead><tr><th>کالا</th><th>تعداد</th><th>قیمت واحد</th><th>جمع</th></tr></thead><tbody>{(stop.invoice_items || []).map((item, index) => <tr key={index}><td>{item.product_name}</td><td>{item.qty}</td><td>{item.unit_price}</td><td>{item.line_total}</td></tr>)}</tbody></table></div><div className="muted mt">آدرس: {stop.customer_address || '—'}</div></Card>;
}

/* ---------- مسیر امروز بازاریاب — متصل به API فاز ۵ ---------- */
export function MyRoutePage() {
  const routeState = useDeliveryData(deliveryApi.routes, []);
  const visitState = useDeliveryData(deliveryApi.visits, []);
  const [actionId, setActionId] = useState(null);
  const [invoiceVisit, setInvoiceVisit] = useState(null);
  const [routePlan, setRoutePlan] = useState({ points: [], track: [], distance: 0, duration: 0, optimized: false, steps: [] });
  const [routing, setRouting] = useState(false);
  const [routeError, setRouteError] = useState('');
  const route = routeState.data[0];
  const visits = visitState.data;
  const mapPoints = useMemo(() => visits.map((v) => ({ id: v.id, lat: v.customer_latitude, lng: v.customer_longitude, label: v.customer_name || 'مقصد', color: v.status === 'completed' ? '#4ade80' : v.status === 'in_progress' ? '#fbbf24' : '#f87171', active: v.status === 'in_progress', status: v.status })), [visits]);
  useEffect(() => {
    let cancelled = false;
    if (mapPoints.length < 2) { setRoutePlan({ points: mapPoints, track: [], distance: 0, duration: 0, optimized: false, steps: [] }); return undefined; }
    setRouting(true); setRouteError('');
    planRoute(mapPoints).then((result) => { if (!cancelled) { setRoutePlan(result); if (route?.id && Number.isInteger(Number(route.id))) deliveryApi.saveRoutePlan(route.id, result).catch(() => {}); } }).catch((e) => { if (!cancelled) setRouteError(e.message); }).finally(() => { if (!cancelled) setRouting(false); });
    return () => { cancelled = true; };
  }, [mapPoints]);
  const locate = async (visit, operation) => { setActionId(visit.id); const p = await currentPosition(); try { const updated = operation === 'in' ? await deliveryApi.checkIn(visit.id, p.latitude, p.longitude) : await deliveryApi.checkOut(visit.id, p.latitude, p.longitude); visitState.setData((items) => items.map((x) => x.id === visit.id ? updated : x)); } catch (e) { window.alert(e.message); } finally { setActionId(null); } };
  return <><PageHead title="مسیر امروز" sub={`${route?.name || 'مسیر بازاریاب'} · GPS و وضعیت لحظه‌ای`} actions={<button className="btn btn-primary btn-sm" onClick={async () => { const p = await currentPosition(); if (route?.id && p.latitude) deliveryApi.recordGps(route.id, p.latitude, p.longitude, p.accuracy_meters).then(routeState.reload).catch(() => {}); }}><Icon name="pin" size={15} /> ثبت موقعیت</button>} /><ApiNotice {...routeState} onRetry={routeState.reload} /><ApiNotice {...visitState} onRetry={visitState.reload} />{routing && <div className="muted" style={{ marginBottom: 12 }}>در حال محاسبهٔ مسیر بهینه با OSRM…</div>}{routeError && <div className="badge" style={{ color: 'var(--amber-400)', marginBottom: 12 }}>مسیریابی هوشمند در دسترس نیست؛ مسیر مستقیم نمایش داده می‌شود.</div>}<Card style={{ marginBottom: 16 }}><RealMap height={380} points={routePlan.points.length ? routePlan.points : mapPoints} track={routePlan.track} title="مسیر واقعی بازاریاب" />{routePlan.distance > 0 && <div className="route-summary"><span>فاصله: <b>{formatDistance(routePlan.distance)}</b></span><span>زمان تقریبی: <b>{formatDuration(routePlan.duration)}</b></span>{routePlan.optimized && <span className="badge" style={{ color: 'var(--green-400)' }}>ترتیب توقف‌ها بهینه شد</span>}</div>}</Card><Card title="راهنمای مسیر" sub="ناوبری مرحله‌به‌مرحله بر اساس مسیر جاده‌ای">{routePlan.steps.length ? <div className="turn-list">{routePlan.steps.slice(0, 12).map((step) => <div className="turn-item" key={`${step.index}-${step.road}`}><b className="turn-index">{step.index}</b><div><div>{step.instruction}</div><small>{step.road} · {formatDistance(step.distance)} · {formatDuration(step.duration)}</small></div></div>)}</div> : <div className="muted">پس از دریافت مختصات حداقل دو مقصد، راهنمای مرحله‌ای نمایش داده می‌شود.</div>}</Card><Card title="ایستگاه‌ها" sub="ورود، خروج، GPS و فاکتور در سرور ثبت می‌شود"><Table columns={[{ key: 'id', label: '#' }, { key: 'customer_name', label: 'مشتری' }, { key: 'status', label: 'وضعیت' }, { key: 'check_in_at', label: 'ورود' }, { key: 'check_out_at', label: 'خروج' }, { key: 'act', label: 'اقدام' }]} rows={visits} render={(k, r) => k === 'status' ? <StatusBadge status={r.status === 'completed' ? 'DELIVERED' : r.status === 'in_progress' ? 'OUT_FOR_DELIVERY' : 'PENDING'} /> : k === 'act' ? <div className="flex"><button className="btn btn-primary btn-sm" disabled={actionId === r.id} onClick={() => locate(r, r.status === 'in_progress' ? 'out' : 'in')}>{actionId === r.id ? 'در حال ثبت…' : r.status === 'in_progress' ? 'ثبت خروج' : 'ثبت ورود'}</button><button className="btn btn-ghost btn-sm" onClick={() => setInvoiceVisit(r)}>فاکتور</button></div> : (r[k] ? String(r[k]).replace('T', ' ').slice(0, 16) : '—')} /></Card>{invoiceVisit && <InvoiceEditor customerId={route?.stops?.find((s) => s.id === invoiceVisit.route_stop)?.customer} customerName={invoiceVisit.customer_name} onCreated={() => setInvoiceVisit(null)} />}</>;
}

/* ---------- لیست تحویل مامور پخش — متصل به API فاز ۵ ---------- */
export function DeliveryListPage() {
  const state = useDeliveryData(deliveryApi.deliveryStops, []);
  const [selected, setSelected] = useState(null); const [saving, setSaving] = useState(false); const [status, setStatus] = useState('delivered'); const [amount, setAmount] = useState('0');
  const rows = state.data.length ? state.data : deliveries.map((d, i) => ({ id: `preview-${i}`, invoice_number: d.invoice, customer_name: d.customer, customer_address: d.address, status: d.status, customer_latitude: null, customer_longitude: null }));
  const submit = async () => { if (!selected || String(selected.id).startsWith('preview')) return window.alert('برای ثبت واقعی، ابتدا به API وارد شوید.'); setSaving(true); const p = await currentPosition(); try { await deliveryApi.deliver(selected.id, { status, received_amount: amount || 0, latitude: p.latitude, longitude: p.longitude, payment_method: 'cash' }); setSelected(null); await state.reload(); } catch (e) { window.alert(e.message); } finally { setSaving(false); } };
  return <><PageHead title="لیست تحویل" sub="توقف‌های سفر پخش — ثبت نتیجه با GPS و رسید" /><ApiNotice {...state} onRetry={state.reload} /><Card><Table columns={[{ key: 'invoice_number', label: 'فاکتور' }, { key: 'customer_name', label: 'مشتری' }, { key: 'customer_address', label: 'آدرس Snapshot' }, { key: 'status', label: 'تحویل' }, { key: 'act', label: 'اقدامات' }]} rows={rows} render={(k, r) => k === 'status' ? <StatusBadge status={r.status === 'delivered' ? 'DELIVERED' : r.status === 'failed' ? 'REJECTED' : 'PENDING'} /> : k === 'act' ? <div className="flex"><a className="btn btn-primary btn-sm" target="_blank" rel="noreferrer" href={r.customer_latitude && r.customer_longitude ? `https://www.google.com/maps/dir/?api=1&destination=${r.customer_latitude},${r.customer_longitude}` : '#'}><Icon name="pin" size={13} /> مسیریابی</a><button className="btn btn-ghost btn-sm" onClick={() => setSelected(r)}>فاکتور / تحویل</button></div> : r[k] || '—'} /></Card>{selected && <DeliveryInvoiceCard stop={selected} />}<div className="grid cols-2 mt"><Card title="ثبت نتیجه تحویل"><div className="tabs">{[['delivered', 'تحویل کامل'], ['partial', 'تحویل ناقص'], ['failed', 'عدم تحویل'], ['returned', 'برگشت کالا']].map(([v, l]) => <span key={v} className={`tab ${status === v ? 'active' : ''}`} onClick={() => setStatus(v)}>{l}</span>)}</div><div className="field"><label>توقف انتخاب‌شده</label><input readOnly value={selected ? `${selected.invoice_number || selected.id} — ${selected.customer_name || ''}` : 'از جدول انتخاب کنید'} /></div><div className="field"><label>مبلغ دریافتی</label><input value={amount} onChange={(e) => setAmount(e.target.value)} inputMode="numeric" /></div><button className="btn btn-primary" disabled={!selected || saving} onClick={submit} style={{ width: '100%', justifyContent: 'center' }}><Icon name="check" size={15} /> {saving ? 'در حال ثبت…' : 'تأیید تحویل و ثبت رسید'}</button></Card><Card title="قوانین ثبت تحویل"><p className="muted">نتیجه، مختصات فعلی، مبلغ دریافتی، روش پرداخت و تاریخچهٔ تلاش تحویل در بک‌اند ذخیره می‌شود. در حالت عدم تحویل می‌توانید دلیل را نیز در API ارسال کنید.</p><div className="grid cols-2">{['مشتری بسته بود', 'عدم موجودی وجه', 'مغایرت سفارش', 'عدم پذیرش', 'آدرس اشتباه', 'سایر'].map((d) => <button key={d} className="btn btn-ghost" onClick={() => setStatus('failed')} style={{ justifyContent: 'center' }}>{d}</button>)}</div></Card></div></>;
}

export function OfflinePage() {
  const [items, setItems] = useState([]); const [lastSync, setLastSync] = useState('—'); const [syncing, setSyncing] = useState(false); const [conflicts, setConflicts] = useState(0);
  const refresh = () => syncApi.pending().then(setItems).catch(() => setItems([]));
  useEffect(() => { refresh(); }, []);
  const sync = async () => { setSyncing(true); try { const result = await syncApi.push(); setConflicts(result.conflicts.length); setLastSync(new Date().toLocaleTimeString('fa-IR', { hour: '2-digit', minute: '2-digit' })); await refresh(); } catch { /* offline remains queued */ } finally { setSyncing(false); } };
  const rows = items.length ? items.map((x) => ({ t: x.entity, d: x.operation, time: x.client_updated_at?.slice(0, 16).replace('T', ' '), st: 'PENDING' })) : [{ t: 'صف خالی', d: 'عملیات آفلاین جدیدی ثبت نشده است', time: '—', st: 'DELIVERED' }];
  return <><PageHead title="همگام‌سازی آفلاین" sub="IndexedDB — صف ارسال و Conflict Resolution" /><div className="grid cols-3" style={{ marginBottom: 16 }}>{[['آیتم در صف ارسال', String(items.length)], ['آخرین همگام‌سازی', lastSync], ['وضعیت اتصال', navigator.onLine ? 'آنلاین' : 'آفلاین']].map(([l, v]) => <Card key={l}><div className="kpi-label">{l}</div><div className="kpi-value num">{v}</div><div className="muted">{conflicts ? `${conflicts} تعارض نیازمند بررسی` : 'تعارضی ثبت نشده است'}</div></Card>)}</div><Card title="صف آفلاین" action={<button className="btn btn-primary btn-sm" onClick={sync} disabled={syncing}><Icon name="sync" size={15} /> {syncing ? 'در حال همگام‌سازی…' : 'همگام‌سازی همه'}</button>}><Table columns={[{ key: 't', label: 'نوع' }, { key: 'd', label: 'شرح' }, { key: 'time', label: 'زمان ثبت آفلاین' }, { key: 'st', label: 'وضعیت' }]} rows={rows} render={(k, r) => k === 'st' ? <StatusBadge status={r.st} /> : r[k]} /></Card></>;
}

export function SimpleListPage({ title, sub, columns, rows, render }) { return <><PageHead title={title} sub={sub} /><Card><Table columns={columns} rows={rows} render={render} /></Card></>; }
