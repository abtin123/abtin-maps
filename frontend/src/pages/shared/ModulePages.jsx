import React, { useEffect, useState } from 'react';
import { Card, PageHead, Table, StatusBadge, MockMap, TlItem, EmptyState } from '../../components/ui.jsx';
import { AreaChart, ProgressList } from '../../components/Charts.jsx';
import Icon from '../../components/Icon.jsx';
import { invoices, products, customers, checks, employees, auditLogs, notifications, salesTrend } from '../../data/mock.js';
import { financeApi } from '../../api/finance.js';
import { platformApi } from '../../api/platform.js';
import { createResource, fetchResource, flattenRow } from '../../api/resources.js';

const invoiceCols = [
  { key: 'no', label: 'شماره فاکتور' }, { key: 'customer', label: 'مشتری' }, { key: 'rep', label: 'بازاریاب' },
  { key: 'amount', label: 'مبلغ (ریال)', num: true }, { key: 'date', label: 'تاریخ' }, { key: 'status', label: 'وضعیت' }, { key: 'act', label: 'اقدام' },
];

/* ---------- فاکتورها ---------- */
export function InvoicesPage() {
  return (
    <>
      <PageHead title="فاکتورها" sub="مدیریت چرخه کامل فاکتور — State Machine"
        actions={<><button className="btn btn-ghost btn-sm">خروجی Excel</button><button className="btn btn-primary btn-sm"><Icon name="plus" size={15} /> فاکتور جدید</button></>} />
      <div className="tabs">
        {['همه (۸۵)', 'در انتظار تأیید (۷)', 'رزرو شده (۱۲)', 'آماده پخش (۹)', 'در حال ارسال (۱۴)', 'تحویل شده (۳۱)', 'تسویه شده', 'لغو/برگشتی'].map((t, i) => (
          <span key={t} className={`tab ${i === 0 ? 'active' : ''}`}>{t}</span>
        ))}
      </div>
      <div className="filter-bar">
        <input placeholder="جستجو: شماره، مشتری…" />
        <select><option>همه شعب</option><option>مرکزی</option></select>
        <select><option>همه بازاریاب‌ها</option></select>
        <select><option>از تاریخ</option></select>
        <select><option>تا تاریخ</option></select>
      </div>
      <Card>
        <Table columns={invoiceCols} rows={invoices} render={(k, r) =>
          k === 'status' ? <StatusBadge status={r.status} /> :
          k === 'act' ? <div className="flex"><button className="btn btn-ghost btn-sm">جزئیات</button><button className="btn btn-ghost btn-sm">تاریخچه</button></div> : r[k]} />
      </Card>
      <div className="grid cols-2 mt">
        <Card title="تاریخچه وضعیت — فاکتور #۱۲۵۰" sub="Invoice Status History">
          <div className="timeline">
            {[
              ['ایجاد فاکتور', '۱۰:۲۱', 'invoice', 'blue'],
              ['رزرو موجودی', '۱۰:۲۲', 'clock', 'blue'],
              ['تأیید مدیر فروش', '۱۰:۲۵', 'approval', 'teal'],
              ['آماده‌سازی انبار', '۱۱:۰۰', 'box', 'violet'],
              ['تحویل به مامور پخش', '۱۲:۱۵', 'truck', 'orange'],
              ['تحویل به مشتری + امضا', '۱۳:۱۵', 'check', 'green'],
              ['ثبت رسید و دریافت وجه', '۱۳:۲۰', 'wallet', 'green'],
            ].map(([t, time, ic, tint]) => <TlItem key={t} icon={ic} tint={tint} title={t} time={time} />)}
          </div>
        </Card>
        <Card title="رزرو موجودی — فاکتور #۱۲۵۰" sub="Available = Physical − Reserved">
          <Table
            columns={[{ key: 'sku', label: 'کد' }, { key: 'name', label: 'کالا' }, { key: 'stock', label: 'فیزیکی', num: true }, { key: 'reserved', label: 'رزرو', num: true }, { key: 'available', label: 'آزاد', num: true }]}
            rows={products.slice(0, 4)}
          />
        </Card>
      </div>
    </>
  );
}

