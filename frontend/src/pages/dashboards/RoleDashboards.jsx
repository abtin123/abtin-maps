import React from 'react';
import { Card, Kpi, PageHead, MockMap, TlItem, Table, StatusBadge } from '../../components/ui.jsx';
import { AreaChart, ProgressList, BarChart } from '../../components/Charts.jsx';
import Icon from '../../components/Icon.jsx';
import { salesTrend, invoices, routeStops, mapPins, employees, deliveries, checks, reps } from '../../data/mock.js';

/* ============ مدیر شرکت ============ */
export function CompanyManagerDashboard() {
  return (
    <>
      <PageHead title="داشبورد مدیر شرکت" sub="شعبه مرکزی — نمای کلی عملیات امروز" />
      <div className="grid cols-4" style={{ marginBottom: 16 }}>
        <Kpi icon="sales" label="فروش شعبه امروز" value="۹۸,۲۰۰,۰۰۰" delta="۹٪" tint="teal" />
        <Kpi icon="invoice" label="فاکتور در انتظار تأیید" value="۷" delta="۲٪" tint="amber" />
        <Kpi icon="truck" label="مرسوله در مسیر" value="۲۳" delta="۵٪" tint="orange" />
        <Kpi icon="users" label="بازاریاب فعال" value="۱۰ / ۱۲" delta="۸۳٪" tint="blue" />
      </div>
      <div className="grid" style={{ gridTemplateColumns: '3fr 2fr', marginBottom: 16 }}>
        <Card title="روند فروش شعبه"><AreaChart data={salesTrend.data} labels={salesTrend.labels} color="#a78bfa" /></Card>
        <Card title="عملکرد بازاریاب‌ها">
          <ProgressList items={reps.map((r) => ({ label: r.name, value: r.target, color: '#2f7bff' }))} />
        </Card>
      </div>
      <Card title="فاکتورهای نیازمند تأیید" action={<button className="btn btn-primary btn-sm">تأیید گروهی</button>}>
        <Table
          columns={[{ key: 'no', label: 'شماره' }, { key: 'customer', label: 'مشتری' }, { key: 'rep', label: 'بازاریاب' }, { key: 'amount', label: 'مبلغ', num: true }, { key: 'status', label: 'وضعیت' }, { key: 'act', label: 'اقدام' }]}
          rows={invoices.filter((i) => ['PENDING', 'RESERVED'].includes(i.status))}
          render={(k, r) => k === 'status' ? <StatusBadge status={r.status} /> : k === 'act' ? <div className="flex"><button className="btn btn-primary btn-sm">تأیید</button><button className="btn btn-danger btn-sm">رد</button></div> : r[k]}
        />
      </Card>
    </>
  );
}

/* ============ مدیر فروش ============ */
export function SalesManagerDashboard() {
  return (
    <>
      <PageHead title="داشبورد فروش" sub="عملکرد تیم، تارگت‌ها و قیف فروش" actions={<button className="btn btn-primary btn-sm"><Icon name="plus" size={15} /> تعریف تارگت</button>} />
      <div className="grid cols-4" style={{ marginBottom: 16 }}>
        <Kpi icon="sales" label="فروش تیم امروز" value="۱۲۵,۴۳۰,۰۰۰" delta="۱۲٪" tint="teal" />
        <Kpi icon="target" label="تحقق تارگت ماه" value="۷۱٪" delta="۶٪" tint="blue" />
        <Kpi icon="users" label="نرخ تبدیل ویزیت" value="۶۸٪" delta="۳٪" tint="violet" />
        <Kpi icon="customer" label="مشتری جدید این ماه" value="۳۴" delta="۱۸٪" tint="amber" />
      </div>
      <div className="grid cols-2" style={{ marginBottom: 16 }}>
        <Card title="فروش بر اساس بازاریاب">
          <BarChart data={reps.map((r, i) => ({ label: r.name.split(' ')[0], value: [95, 72, 41][i], color: ['#2f7bff', '#2dd4bf', '#a78bfa'][i] }))} />
        </Card>
        <Card title="تحقق تارگت بازاریاب‌ها">
          <ProgressList items={reps.map((r) => ({ label: `${r.name} — ${r.sales} ریال`, value: r.target }))} />
        </Card>
      </div>
      <Card title="عملکرد تیم امروز">
        <Table
          columns={[{ key: 'name', label: 'بازاریاب' }, { key: 'route', label: 'مسیر' }, { key: 'visits', label: 'ویزیت', num: true }, { key: 'orders', label: 'سفارش', num: true }, { key: 'sales', label: 'فروش (ریال)', num: true }, { key: 'target', label: 'تحقق تارگت' }]}
          rows={reps}
          render={(k, r) => k === 'target' ? <div className="progress" style={{ width: 110 }}><div style={{ width: `${r.target}%`, background: 'var(--brand-500)' }} /></div> : r[k]}
        />
      </Card>
    </>
  );
}

