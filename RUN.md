# اجرای سریع آبتین

پیش‌نیاز: Docker Desktop + Docker Compose.

```bash
docker compose up --build
```

سپس:
- Frontend: http://localhost:3000
- API: http://localhost:8000
- Swagger: http://localhost:8000/api/docs/

کاربران نمونه:
- `admin`
- `sales.rep`
- `driver`
- `warehouse.manager`
- `accountant`

رمز کاربران seed شده: `Demo-Strong-Password-2026!`

برای اجرای CI در GitHub، فایل `.github/workflows/abtin-ci.yml` را نگه دارید. Workflow شامل تست Backend، HTTP smoke، Build فرانت و Docker Compose validation است.