/* ---------- کالاها ---------- */
export function ProductsPage() {
  return (
    <>
      <PageHead title="کالاها" sub="مدیریت کالا، قیمت‌گذاری و موجودی"
        actions={<><button className="btn btn-ghost btn-sm"><Icon name="barcode" size={15} /> اسکن بارکد</button><button className="btn btn-primary btn-sm"><Icon name="plus" size={15} /> کالای جدید</button></>} />
      <div className="filter-bar">
        <input placeholder="جستجو: نام، SKU، بارکد…" />
        <select><option>همه برندها</option></select>
        <select><option>همه دسته‌ها</option></select>
        <select><option>همه انبارها</option></select>
      </div>
      <Card>
        <Table
          columns={[{ key: 'sku', label: 'SKU' }, { key: 'name', label: 'نام کالا' }, { key: 'brand', label: 'برند' }, { key: 'stock', label: 'فیزیکی', num: true }, { key: 'reserved', label: 'رزرو', num: true }, { key: 'available', label: 'آزاد', num: true }, { key: 'price', label: 'قیمت فروش', num: true }, { key: 'status', label: 'وضعیت' }]}
          rows={products}
          render={(k, r) => k === 'status'
            ? <span className="badge" style={{ color: r.status === 'ok' ? 'var(--green-400)' : r.status === 'low' ? 'var(--amber-400)' : 'var(--red-400)', background: 'rgba(255,255,255,0.05)' }}><i className="b-dot" />{r.status === 'ok' ? 'موجود' : r.status === 'low' ? 'رو به اتمام' : 'تمام شده'}</span>
            : r[k]} />
      </Card>
    </>
  );
}

/* ---------- مشتریان ---------- */
export function CustomersPage() {
  return (
    <>
      <PageHead title="مشتریان" sub="CRM — ۱,۲۵۰ مشتری فعال"
        actions={<button className="btn btn-primary btn-sm"><Icon name="plus" size={15} /> مشتری جدید</button>} />
      <div className="filter-bar">
        <input placeholder="جستجو: فروشگاه، مالک، تلفن…" />
        <select><option>همه مناطق</option></select>
        <select><option>همه بازاریاب‌ها</option></select>
        <select><option>وضعیت اعتبار</option></select>
      </div>
      <Card>
        <Table
          columns={[{ key: 'name', label: 'فروشگاه' }, { key: 'owner', label: 'مالک' }, { key: 'zone', label: 'منطقه' }, { key: 'rep', label: 'بازاریاب' }, { key: 'balance', label: 'بدهی', num: true }, { key: 'credit', label: 'سقف اعتبار', num: true }, { key: 'lastBuy', label: 'آخرین خرید' }, { key: 'act', label: '' }]}
          rows={customers}
          render={(k, r) => k === 'act'
            ? <div className="flex"><button className="btn btn-ghost btn-sm"><Icon name="pin" size={14} /> نقشه</button><button className="btn btn-ghost btn-sm">پرونده</button></div>
            : k === 'balance' ? <b style={{ color: r.balance === '۰' ? 'var(--green-400)' : 'var(--amber-400)' }}>{r.balance}</b> : r[k]} />
      </Card>
    </>
  );
}

/* ---------- موجودی / رزرو ---------- */
export function InventoryPage() {
  return (
    <>
      <PageHead title="موجودی و رزرو" sub="موجودی لحظه‌ای، رزرو شده، در مسیر" />
      <div className="grid cols-4" style={{ marginBottom: 16 }}>
        {[['فیزیکی کل', '۴۵,۸۲۰', 'blue'], ['رزرو شده', '۱,۷۴۰', 'violet'], ['قابل فروش', '۴۴,۰۸۰', 'green'], ['در مسیر', '۳۲۵', 'orange']].map(([l, v, t]) => (
          <Card key={l}><div className="kpi-label">{l}</div><div className="kpi-value num" style={{ color: `var(--${t === 'blue' ? 'brand-400' : t + '-400'})` }}>{v}</div></Card>
        ))}
      </div>
      <Card title="موجودی لحظه‌ای به تفکیک کالا">
        <Table
          columns={[{ key: 'sku', label: 'SKU' }, { key: 'name', label: 'کالا' }, { key: 'stock', label: 'فیزیکی', num: true }, { key: 'reserved', label: 'رزرو', num: true }, { key: 'available', label: 'آزاد', num: true }]}
          rows={products}
        />
      </Card>
    </>
  );
}