/* ============ مدیر انبار ============ */
export function WarehouseManagerDashboard() {
  return (
    <>
      <PageHead title="داشبورد انبار" sub="انبار مرکزی — موجودی لحظه‌ای و عملیات" />
      <div className="grid cols-4" style={{ marginBottom: 16 }}>
        <Kpi icon="warehouse" label="ارزش موجودی" value="۲,۴۰۰,۰۰۰,۰۰۰" delta="۵٪" tint="violet" />
        <Kpi icon="clock" label="اقلام رزرو شده" value="۱,۷۴۰" delta="۱۲٪" tint="blue" />
        <Kpi icon="box" label="کالای رو به اتمام" value="۸" delta="۲" dir="down" tint="amber" />
        <Kpi icon="sync" label="سفارش در صف آماده‌سازی" value="۱۴" delta="۷٪" tint="orange" />
      </div>
      <div className="grid cols-2" style={{ marginBottom: 16 }}>
        <Card title="ساختار موجودی">
          <ProgressList items={[
            { label: 'موجودی آزاد (قابل فروش)', value: 82, color: '#4ade80' },
            { label: 'رزرو شده', value: 12, color: '#38bdf8' },
            { label: 'در مسیر (تحویل نشده)', value: 4, color: '#fbbf24' },
            { label: 'رو به اتمام / تمام‌شده', value: 2, color: '#f87171' },
          ]} />
        </Card>
        <Card title="گردش کالای ۷ روز اخیر">
          <AreaChart data={[120, 180, 150, 240, 210, 290, 260]} labels={['ش', 'ی', 'د', 'س', 'چ', 'پ', 'ج']} color="#2dd4bf" height={200} />
        </Card>
      </div>
      <Card title="سفارش‌های در انتظار آماده‌سازی" action={<button className="btn btn-primary btn-sm">شروع آماده‌سازی</button>}>
        <Table
          columns={[{ key: 'no', label: 'فاکتور' }, { key: 'customer', label: 'مشتری' }, { key: 'amount', label: 'اقلام', num: true }, { key: 'status', label: 'وضعیت' }]}
          rows={invoices.filter((i) => ['CONFIRMED', 'WAREHOUSE_PENDING', 'READY_FOR_DELIVERY'].includes(i.status))}
          render={(k, r) => k === 'status' ? <StatusBadge status={r.status} /> : k === 'amount' ? '۱۲ قلم' : r[k]}
        />
      </Card>
    </>
  );
}

/* ============ بازاریاب (موبایل) ============ */
export function SalesRepDashboard() {
  return (
    <>
      <PageHead title="میز کار بازاریاب" sub="امیر حسینی — مسیر ۱۲، منطقه غرب"
        actions={<button className="btn btn-primary"><Icon name="pin" size={16} /> شروع مسیر</button>} />
      <div className="grid cols-4" style={{ marginBottom: 16 }}>
        <Kpi icon="sales" label="فروش امروز" value="۲,۴۵۰,۰۰۰" delta="۱۲٪" tint="teal" />
        <Kpi icon="customer" label="ویزیت موفق" value="۹ / ۱۲" delta="۷۵٪" tint="blue" />
        <Kpi icon="wallet" label="وصولی امروز" value="۱,۱۰۰,۰۰۰" delta="۸٪" tint="green" />
        <Kpi icon="target" label="تحقق تارگت ماه" value="۸۲٪" delta="۵٪" tint="violet" />
      </div>
      <div className="grid" style={{ gridTemplateColumns: '3fr 2fr', marginBottom: 16 }}>
        <Card title="مسیر امروز" sub="۵ مشتری باقی‌مانده" action={<button className="btn btn-ghost btn-sm">نقشه</button>}>
          <MockMap pins={mapPins} height={300} />
        </Card>
        <Card title="ایستگاه‌های مسیر ۱۲">
          <div className="timeline">
            {routeStops.map((s, i) => (
              <TlItem key={i}
                icon={s.state === 'done' ? 'check' : s.state === 'current' ? 'pin' : s.state === 'cancel' ? 'logout' : 'clock'}
                tint={s.state === 'done' ? 'green' : s.state === 'current' ? 'amber' : s.state === 'cancel' ? 'rose' : 'blue'}
                title={s.name}
                desc={s.state === 'done' ? `فروش: ${s.sale} ریال` : s.state === 'current' ? 'در حال ویزیت…' : s.state === 'cancel' ? 'لغو شده' : 'در انتظار'}
                time={s.time} />
            ))}
          </div>
        </Card>
      </div>
      <Card title="اقدام سریع">
        <div className="grid cols-4">
          {[['plus', 'ثبت سفارش جدید', 'blue'], ['wallet', 'دریافت وجه', 'green'], ['pin', 'ثبت ورود به مشتری', 'amber'], ['camera', 'ثبت عکس / سند', 'violet']].map(([ic, t, tint]) => (
            <button key={t} className="btn btn-ghost" style={{ justifyContent: 'center', padding: 16, flexDirection: 'column', gap: 8 }}>
              <Icon name={ic} size={22} />{t}
            </button>
          ))}
        </div>
      </Card>
    </>
  );
}

