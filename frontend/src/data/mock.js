// داده‌های Preview — در نسخه نهایی از API جنگو تغذیه می‌شود
export const salesTrend = {
  labels: ['۱', '۵', '۱۰', '۱۵', '۲۰', '۲۵', '۳۰'],
  data: [25, 42, 58, 95, 62, 74, 88],
};

export const salesByProduct = [
  { label: 'نوشابه', value: 35, color: '#2dd4bf' },
  { label: 'آب معدنی', value: 25, color: '#38bdf8' },
  { label: 'تنقلات', value: 15, color: '#fb923c' },
  { label: 'مواد غذایی', value: 13, color: '#f472b6' },
  { label: 'سایر', value: 12, color: '#a78bfa' },
];

export const salesByRegion = [
  { label: 'منطقه غرب', value: 78, color: '#2f7bff' },
  { label: 'منطقه مرکز', value: 64, color: '#2dd4bf' },
  { label: 'منطقه شمال', value: 52, color: '#a78bfa' },
  { label: 'منطقه شرق', value: 38, color: '#fb923c' },
  { label: 'منطقه جنوب', value: 24, color: '#f472b6' },
];

export const monthlyCompare = [
  { label: 'فرو', value: 62 }, { label: 'ارد', value: 78 }, { label: 'خرد', value: 90 },
  { label: 'تیر', value: 74 }, { label: 'مرد', value: 105 }, { label: 'شهر', value: 96 },
  { label: 'مهر', value: 112 }, { label: 'آبا', value: 98 }, { label: 'آذر', value: 121 },
  { label: 'دی', value: 108 }, { label: 'بهم', value: 132 }, { label: 'اسف', value: 145 },
];

export const invoices = [
  { no: '۱۲۵۰', customer: 'فروشگاه آریا', rep: 'امیر حسینی', amount: '۸۵۰,۰۰۰,۰۰۰', status: 'PAID', date: '۱۴۰۴/۰۶/۱۰' },
  { no: '۱۲۴۹', customer: 'سوپرمارکت مهر', rep: 'رضا عزیزی', amount: '۳۲۰,۵۰۰,۰۰۰', status: 'OUT_FOR_DELIVERY', date: '۱۴۰۴/۰۶/۱۰' },
  { no: '۱۲۴۸', customer: 'هاپرمارکت شهر', rep: 'امیر حسینی', amount: '۱,۴۲۰,۰۰۰,۰۰۰', status: 'CONFIRMED', date: '۱۴۰۴/۰۶/۰۹' },
  { no: '۱۲۴۷', customer: 'فروشگاه نگین', rep: 'سارا کاظمی', amount: '۲۱۰,۰۰۰,۰۰۰', status: 'RESERVED', date: '۱۴۰۴/۰۶/۰۹' },
  { no: '۱۲۴۶', customer: 'مارکت امید', rep: 'رضا عزیزی', amount: '۹۸,۰۰۰,۰۰۰', status: 'PENDING', date: '۱۴۰۴/۰۶/۰۸' },
  { no: '۱۲۴۵', customer: 'فروشگاه سحر', rep: 'امیر حسینی', amount: '۴۵۰,۰۰۰,۰۰۰', status: 'DELIVERED', date: '۱۴۰۴/۰۶/۰۸' },
  { no: '۱۲۴۴', customer: 'سوپر برادران', rep: 'سارا کاظمی', amount: '۱۷۵,۰۰۰,۰۰۰', status: 'CANCELLED', date: '۱۴۰۴/۰۶/۰۷' },
];

export const products = [
  { sku: 'AB-1001', name: 'نوشابه خانواده ۱.۵ لیتری', brand: 'آریا', stock: '۲,۴۵۰', reserved: '۳۲۰', available: '۲,۱۳۰', price: '۴۵,۰۰۰', status: 'ok' },
  { sku: 'AB-1002', name: 'آب معدنی ۵۰۰ میلی‌لیتر', brand: 'چشمه', stock: '۸,۲۰۰', reserved: '۱,۱۰۰', available: '۷,۱۰۰', price: '۱۲,۰۰۰', status: 'ok' },
  { sku: 'AB-1003', name: 'چیپس نمکی ۱۲۰ گرم', brand: 'طعم‌نو', stock: '۱۸۰', reserved: '۶۰', available: '۱۲۰', price: '۳۸,۰۰۰', status: 'low' },
  { sku: 'AB-1004', name: 'کیک دوقلو ۸۰ گرم', brand: 'شیرین', stock: '۰', reserved: '۰', available: '۰', price: '۲۵,۰۰۰', status: 'out' },
  { sku: 'AB-1005', name: 'بیسکوییت کرم‌دار', brand: 'شیرین', stock: '۳,۱۰۰', reserved: '۲۴۰', available: '۲,۸۶۰', price: '۳۰,۰۰۰', status: 'ok' },
  { sku: 'AB-1006', name: 'نوشیدنی انرژی‌زا', brand: 'آریا', stock: '۹۵', reserved: '۲۰', available: '۷۵', price: '۵۵,۰۰۰', status: 'low' },
];