/* ---------- مسیرها ---------- */
export function RoutesPage() {
  return (
    <>
      <PageHead title="مسیرهای فروش" sub="تعریف، تخصیص و پایش مسیر"
        actions={<button className="btn btn-primary btn-sm"><Icon name="plus" size={15} /> مسیر جدید</button>} />
      <div className="grid" style={{ gridTemplateColumns: '3fr 2fr' }}>
        <Card title="مسیر ۱۲ — منطقه غرب" sub="بازاریاب: امیر حسینی · شنبه‌ها">
          <MockMap height={320} pins={[
            { x: 15, y: 60, label: 'ایست ۱ ✓', color: '#4ade80' },
            { x: 35, y: 42, label: 'ایست ۲ ✓', color: '#4ade80' },
            { x: 52, y: 58, label: 'ایست ۳ ●', color: '#fbbf24' },
            { x: 70, y: 36, label: 'ایست ۴ ○', color: '#f87171' },
            { x: 87, y: 55, label: 'ایست ۵ ○', color: '#f87171' },
          ]} />
          <div className="map-legend">
            <span><i style={{ background: '#4ade80' }} />انجام شده</span>
            <span><i style={{ background: '#fbbf24' }} />در حال انجام</span>
            <span><i style={{ background: '#f87171' }} />انجام نشده</span>
            <span><i style={{ background: '#94a3b8' }} />لغو شده</span>
          </div>
        </Card>
        <Card title="مسیرهای فعال امروز">
          <Table
            columns={[{ key: 'r', label: 'مسیر' }, { key: 'rep', label: 'بازاریاب' }, { key: 'p', label: 'پیشرفت' }]}
            rows={[
              { r: 'مسیر ۱۲ — غرب', rep: 'امیر حسینی', p: 62 }, { r: 'مسیر ۸ — مرکز', rep: 'رضا عزیزی', p: 45 },
              { r: 'مسیر ۳ — شرق', rep: 'سارا کاظمی', p: 30 }, { r: 'مسیر ۵ — شمال', rep: 'علی نادری', p: 80 },
            ]}
            render={(k, r2) => k === 'p' ? <div className="progress" style={{ width: 100 }}><div style={{ width: `${r2.p}%`, background: 'var(--brand-500)' }} /></div> : r2[k]}
          />
        </Card>
      </div>
    </>
  );
}

/* ---------- حسابداری ---------- */
export function AccountingPage() {
  const [summary, setSummary] = useState(null);
  const [entries, setEntries] = useState(invoices.slice(0, 3).map((r, i) => ({ no: `98${i + 1}`, desc: r.customer, debit: r.amount, credit: r.amount, date: r.date, status: 'PENDING' })));
  useEffect(() => {
    Promise.all([financeApi.summary(), financeApi.journalEntries()]).then(([s, e]) => {
      setSummary(s);
      setEntries(e.map((x) => ({ no: x.number, desc: x.description, debit: x.total_debit, credit: x.total_credit, date: x.entry_date, status: x.status.toUpperCase() })));
    }).catch(() => {});
  }, []);
  return (
    <>
      <PageHead title="حسابداری" sub="دفتر روزنامه، سرفصل‌ها و اسناد خودکار" />
      <div className="tabs">
        {['دفتر روزنامه', 'دفتر کل', 'دفتر معین', 'صندوق', 'بانک', 'بدهکاران', 'بستانکاران', 'سود و زیان'].map((t, i) => (
          <span key={t} className={`tab ${i === 0 ? 'active' : ''}`}>{t}</span>
        ))}
      </div>
      <div className="grid cols-2" style={{ marginBottom: 16 }}>
        <Card title="سود و زیان ماه جاری">
          <ProgressList items={[
            { label: 'درآمد', value: Number(summary?.income || 100), color: '#4ade80' },
            { label: 'هزینه', value: Number(summary?.expense || 62), color: '#fbbf24' },
            { label: 'سود خالص', value: Number(summary?.net_profit || 17), color: '#2dd4bf' },
          ]} />
        </Card>
        <Card title="جریان نقدینگی"><AreaChart data={salesTrend.data} labels={salesTrend.labels} color="#4ade80" height={190} /></Card>
      </div>
      <Card title="اسناد حسابداری خودکار" sub="بدهکار / بستانکار">
        <Table
          columns={[{ key: 'no', label: 'شماره سند' }, { key: 'desc', label: 'شرح' }, { key: 'debit', label: 'بدهکار', num: true }, { key: 'credit', label: 'بستانکار', num: true }, { key: 'date', label: 'تاریخ' }, { key: 'status', label: 'وضعیت' }]}
          rows={entries}
          render={(k, r) => k === 'status' ? <StatusBadge status={r.status} /> : r[k]}
        />
      </Card>
    </>
  );
}

