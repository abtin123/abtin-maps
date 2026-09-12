import React from 'react';
import { Routes, Route, Navigate, useParams } from 'react-router-dom';
import Login from './pages/Login.jsx';
import { AppShell } from './components/Layout.jsx';
import SuperAdminDashboard from './pages/dashboards/SuperAdminDashboard.jsx';
import {
  CompanyManagerDashboard, SalesManagerDashboard, WarehouseManagerDashboard,
  SalesRepDashboard, DriverDashboard, AccountantDashboard, HRDashboard,
  CustomerDashboard, GenericDashboard,
} from './pages/dashboards/RoleDashboards.jsx';
import {
  InvoicesPage, ProductsPage, CustomersPage, InventoryPage, RoutesPage,
  AccountingPage, ChecksPage, EmployeesPage, ReportsPage, SettingsPage,
  NotificationsPage, LiveMapPage, UsersPage, ApprovalsPage, AuditPage, PlaceholderPage, ApiResourcePage,
} from './pages/shared/ModulePages.jsx';
import { NewOrderPage, MyRoutePage, DeliveryListPage, OfflinePage, SimpleListPage } from './pages/roles/FieldPages.jsx';
import { ROLES } from './data/roles.js';
import { StatusBadge, Card, PageHead, Table } from './components/ui.jsx';
import { invoices, reps } from './data/mock.js';
import LiveEntityPage from './pages/shared/LiveEntityPage.jsx';

function DashboardRouter({ role }) {
  switch (role) {
    case 'super_admin': return <SuperAdminDashboard />;
    case 'company_manager': return <CompanyManagerDashboard />;
    case 'sales_manager': return <SalesManagerDashboard />;
    case 'warehouse_manager': return <WarehouseManagerDashboard />;
    case 'warehouse_keeper':
      return <GenericDashboard title="داشبورد انباردار" sub="سفارش‌های در صف آماده‌سازی"
        kpis={[
          { icon: 'box', label: 'در صف آماده‌سازی', value: '۱۴', tint: 'violet' },
          { icon: 'check', label: 'آماده‌شده امروز', value: '۲۲', delta: '۸٪', tint: 'green' },
          { icon: 'truck', label: 'تحویل به مامور', value: '۱۸', tint: 'orange' },
          { icon: 'clock', label: 'شمارش در انتظار', value: '۳', tint: 'amber' },
        ]}>
        <Card title="سفارش‌های در صف">
          <Table columns={[{ key: 'no', label: 'فاکتور' }, { key: 'customer', label: 'مشتری' }, { key: 'status', label: 'وضعیت' }]}
            rows={invoices.slice(1, 5)} render={(k, r) => k === 'status' ? <StatusBadge status={r.status} /> : r[k]} />
        </Card>
      </GenericDashboard>;
    case 'sales_rep': return <SalesRepDashboard />;
    case 'rep_supervisor':
      return <GenericDashboard title="داشبورد سرپرست بازاریاب‌ها" sub="نظارت زنده بر تیم"
        kpis={[
          { icon: 'users', label: 'بازاریاب فعال', value: '۱۲ / ۱۴', tint: 'blue' },
          { icon: 'pin', label: 'ویزیت امروز', value: '۸۶', delta: '۹٪', tint: 'teal' },
          { icon: 'invoice', label: 'سفارش امروز', value: '۶۱', delta: '۵٪', tint: 'violet' },
          { icon: 'sales', label: 'فروش تیم', value: '۸,۲۵۰,۰۰۰,۰۰۰', delta: '۱۱٪', tint: 'green' },
        ]}>
        <Card title="وضعیت لحظه‌ای تیم">
          <Table columns={[{ key: 'name', label: 'بازاریاب' }, { key: 'route', label: 'مسیر' }, { key: 'visits', label: 'ویزیت', num: true }, { key: 'orders', label: 'سفارش', num: true }, { key: 'sales', label: 'فروش', num: true }]}
            rows={reps} />
        </Card>
      </GenericDashboard>;
    case 'driver': return <DriverDashboard />;
    case 'accountant': return <AccountantDashboard />;
    case 'finance_manager': return <AccountantDashboard manager />;
    case 'hr': return <HRDashboard />;
    case 'operator':
      return <GenericDashboard title="میز کار اپراتور" sub="ثبت سفارش تلفنی و پشتیبانی"
        kpis={[
          { icon: 'invoice', label: 'سفارش ثبت‌شده امروز', value: '۲۴', tint: 'blue' },
          { icon: 'customer', label: 'تماس امروز', value: '۴۸', tint: 'teal' },
          { icon: 'bell', label: 'اعلان خوانده‌نشده', value: '۷', tint: 'amber' },
          { icon: 'clock', label: 'در انتظار تأیید', value: '۵', tint: 'violet' },
        ]} />;
    case 'customer': return <CustomerDashboard />;
    case 'system_admin':
      return <GenericDashboard title="سلامت سیستم" sub="مدیریت فنی، نشست‌ها و پشتیبان‌گیری"
        kpis={[
          { icon: 'shield', label: 'وضعیت سرویس', value: 'پایدار', tint: 'green' },
          { icon: 'users', label: 'نشست فعال', value: '۳۸', tint: 'blue' },
          { icon: 'sync', label: 'آخرین بکاپ', value: '۰۳:۰۰', tint: 'violet' },
          { icon: 'audit', label: 'رویداد امروز', value: '۱,۲۴۸', tint: 'amber' },
        ]} />;
    default: return <SuperAdminDashboard />;
  }
}