export const customers = [
  { name: 'فروشگاه آریا', owner: 'عباس رستمی', zone: 'غرب', rep: 'امیر حسینی', balance: '۱۲۰,۰۰۰,۰۰۰', credit: '۵۰۰,۰۰۰,۰۰۰', lastBuy: '۱۴۰۴/۰۶/۱۰' },
  { name: 'سوپرمارکت مهر', owner: 'مهدی نصیری', zone: 'مرکز', rep: 'رضا عزیزی', balance: '۰', credit: '۳۰۰,۰۰۰,۰۰۰', lastBuy: '۱۴۰۴/۰۶/۱۰' },
  { name: 'هاپرمارکت شهر', owner: 'سعید محمدی', zone: 'شمال', rep: 'امیر حسینی', balance: '۸۵۰,۰۰۰,۰۰۰', credit: '۲,۰۰۰,۰۰۰,۰۰۰', lastBuy: '۱۴۰۴/۰۶/۰۹' },
  { name: 'فروشگاه نگین', owner: 'زهرا احمدی', zone: 'شرق', rep: 'سارا کاظمی', balance: '۴۵,۰۰۰,۰۰۰', credit: '۲۰۰,۰۰۰,۰۰۰', lastBuy: '۱۴۰۴/۰۶/۰۹' },
  { name: 'مارکت امید', owner: 'رضا کاظمی', zone: 'جنوب', rep: 'رضا عزیزی', balance: '۲۱۰,۰۰۰,۰۰۰', credit: '۱۵۰,۰۰۰,۰۰۰', lastBuy: '۱۴۰۴/۰۶/۰۸' },
];

export const activities = [
  { icon: 'invoice', tint: 'green', title: 'فاکتور #۱۲۵۰ تسویه شد', desc: 'فروشگاه آریا — ۸۵۰,۰۰۰,۰۰۰ ریال', time: '۱۱:۴۵' },
  { icon: 'box', tint: 'teal', title: 'موجودی کالا به‌روزرسانی شد', desc: 'رسید ورود #۴۸ — انبار مرکزی', time: '۱۰:۲۱' },
  { icon: 'users', tint: 'orange', title: 'پرداخت مشتری ثبت شد', desc: 'سوپرمارکت مهر — کارتخوان', time: '۰۹:۳۸' },
  { icon: 'invoice', tint: 'violet', title: 'سفارش جدید ثبت شد', desc: 'بازاریاب امیر حسینی — مسیر ۱۲', time: '۰۹:۱۲' },
  { icon: 'route', tint: 'blue', title: 'مسیر جدید تعریف شد', desc: 'مامور پخش: کامران صالحی', time: '۰۸:۵۴' },
];

export const routeStops = [
  { name: 'فروشگاه آریا', state: 'done', time: '۰۸:۳۰', sale: '۸۵۰,۰۰۰,۰۰۰' },
  { name: 'سوپرمارکت مهر', state: 'done', time: '۰۹:۴۵', sale: '۳۲۰,۵۰۰,۰۰۰' },
  { name: 'مارکت امید', state: 'current', time: '۱۰:۳۰', sale: '—' },
  { name: 'فروشگاه نگین', state: 'next', time: '—', sale: '—' },
  { name: 'سوپر برادران', state: 'next', time: '—', sale: '—' },
  { name: 'فروشگاه سحر', state: 'cancel', time: '—', sale: '—' },
];

export const mapPins = [
  { x: 18, y: 62, label: 'آریا ✓', color: '#4ade80' },
  { x: 34, y: 40, label: 'مهر ✓', color: '#4ade80' },
  { x: 48, y: 55, label: 'امید ●', color: '#fbbf24' },
  { x: 62, y: 32, label: 'نگین ○', color: '#f87171' },
  { x: 76, y: 58, label: 'برادران ○', color: '#f87171' },
  { x: 88, y: 40, label: 'انبار', color: '#38bdf8' },
];

export const employees = [
  { name: 'امیر حسینی', role: 'بازاریاب', branch: 'مرکزی', checkin: '۰۷:۵۵', status: 'حاضر' },
  { name: 'رضا عزیزی', role: 'بازاریاب', branch: 'مرکزی', checkin: '۰۸:۱۰', status: 'حاضر' },
  { name: 'کامران صالحی', role: 'مامور پخش', branch: 'مرکزی', checkin: '۰۷:۳۰', status: 'حاضر' },
  { name: 'مهدی اکبری', role: 'انباردار', branch: 'انبار غرب', checkin: '—', status: 'غایب' },
  { name: 'فرهاد نادری', role: 'حسابدار', branch: 'دفتر مرکزی', checkin: '۰۸:۰۰', status: 'حاضر' },
];