/* ---------- چک‌ها ---------- */
export function ChecksPage() {
  const [rows, setRows] = useState(checks);
  useEffect(() => { financeApi.cheques().then((data) => setRows(data.map((x) => ({ no: x.number, bank: x.bank, owner: x.owner, amount: x.amount, due: x.due_date, status: x.status.toUpperCase() })))).catch(() => {}); }, []);
  return (
    <>
      <PageHead title="مدیریت چک" sub="دریافتی، پرداختی، سررسید و وصول"
        actions={<button className="btn btn-primary btn-sm"><Icon name="plus" size={15} /> ثبت چک</button>} />
      <Card>
        <Table
          columns={[{ key: 'no', label: 'شماره چک' }, { key: 'bank', label: 'بانک' }, { key: 'owner', label: 'صاحب چک' }, { key: 'amount', label: 'مبلغ', num: true }, { key: 'due', label: 'سررسید' }, { key: 'status', label: 'وضعیت' }]}
          rows={rows}
          render={(k, r) => k === 'status' ? <StatusBadge status={r.status} /> : r[k]}
        />
      </Card>
    </>
  );
}

/* ---------- HR ---------- */
export function EmployeesPage() {
  const [rows, setRows] = useState(employees);
  useEffect(() => {
    Promise.all([financeApi.employees(), financeApi.attendance()]).then(([people, attendance]) => {
      const today = new Date().toISOString().slice(0, 10);
      setRows(people.map((x) => {
        const a = attendance.find((item) => item.employee === x.id && item.work_date === today);
        return { name: x.full_name, role: x.title || '—', branch: x.branch || '—', checkin: a?.check_in_at ? new Date(a.check_in_at).toLocaleTimeString('fa-IR', { hour: '2-digit', minute: '2-digit' }) : '—', status: a?.check_in_at ? 'حاضر' : 'غایب' };
      }));
    }).catch(() => {});
  }, []);
  return (
    <>
      <PageHead title="کارکنان" sub="۴۵ نفر — ۵ واحد" actions={<button className="btn btn-primary btn-sm"><Icon name="plus" size={15} /> کارمند جدید</button>} />
      <Card>
        <Table
          columns={[{ key: 'name', label: 'نام' }, { key: 'role', label: 'سمت' }, { key: 'branch', label: 'شعبه' }, { key: 'checkin', label: 'ورود امروز' }, { key: 'status', label: 'وضعیت' }]}
          rows={rows}
          render={(k, r) => k === 'status' ? <StatusBadge status={r.status === 'حاضر' ? 'DELIVERED' : 'CANCELLED'} /> : r[k]}
        />
      </Card>
    </>
  );
}

