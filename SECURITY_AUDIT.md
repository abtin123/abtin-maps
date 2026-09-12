# گزارش ممیزی امنیتی آبتین

**دامنهٔ بررسی:** کد محلی Backend و Frontend، تنظیمات Django، وابستگی‌های Python و Node، کنترل دسترسی API، ورودی‌های جست‌وجو، حذف اسناد مالی، OTP/JWT و مسیرهای Backup/Restore. این بررسی دفاعی و غیرمخرب است و روی سرویس عمومی یا حساب واقعی انجام نشده است.

## نتایج اجراشده

| بررسی | نتیجه |
|---|---|
| `pip-audit -r backend/requirements.txt` | بدون آسیب‌پذیری شناخته‌شده |
| `npm audit --audit-level=high` | بدون آسیب‌پذیری |
| Bandit با آستانهٔ Medium/High | بدون یافته |
| `manage.py check` | موفق |
| بررسی migrationها | بدون تغییر معلق |
| تست ناشناس بودن APIهای محافظت‌شده | موفق؛ پاسخ 401 |
| تست RBAC کاربر فروش در API مالی | موفق؛ پاسخ 403 |
| تست ورودی جست‌وجوی SQL-like | بدون خطای 500 و با ORM پارامتری |
| تست حذف حساب مالی | موفق؛ پاسخ 405 و پیام Void |
| تست throttle ورود و OTP | پیکربندی scoped با نرخ `login=10/min` و `otp=3/min` |
| smoke test فازهای ۴ تا ۷ | همگی موفق |
| build فرانت‌اند با Vite patched | موفق |
| `check --deploy` با تنظیمات production | بدون هشدارهای امنیتی Django |

## اصلاحات انجام‌شده

نسخهٔ Django به بازهٔ patched `5.2.15–<5.3` ارتقا یافت. نسخه‌های Vite و React Router نیز به نسخه‌های بدون یافتهٔ `npm audit` ارتقا پیدا کردند. رمز هاردکدشدهٔ seed حذف شد؛ فرمان seed اکنون از `SEED_DEFAULT_PASSWORD` استفاده می‌کند و در صورت نبود آن، رمز تصادفی تولید می‌کند. رفتار logout دیگر `except Exception: pass` ندارد و فقط خطاهای مورد انتظار توکن را به‌صورت idempotent مدیریت می‌کند. برای production، `config.settings.prod` کلید، hostname، HTTPS، HSTS، کوکی امن و CORS/CSRF صریح را اجباری می‌کند.

## اجرای محلی ممیزی

```bash
cd backend
pip-audit -r requirements.txt
bandit -r apps config -lll -iii
DJANGO_SETTINGS_MODULE=config.settings.dev python manage.py check
DJANGO_SETTINGS_MODULE=config.settings.dev python security_smoke.py

cd ../frontend
npm audit --audit-level=high
npm run build
```

## نکتهٔ دامنه

این گزارش به معنی تضمین امنیت مطلق نیست. آزمون نفوذ خارجی، DAST کامل، بررسی تنظیمات شبکه/فایروال، تست بار و بازبینی secrets محیط استقرار باید در محیط staging واقعی و با مجوز مالک زیرساخت انجام شود. در production نباید از `config.settings.dev`، رمز seed ثابت یا wildcard در `ALLOWED_HOSTS` استفاده شود.