/* ============ مامور پخش (موبایل) ============ */
export function DriverDashboard() {
  return (
    <>
      <PageHead title="میز کار مامور پخش" sub="کامران صالحی — مأموریت ۴۲، خودرو ۲۴ب۳۵۸"
        actions={<button className="btn btn-primary"><Icon name="route" size={16} /> شروع مأموریت</button>} />
      <div className="grid cols-4" style={{ marginBottom: 16 }}>
        <Kpi icon="truck" label="مرسوله امروز" value="۱۴" tint="blue" />
        <Kpi icon="check" label="تحویل شده" value="۸" delta="۵۷٪" tint="green" />
        <Kpi icon="clock" label="باقی‌مانده" value="۶" tint="amber" />
        <Kpi icon="wallet" label="وجه دریافتی" value="۱,۸۵۰,۰۰۰" delta="۲۱٪" tint="teal" />
      </div>
      <div className="grid" style={{ gridTemplateColumns: '2fr 3fr' }}>
        <Card title="نقشه مقصدها" sub="مقصد بعدی: مارکت امید">
          <MockMap pins={mapPins} height={320} />
        </Card>
        <Card title="لیست تحویل امروز" sub="به ترتیب مسیر بهینه">
          <Table
            columns={[{ key: 'invoice', label: 'فاکتور' }, { key: 'customer', label: 'مشتری' }, { key: 'address', label: 'آدرس' }, { key: 'amount', label: 'مبلغ', num: true }, { key: 'status', label: 'تحویل' }, { key: 'pay', label: 'پرداخت' }, { key: 'act', label: '' }]}
            rows={deliveries}
            render={(k, r) =>
              k === 'status' || k === 'pay' ? <StatusBadge status={r[k]} /> :
              k === 'act' ? <button className="btn btn-primary btn-sm"><Icon name="pin" size={14} /> مسیریابی</button> : r[k]}
          />
        </Card>
      </div>
    </>
  );
}