/* ---------- گزارشات ---------- */
export function ReportsPage() {
  const cards = [
    ['sales', 'گزارش فروش', 'روزانه، ماهانه، مقایسه‌ای', 'teal'], ['warehouse', 'گزارش انبار', 'موجودی، گردش، کاردکس', 'violet'],
    ['wallet', 'گزارش مالی', 'وصول، بدهی، سود و زیان', 'green'], ['route', 'گزارش مسیر', 'عملکرد و پوشش ویزیت', 'blue'],
    ['hr', 'گزارش کارکنان', 'حضور، حقوق، عملکرد', 'pink'], ['chart', 'گزارش عملکرد', 'بازاریاب و مامور پخش', 'amber'],
  ];
  return (
    <>
      <PageHead title="مرکز گزارشات" sub="فیلتر: تاریخ، شعبه، انبار، بازاریاب، مشتری، منطقه، کالا — خروجی PDF / Excel / CSV" />
      <div className="filter-bar">
        <select><option>بازه: ماه جاری</option></select><select><option>همه شعب</option></select>
        <select><option>همه بازاریاب‌ها</option></select><select><option>همه مناطق</option></select>
        <button className="btn btn-ghost btn-sm" onClick={() => window.print()}>خروجی PDF</button>
        <button className="btn btn-ghost btn-sm" onClick={() => financeApi.downloadCsv().catch(() => {})}>خروجی CSV حسابداری</button>
      </div>
      <div className="grid cols-3">
        {cards.map(([ic, t, d, tint]) => (
          <Card key={t} style={{ cursor: 'pointer' }}>
            <div className="flex">
              <div className="kpi-icon" style={{ background: 'rgba(47,123,255,0.12)', color: 'var(--brand-400)' }}><Icon name={ic} size={22} /></div>
              <div><b>{t}</b><div className="muted">{d}</div></div>
            </div>
          </Card>
        ))}
      </div>
    </>
  );
}

/* ---------- تنظیمات ---------- */
export function SettingsPage() {
  const items = [
    ['company', 'شرکت و شعبات', 'اطلاعات شرکت، شعبه‌ها، انبارها و مناطق'],
    ['users', 'کاربران و دسترسی‌ها', 'نقش‌ها، Permission-Based Access'],
    ['invoice', 'تنظیمات فاکتور', 'الگوی شماره‌گذاری، مالیات، چاپ'],
    ['warehouse', 'تنظیمات انبار', 'نقطه سفارش، رزرو، انبارگردانی'],
    ['pin', 'تنظیمات GPS', 'ردیابی، فاصله مجاز، Geofence'],
    ['bell', 'اعلان‌ها', 'Push، پیامک، قواعد هشدار'],
    ['shield', 'امنیت', 'نشست‌ها، رمز، Rate Limiting'],
    ['sync', 'پشتیبان‌گیری', 'Backup، Restore، Export'],
  ];
  return (
    <>
      <PageHead title="تنظیمات سیستم" sub="پیکربندی کلی شرکت و سیاست‌ها" />
      <div className="grid cols-4">
        {items.map(([ic, t, d]) => (
          <Card key={t} style={{ cursor: 'pointer' }}>
            <div className="flex">
              <div className="kpi-icon" style={{ background: 'rgba(47,123,255,0.12)', color: 'var(--brand-400)' }}><Icon name={ic} size={21} /></div>
              <div><b>{t}</b><div className="muted">{d}</div></div>
            </div>
          </Card>
        ))}
      </div>
    </>
  );
}

/* ---------- اعلان‌ها ---------- */
export function NotificationsPage() {
  const [items, setItems] = useState(notifications);
  useEffect(() => { platformApi.notifications().then((data) => setItems(data.map((x) => ({ title: x.title, time: x.created_at?.replace('T', ' ').slice(0, 16), icon: x.notification_type === 'warning' ? 'alert' : 'bell', tint: x.notification_type === 'success' ? 'green' : 'blue' })))).catch(() => {}); }, []);
  return (
    <>
      <PageHead title="مرکز اعلان‌ها" sub="Push + داخل برنامه" />
      <Card>
        <div className="timeline">
          {items.map((n, i) => <TlItem key={i} {...n} />)}
        </div>
      </Card>
    </>
  );
}