function ModuleRouter({ role, page }) {
  switch (page) {
    case 'dashboard': return <DashboardRouter role={role} />;
    case 'invoices': case 'my-invoices': return <LiveEntityPage title="فاکتورها" sub="چرخه واقعی سفارش و فاکتور" endpoint="/sales/invoices/" />;
    case 'products': case 'catalog': return <LiveEntityPage title="کالاها" sub="کاتالوگ واقعی کالا" endpoint="/inventory/products/" />;
    case 'customers': case 'my-customers': return <LiveEntityPage title="مشتریان" sub="CRM واقعی مشتریان" endpoint="/sales/customers/" />;
    case 'inventory': case 'reservations': case 'stock-card': return <InventoryPage />;
    case 'routes': return <LiveEntityPage title="مسیرهای فروش" sub="مسیرهای واقعی بازاریاب و پخش" endpoint="/delivery/routes/" />;
    case 'accounting': case 'journal': case 'accounts': case 'cash-bank': case 'receivables': case 'payables': return <AccountingPage />;
    case 'checks': return <ChecksPage />;
    case 'employees': case 'hr': case 'attendance': case 'leave': case 'payroll': return <EmployeesPage />;
    case 'reports': case 'my-report': return <ReportsPage />;
    case 'settings': case 'security': case 'backup': case 'profile': return <SettingsPage />;
    case 'notifications': return <NotificationsPage />;
    case 'live': case 'delivery-map': return <LiveMapPage />;
    case 'users': return <UsersPage />;
    case 'approvals': return <ApprovalsPage />;
    case 'audit': return <AuditPage />;
    case 'new-order': return <NewOrderPage />;
    case 'my-route': return <MyRoutePage />;
    case 'delivery-list': case 'deliveries': case 'my-trips': return <DeliveryListPage />;
    case 'offline': return <OfflinePage />;
    case 'my-orders': return <InvoicesPage />;
    case 'my-balance': return <SimpleListPage title="مانده حساب" sub="گردش حساب فروشگاه آریا"
      columns={[{ key: 'no', label: 'سند' }, { key: 'date', label: 'تاریخ' }, { key: 'amount', label: 'مبلغ', num: true }, { key: 'status', label: 'وضعیت' }]}
      rows={invoices.slice(0, 4)} render={(k, r) => k === 'status' ? <StatusBadge status={r.status} /> : r[k]} />;
    case 'company': return <ApiResourcePage title="مدیریت شرکت و شعبات" sub="شرکت، شعبه‌ها، انبارها، مناطق و شهرها" endpoint="/org/companies/" />;
    case 'warehouses': return <ApiResourcePage title="انبارها" sub="تعریف انبار، ظرفیت و تخصیص به شعبه" endpoint="/org/warehouses/" />;
    case 'reps': return <SimpleListPage title="بازاریاب‌ها" sub="عملکرد و تخصیص مسیر"
      columns={[{ key: 'name', label: 'نام' }, { key: 'route', label: 'مسیر' }, { key: 'visits', label: 'ویزیت', num: true }, { key: 'sales', label: 'فروش', num: true }]} rows={reps} />;
    case 'visits': return <ApiResourcePage title="ویزیت‌ها" sub="ورود، خروج و GPS بازاریاب" endpoint="/delivery/visits/" />;
    case 'targets': return <ApiResourcePage title="تارگت فروش" sub="تارگت و درصد تحقق" endpoint="/finance/targets/" />;
    case 'commissions': return <ApiResourcePage title="پورسانت بازاریاب" sub="پورسانت محاسبه‌شده از فروش و وصول" endpoint="/finance/commissions/" />;
    case 'campaigns': return <ApiResourcePage title="کمپین‌های فروش" sub="کمپین‌های فعال فروش" endpoint="/sales/campaigns/" />;
    case 'stock-entry': return <ApiResourcePage title="ورود کالا" sub="رسید انبار و افزایش موجودی" endpoint="/inventory/documents/" />;
    case 'stock-exit': return <ApiResourcePage title="خروج کالا" sub="حواله خروج و کاهش موجودی" endpoint="/inventory/documents/" />;
    case 'transfers': return <ApiResourcePage title="انتقال بین انبارها" sub="درخواست، خروج و دریافت" endpoint="/inventory/documents/" />;
    case 'counting': return <ApiResourcePage title="انبارگردانی" sub="شمارش و مغایرت موجودی" endpoint="/inventory/documents/" />;
    case 'purchase': return <ApiResourcePage title="خرید و تأمین‌کنندگان" sub="مدیریت ورودی کالا و اسناد انبار" endpoint="/inventory/documents/" />;
    case 'prepare': return <ApiResourcePage title="آماده‌سازی سفارش" sub="Picking List و اقلام سفارش" endpoint="/sales/invoices/" />;
    case 'returns': return <ApiResourcePage title="برگشت کالا" sub="برگشت از مشتری یا تأمین‌کننده" endpoint="/inventory/documents/" />;
    case 'receive': return <ApiResourcePage title="دریافت وجه" sub="رسیدهای نقدی، کارت، انتقال و چک" endpoint="/finance/receipts/" />;
    case 'expenses': return <ApiResourcePage title="درآمد و هزینه" sub="اسناد مالی و سود و زیان" endpoint="/finance/financial-documents/" />;
    case 'credits': return <ApiResourcePage title="اعتبار مشتریان" sub="فاکتورها و مانده حساب مشتریان" endpoint="/sales/customers/" />;
    default: return <PlaceholderPage title={page} sub="ماژول عملیاتی" />;
  }
}

function RoleApp() {
  const { role, page = 'dashboard' } = useParams();
  if (!ROLES[role]) return <Navigate to="/" replace />;
  return (
    <AppShell role={role}>
      <ModuleRouter role={role} page={page} />
    </AppShell>
  );
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Login />} />
      <Route path="/app/:role" element={<RoleApp />} />
      <Route path="/app/:role/:page" element={<RoleApp />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