/* ============ حسابدار / مدیر مالی ============ */
export function AccountantDashboard({ manager = false }) {
  return (
    <>
      <PageHead title={manager ? 'داشبورد مدیر مالی' : 'داشبورد حسابداری'} sub="نقدینگی، اسناد و چک‌ها" />
      <div className="grid cols-4" style={{ marginBottom: 16 }}>
        <Kpi icon="wallet" label="دریافتی امروز" value="۳۳۰,۰۰۰,۰۰۰" delta="۱۵٪" tint="green" />
        <Kpi icon="cash" label="پرداختی امروز" value="۱۴۵,۰۰۰,۰۰۰" delta="۴٪" dir="down" tint="rose" />
        <Kpi icon="receipt" label="چک در انتظار وصول" value="۲,۷۵۰,۰۰۰,۰۰۰" delta="۷" tint="amber" />
        <Kpi icon="chart" label={manager ? 'جریان نقد خالص' : 'مانده صندوق'} value="۱۸۵,۰۰۰,۰۰۰" delta="۹٪" tint="blue" />
      </div>
      <div className="grid cols-2" style={{ marginBottom: 16 }}>
        <Card title="جریان نقدینگی ۳۰ روز"><AreaChart data={salesTrend.data} labels={salesTrend.labels} color="#4ade80" /></Card>
        <Card title="چک‌های نزدیک سررسید">
          <Table
            columns={[{ key: 'no', label: 'شماره چک' }, { key: 'bank', label: 'بانک' }, { key: 'amount', label: 'مبلغ', num: true }, { key: 'due', label: 'سررسید' }, { key: 'status', label: 'وضعیت' }]}
            rows={checks}
            render={(k, r) => k === 'status' ? <StatusBadge status={r.status} /> : r[k]}
          />
        </Card>
      </div>
      <Card title="آخرین اسناد خودکار" sub="ایجادشده از فروش و دریافت">
        <Table
          columns={[{ key: 'no', label: 'سند' }, { key: 'customer', label: 'شرح' }, { key: 'amount', label: 'بدهکار', num: true }, { key: 'rep', label: 'بستانکار' }, { key: 'status', label: 'وضعیت' }]}
          rows={invoices.slice(0, 4)}
          render={(k, r) => k === 'status' ? <StatusBadge status="CONFIRMED" /> : k === 'customer' ? `فروش — فاکتور ${r.no}` : k === 'rep' ? 'حساب فروش' : r[k]}
        />
      </Card>
    </>
  );
}

/* ============ HR ============ */
export function HRDashboard() {
  return (
    <>
      <PageHead title="داشبورد منابع انسانی" sub="حضور و غیاب، مرخصی و حقوق" />
      <div className="grid cols-4" style={{ marginBottom: 16 }}>
        <Kpi icon="hr" label="حاضر امروز" value="۴۲ / ۴۵" delta="۹۳٪" tint="green" />
        <Kpi icon="clock" label="تأخیر امروز" value="۳" dir="down" delta="۱" tint="amber" />
        <Kpi icon="receipt" label="درخواست مرخصی" value="۵" tint="violet" />
        <Kpi icon="cash" label="حقوق این ماه" value="۱,۹۸۰,۰۰۰,۰۰۰" delta="۲٪" tint="blue" />
      </div>
      <Card title="حضور و غیاب امروز">
        <Table
          columns={[{ key: 'name', label: 'کارمند' }, { key: 'role', label: 'سمت' }, { key: 'branch', label: 'شعبه' }, { key: 'checkin', label: 'ساعت ورود' }, { key: 'status', label: 'وضعیت' }]}
          rows={employees}
          render={(k, r) => k === 'status' ? <StatusBadge status={r.status === 'حاضر' ? 'DELIVERED' : 'CANCELLED'} /> : r[k]}
        />
      </Card>
    </>
  );
}

/* ============ مشتری ============ */
export function CustomerDashboard() {
  return (
    <>
      <PageHead title="فروشگاه آریا" sub="خوش آمدید — پیگیری سفارش‌ها و حساب" />
      <div className="grid cols-4" style={{ marginBottom: 16 }}>
        <Kpi icon="invoice" label="سفارش در راه" value="۲" tint="orange" />
        <Kpi icon="wallet" label="مانده حساب" value="۱۲۰,۰۰۰,۰۰۰" dir="down" tint="rose" />
        <Kpi icon="shield" label="سقف اعتبار" value="۵۰۰,۰۰۰,۰۰۰" tint="blue" />
        <Kpi icon="sales" label="خرید این ماه" value="۲,۳۵۰,۰۰۰,۰۰۰" delta="۱۴٪" tint="teal" />
      </div>
      <Card title="سفارش‌های اخیر">
        <Table
          columns={[{ key: 'no', label: 'شماره' }, { key: 'amount', label: 'مبلغ', num: true }, { key: 'date', label: 'تاریخ' }, { key: 'status', label: 'وضعیت' }]}
          rows={invoices.slice(0, 4)}
          render={(k, r) => k === 'status' ? <StatusBadge status={r.status} /> : r[k]}
        />
      </Card>
    </>
  );
}

/* ============ اپراتور / سرپرست / مدیر سیستم / انباردار ============ */
export function GenericDashboard({ title, sub, kpis, children }) {
  return (
    <>
      <PageHead title={title} sub={sub} />
      {kpis && <div className="grid cols-4" style={{ marginBottom: 16 }}>{kpis.map((k, i) => <Kpi key={i} {...k} />)}</div>}
      {children}
    </>
  );
}