/* ---------- نقشه زنده ---------- */
export function LiveMapPage() {
  return (
    <>
      <PageHead title="نقشه مدیریتی زنده" sub="بازاریاب‌ها، ماموران، مشتریان، انبارها، خودروها" />
      <Card>
        <MockMap height={480} pins={[
          { x: 12, y: 55, label: 'امیر ح. (در مشتری)', color: '#4ade80' },
          { x: 28, y: 35, label: 'رضا ع.', color: '#4ade80' },
          { x: 45, y: 62, label: 'سارا ک.', color: '#fbbf24' },
          { x: 60, y: 28, label: 'مامور: کامران', color: '#38bdf8' },
          { x: 74, y: 50, label: 'مشتریان', color: '#f87171' },
          { x: 88, y: 32, label: 'انبار مرکزی', color: '#a78bfa' },
        ]} />
      </Card>
    </>
  );
}

/* ---------- کاربران و نقش‌ها ---------- */
export function UsersPage() {
  return (
    <>
      <PageHead title="کاربران و نقش‌ها" sub="RBAC + Permission-Based"
        actions={<button className="btn btn-primary btn-sm"><Icon name="plus" size={15} /> کاربر جدید</button>} />
      <div className="grid cols-3" style={{ marginBottom: 16 }}>
        {[
          ['مدیر کل', '۱ کاربر', 'دسترسی کامل', 'blue'], ['مدیر فروش', '۲ کاربر', 'فروش، بازاریاب، تارگت', 'teal'],
          ['مدیر انبار', '۲ کاربر', 'موجودی، ورود/خروج', 'violet'], ['بازاریاب', '۱۲ کاربر', 'مسیر، سفارش، فاکتور', 'amber'],
          ['مامور پخش', '۴ کاربر', 'تحویل، دریافت', 'orange'], ['حسابدار', '۳ کاربر', 'اسناد، چک، صندوق', 'green'],
        ].map(([t, c, d, tint]) => (
          <Card key={t}><div className="flex"><div className="kpi-icon" style={{ background: 'rgba(47,123,255,0.12)', color: 'var(--brand-400)' }}><Icon name="shield" size={20} /></div>
          <div><b>{t}</b> <span className="muted">· {c}</span><div className="muted">{d}</div></div></div></Card>
        ))}
      </div>
      <Card title="ماتریس دسترسی — نقش: بازاریاب">
        <Table
          columns={[{ key: 'm', label: 'ماژول' }, { key: 'v', label: 'مشاهده' }, { key: 'c', label: 'ایجاد' }, { key: 'e', label: 'ویرایش' }, { key: 'd', label: 'حذف' }]}
          rows={[
            { m: 'مشتریان', v: '✓', c: '✓', e: '✓', d: '—' }, { m: 'سفارش / فاکتور', v: '✓', c: '✓', e: 'با تأیید', d: '—' },
            { m: 'موجودی (فقط مشاهده)', v: '✓', c: '—', e: '—', d: '—' }, { m: 'دریافت وجه', v: '✓', c: '✓', e: '—', d: '—' },
            { m: 'حسابداری', v: '—', c: '—', e: '—', d: '—' },
          ]}
        />
      </Card>
    </>
  );
}

/* ---------- تأییدها ---------- */
export function ApprovalsPage() {
  return (
    <>
      <PageHead title="درخواست‌های تأیید" sub="Approval Workflow — عملیات حساس" />
      <Card>
        <Table
          columns={[{ key: 't', label: 'نوع' }, { key: 'by', label: 'درخواست‌دهنده' }, { key: 'd', label: 'شرح' }, { key: 'time', label: 'زمان' }, { key: 'act', label: 'اقدام' }]}
          rows={[
            { t: 'تخفیف بیش از حد مجاز', by: 'امیر حسینی', d: 'فاکتور #۱۲۵۱ — تخفیف ۱۸٪ (حد مجاز ۱۰٪)', time: '۱۰:۴۰' },
            { t: 'فروش اعتباری بالای سقف', by: 'رضا عزیزی', d: 'مارکت امید — بدهی ۲۱۰M از سقف ۱۵۰M', time: '۰۹:۵۵' },
            { t: 'حذف فاکتور', by: 'اپراتور', d: 'فاکتور #۱۲۴۴ — دلیل: ثبت اشتباه', time: '۰۹:۱۰' },
            { t: 'اصلاح موجودی', by: 'مهدی اکبری', d: 'کالای AB-1003 — کسری شمارش ۱۵ عدد', time: '۰۸:۳۰' },
          ]}
          render={(k, r) => k === 'act' ? <div className="flex"><button className="btn btn-primary btn-sm">تأیید</button><button className="btn btn-danger btn-sm">رد</button></div> : r[k]}
        />
      </Card>
    </>
  );
}

