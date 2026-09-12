import React, { useEffect, useState } from 'react';
import { Card, Kpi, PageHead, TlItem, Table, StatusBadge } from '../../components/ui.jsx';
import { AreaChart, DonutChart, BarChart, ProgressList } from '../../components/Charts.jsx';
import Icon from '../../components/Icon.jsx';
import { salesTrend, salesByProduct, salesByRegion, monthlyCompare, invoices, activities, mapPins } from '../../data/mock.js';
import { deliveryApi } from '../../api/delivery.js';
import RealMap from '../../components/RealMap.jsx';

export default function SuperAdminDashboard() {
  const [livePoints, setLivePoints] = useState([]);
  useEffect(() => { deliveryApi.visits().then((items) => setLivePoints(items.map((v) => ({ id: v.id, lat: v.customer_latitude, lng: v.customer_longitude, label: v.customer_name, status: v.status, color: v.status === 'completed' ? '#4ade80' : '#fbbf24' })))).catch(() => {}); }, []);
  return (
    <>
      {/* Hero */}
      <div className="hero" style={{ marginBottom: 18 }}>
        <div className="hero-inner">
          <h2>صبح بخیر، علی محمدی 👋</h2>
          <p>امروز یک روز عالی برای رشد و پیشرفت است… ۸۵ فاکتور، ۱۲ بازاریاب فعال و ۴ مامور پخش در مسیر هستند.</p>
          <div className="flex mt wrap">
            <span className="badge" style={{ background: 'rgba(251,191,36,0.14)', color: 'var(--amber-400)' }}>☀ ۲۶° تهران</span>
            <span className="badge" style={{ background: 'rgba(47,123,255,0.14)', color: 'var(--brand-400)' }}>دوشنبه ۱۴۰۵/۰۶/۲۱</span>
          </div>
        </div>
        <div className="hero-art">
          <RealMap points={livePoints.slice(0, 4)} height={210} title="نقشه زنده" />
        </div>
      </div>

      {/* KPI row 1 */}
      <div className="grid cols-6" style={{ marginBottom: 16 }}>
        <Kpi icon="sales" label="فروش امروز" value="۱۲۵,۴۳۰,۰۰۰" delta="۱۲٪" tint="teal" />
        <Kpi icon="invoice" label="فاکتورهای امروز" value="۸۵" delta="۸٪" tint="blue" />
        <Kpi icon="warehouse" label="موجودی انبار" value="۲,۴۰۰,۰۰۰,۰۰۰" delta="۵٪" tint="violet" />
        <Kpi icon="users" label="مشتریان فعال" value="۱,۲۵۰" delta="۳٪" tint="amber" />
        <Kpi icon="wallet" label="بدهی مشتریان" value="۸۵۰,۰۰۰,۰۰۰" delta="۶٪" dir="down" tint="rose" />
        <Kpi icon="cash" label="دریافتی امروز" value="۳۳۰,۰۰۰,۰۰۰" delta="۱۵٪" tint="green" />
      </div>

      <div className="grid" style={{ gridTemplateColumns: '3fr 2fr', marginBottom: 16 }}>
        <Card title="روند فروش" sub="ماه جاری" action={<select><option>ماه جاری</option><option>هفته جاری</option><option>سال جاری</option></select>}>
          <AreaChart data={salesTrend.data} labels={salesTrend.labels} color="#2f7bff" />
        </Card>
        <Card title="فروش بر اساس محصول">
          <div className="flex" style={{ alignItems: 'center' }}>
            <DonutChart segments={salesByProduct} size={170} centerLabel="کل فروش" centerValue="۱۲۵M" />
            <div className="legend-list" style={{ flex: 1 }}>
              {salesByProduct.map((s) => (
                <div className="legend-item" key={s.label}><i style={{ background: s.color }} />{s.label}<span className="lg-val num">{s.value}٪</span></div>
              ))}
            </div>
          </div>
        </Card>
      </div>

      <div className="grid cols-2" style={{ marginBottom: 16 }}>
        <Card title="مقایسه فروش ماهانه" sub="میلیون ریال">
          <BarChart data={monthlyCompare} color="#2dd4bf" />
        </Card>
        <Card title="فروش بر اساس منطقه">
          <ProgressList items={salesByRegion} />
          <div className="mt">
            <div className="card-title" style={{ marginBottom: 8 }}>تحقق تارگت ماهانه <small>شرکت</small></div>
            <div className="flex between" style={{ fontSize: 12, marginBottom: 5 }}>
              <span className="muted">۲,۸۵۰M از ۴,۰۰۰M ریال</span><b className="num">۷۱٪</b>
            </div>
            <div className="progress"><div style={{ width: '71%', background: 'linear-gradient(90deg,#2f7bff,#2dd4bf)' }} /></div>
          </div>
        </Card>
      </div>

      {/* Live map + activities */}
      <div className="grid" style={{ gridTemplateColumns: '3fr 2fr', marginBottom: 16 }}>
        <Card title="نقشه زنده عملیات" sub="۱۲ بازاریاب · ۴ مامور پخش" action={<button className="btn btn-ghost btn-sm">نمایش کامل</button>}>
          <RealMap points={livePoints} height={330} title="نقشه زنده عملیات" />
          <div className="map-legend">
            <span><i style={{ background: '#4ade80' }} />بازاریاب فعال ۱۲</span>
            <span><i style={{ background: '#fbbf24' }} />در مشتری ۸</span>
            <span><i style={{ background: '#f87171' }} />مشتری ۴۴</span>
            <span><i style={{ background: '#38bdf8' }} />مامور پخش ۴</span>
            <span><i style={{ background: '#a78bfa' }} />انبار ۷</span>
          </div>
        </Card>
        <Card title="آخرین فعالیت‌ها" action={<button className="btn btn-ghost btn-sm">مشاهده همه</button>}>
          <div className="timeline">
            {activities.map((a, i) => <TlItem key={i} {...a} />)}
          </div>
        </Card>
      </div>

      {/* Latest invoices */}
      <Card title="آخرین فاکتورها" sub="وضعیت لحظه‌ای" action={<button className="btn btn-primary btn-sm"><Icon name="plus" size={15} /> فاکتور جدید</button>}>
        <Table
          columns={[
            { key: 'no', label: 'شماره' }, { key: 'customer', label: 'مشتری' }, { key: 'rep', label: 'بازاریاب' },
            { key: 'amount', label: 'مبلغ (ریال)', num: true }, { key: 'date', label: 'تاریخ' }, { key: 'status', label: 'وضعیت' },
          ]}
          rows={invoices}
          render={(k, r) => (k === 'status' ? <StatusBadge status={r.status} /> : r[k])}
        />
      </Card>

      {/* Financial strip */}
      <div className="grid cols-4 mt">
        <Kpi icon="chart" label="سود ناخالص ماه" value="۴۸۵,۰۰۰,۰۰۰" delta="۹٪" tint="green" />
        <Kpi icon="receipt" label="چک‌های سررسید نزدیک" value="۷" delta="۲" tint="amber" />
        <Kpi icon="truck" label="مسیرهای فعال امروز" value="۱۶" delta="۴٪" tint="orange" />
        <Kpi icon="hr" label="کارکنان حاضر" value="۴۲ / ۴۵" delta="۹۳٪" tint="pink" />
      </div>
    </>
  );
}