export const checks = [
  { no: '۸۵۴۱۲۳', bank: 'ملی', amount: '۲,۰۰۰,۰۰۰,۰۰۰', due: '۱۴۰۴/۰۶/۲۵', owner: 'فروشگاه آریا', status: 'PENDING' },
  { no: '۸۵۴۱۲۴', bank: 'تجارت', amount: '۷۵۰,۰۰۰,۰۰۰', due: '۱۴۰۴/۰۶/۱۸', owner: 'هاپرمارکت شهر', status: 'PENDING' },
  { no: '۸۵۴۱۱۹', bank: 'صادرات', amount: '۴۰۰,۰۰۰,۰۰۰', due: '۱۴۰۴/۰۶/۰۵', owner: 'مارکت امید', status: 'CONFIRMED' },
  { no: '۸۵۴۱۱۰', bank: 'ملت', amount: '۱,۲۰۰,۰۰۰,۰۰۰', due: '۱۴۰۴/۰۵/۳۰', owner: 'سوپر برادران', status: 'REJECTED' },
];

export const deliveries = [
  { invoice: '۱۲۴۹', customer: 'سوپرمارکت مهر', address: 'تهران، خیابان ولیعصر، پلاک ۲۴', amount: '۳۲۰,۵۰۰,۰۰۰', status: 'OUT_FOR_DELIVERY', pay: 'UNPAID' },
  { invoice: '۱۲۴۵', customer: 'فروشگاه سحر', address: 'تهران، میدان انقلاب، کوچه ۸', amount: '۴۵۰,۰۰۰,۰۰۰', status: 'DELIVERED', pay: 'PAID' },
  { invoice: '۱۲۴۸', customer: 'هاپرمارکت شهر', address: 'تهران، سعادت‌آباد، بلوار دریا', amount: '۱,۴۲۰,۰۰۰,۰۰۰', status: 'READY_FOR_DELIVERY', pay: 'UNPAID' },
];

export const auditLogs = [
  { user: 'Admin', action: 'تأیید فاکتور', target: '#۱۲۵۵', time: '۱۰:۲۵', oldv: 'RESERVED', newv: 'CONFIRMED', ip: '192.168.1.10' },
  { user: 'حسین رضایی', action: 'اصلاح موجودی', target: 'AB-1003', time: '۰۹:۵۰', oldv: '۱۸۰', newv: '۱۹۵', ip: '192.168.1.22' },
  { user: 'امیر حسینی', action: 'ثبت سفارش', target: '#۱۲۵۶', time: '۰۹:۱۲', oldv: '—', newv: 'DRAFT', ip: 'Mobile GPS' },
  { user: 'فرهاد نادری', action: 'ثبت دریافت', target: 'رسید #۹۸', time: '۰۸:۴۰', oldv: '—', newv: '۸۵۰,۰۰۰,۰۰۰', ip: '192.168.1.15' },
];

export const reps = [
  { name: 'امیر حسینی', visits: 12, orders: 9, sales: '۲,۴۵۰,۰۰۰,۰۰۰', target: 82, route: 'غرب — مسیر ۱۲' },
  { name: 'رضا عزیزی', visits: 10, orders: 7, sales: '۱,۸۲۰,۰۰۰,۰۰۰', target: 65, route: 'مرکز — مسیر ۸' },
  { name: 'سارا کاظمی', visits: 8, orders: 5, sales: '۹۸۰,۰۰۰,۰۰۰', target: 44, route: 'شرق — مسیر ۳' },
];

export const notifications = [
  { icon: 'invoice', tint: 'green', title: 'فاکتور جدید ثبت شد', desc: 'فاکتور #۱۲۵۶ توسط امیر حسینی', time: '۵ دقیقه پیش' },
  { icon: 'box', tint: 'rose', title: 'کالای «کیک دوقلو» تمام شد', desc: 'انبار مرکزی — موجودی صفر', time: '۲۰ دقیقه پیش' },
  { icon: 'receipt', tint: 'amber', title: 'چک نزدیک سررسید', desc: 'چک #۸۵۴۱۲۴ — ۴ روز مانده', time: '۱ ساعت پیش' },
  { icon: 'approval', tint: 'violet', title: 'درخواست تخفیف بیش از حد مجاز', desc: 'فاکتور #۱۲۵۱ — نیازمند تأیید مدیر', time: '۲ ساعت پیش' },
  { icon: 'truck', tint: 'blue', title: 'مرسوله تحویل شد', desc: 'فاکتور #۱۲۴۵ — فروشگاه سحر', time: '۳ ساعت پیش' },
];