/* ---------- Audit Log ---------- */
export function AuditPage() {
  const [items, setItems] = useState(auditLogs);
  useEffect(() => { platformApi.auditLogs().then((data) => setItems(data.map((x) => ({ user: x.actor_name || 'سیستم', action: x.action, target: x.object_repr, oldv: '', newv: x.changes || '', time: x.timestamp?.replace('T', ' ').slice(0, 16), ip: x.remote_addr || '—' })))).catch(() => {}); }, []);
  return (
    <>
      <PageHead title="Audit Log" sub="تمام عملیات حساس — غیرقابل حذف" />
      <div className="filter-bar">
        <input placeholder="جستجو: کاربر، شماره سند…" /><select><option>همه عملیات</option></select><select><option>امروز</option></select>
      </div>
      <Card>
        <Table
          columns={[{ key: 'user', label: 'کاربر' }, { key: 'action', label: 'عملیات' }, { key: 'target', label: 'هدف' }, { key: 'oldv', label: 'مقدار قبلی' }, { key: 'newv', label: 'مقدار جدید' }, { key: 'time', label: 'زمان' }, { key: 'ip', label: 'IP / دستگاه' }]}
          rows={items}
        />
      </Card>
    </>
  );
}

/* ---------- صفحه عمومی ساده برای سایر ماژول‌ها ---------- */
export function PlaceholderPage({ title, sub }) {
  return (
    <>
      <PageHead title={title} sub={sub} />
      <Card><EmptyState title={`ماژول «${title}»`} desc="برای این مسیر هنوز رکوردی برای نمایش وجود ندارد." /></Card>
    </>
  );
}

export function ApiResourcePage({ title, sub, endpoint }) {
  const [rows, setRows] = useState([]); const [loading, setLoading] = useState(true); const [error, setError] = useState(''); const [json, setJson] = useState('{}'); const [saving, setSaving] = useState(false); const [showForm, setShowForm] = useState(false);
  const load = () => { setLoading(true); fetchResource(endpoint).then((items) => setRows(items.map(flattenRow))).catch((e) => setError(e.message)).finally(() => setLoading(false)); };
  const save = async () => { setSaving(true); setError(''); try { await createResource(endpoint, JSON.parse(json)); setJson('{}'); setShowForm(false); load(); } catch (e) { setError(e.message || 'JSON نامعتبر است'); } finally { setSaving(false); } };
  useEffect(load, [endpoint]);
  const columns = rows.length ? Object.keys(rows[0]).map((key) => ({ key, label: key })) : [{ key: 'empty', label: 'وضعیت' }];
  return <><PageHead title={title} sub={`${sub} — متصل به API واقعی`} actions={<><button className="btn btn-primary btn-sm" onClick={() => setShowForm(!showForm)}><Icon name="plus" size={15} /> ثبت رکورد</button><button className="btn btn-ghost btn-sm" onClick={load}>به‌روزرسانی</button></>} />{showForm && <Card title="ثبت رکورد جدید" sub="Payload JSON مطابق فیلدهای API"><textarea value={json} onChange={(e) => setJson(e.target.value)} rows={6} dir="ltr" style={{ width: '100%', fontFamily: 'monospace', marginBottom: 10 }} /><button className="btn btn-primary" onClick={save} disabled={saving}>{saving ? 'در حال ثبت…' : 'ثبت در دیتابیس'}</button></Card>}{loading && <div className="muted">در حال دریافت داده‌های واقعی…</div>}{error && <div className="badge" style={{ color: 'var(--amber-400)' }}>API: {error}</div>}<Card><Table columns={columns} rows={rows.length ? rows : [{ empty: error ? 'داده‌ای دریافت نشد' : 'رکوردی ثبت نشده است' }]} render={(k, r) => String(r[k] ?? '—')} /></Card></>;
}
