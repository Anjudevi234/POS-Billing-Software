# POS Billing Software

Interview-task implementation for a textile/retail Point of Sale system.

## Features
- Admin Portal
  - Dashboard
  - Product CRUD
  - Staff management
  - Supplier management
  - Product return handling
  - Ledger
  - Sales/reports
- Billing Portal
  - Product search
  - Cart
  - Stock validation
  - Payment
  - Invoice generation/printing
- Responsive mobile Admin Portal
  - Same Admin Portal works as a mobile-app-style web layout
  - Direct route: `/admin-portal/mobile/`
- Role-based authentication
  - ADMIN
  - STAFF
- SQLite for local development
- PostgreSQL-ready for production
- WhiteNoise + Gunicorn for deployment

## Local setup

### 1. Create virtual environment
Windows PowerShell:
```powershell
python -m venv venv
.env\Scripts\Activate.ps1
```

Linux/macOS:
```bash
python3 -m venv venv
source venv/bin/activate
```

### 2. Install
```bash
pip install -r requirements.txt
```

### 3. Migrate
```bash
python manage.py migrate
```

### 4. Create admin user
```bash
python manage.py createsuperuser
```

### 5. Run
```bash
python manage.py runserver
```

Open:
- Login: http://127.0.0.1:8000/
- Admin portal: http://127.0.0.1:8000/admin-portal/
- Mobile admin: http://127.0.0.1:8000/admin-portal/mobile/
- Billing: http://127.0.0.1:8000/billing/
- Django admin: http://127.0.0.1:8000/django-admin/

## Important role setup

The superuser is treated as ADMIN.

For normal staff:
1. Login to Django admin at `/django-admin/`.
2. Create a User.
3. Set `is_staff=True` only if you want Django admin access; it is not required for POS staff.
4. Create a Staff Profile and select role `STAFF`.

## Render deployment

1. Push the project to a public GitHub repository.
2. Create a PostgreSQL database on Render.
3. Create a Render Web Service from the GitHub repository.
4. Build command:
```bash
pip install -r requirements.txt && python manage.py migrate && python manage.py collectstatic --noinput
```
5. Start command:
```bash
gunicorn posbilling.wsgi:application
```
6. Add environment variables:
```text
SECRET_KEY=<strong-random-secret>
DEBUG=False
DATABASE_URL=<Render PostgreSQL internal/external connection string>
ALLOWED_HOSTS=<your-render-hostname>
CSRF_TRUSTED_ORIGINS=https://<your-render-hostname>
```
7. Open the deployed URL and create/use the test accounts.

## Suggested test credentials
Create these yourself rather than committing passwords:
- Admin: admin / your-password
- Staff: staff / your-password

## Interview explanation

Architecture:
Browser -> Django URLs -> Views -> Models -> SQLite/PostgreSQL

Authentication:
Django session authentication + StaffProfile role.

Billing:
Product selection -> Cart -> stock check -> Sale + SaleItem transaction -> stock decrement -> invoice page.

Returns:
Return record -> product stock increment -> ledger entry.

Reports:
Sales and ledger are aggregated from Sale, SaleItem and LedgerEntry records.

Mobile UI:
Responsive Bootstrap layout. The mobile route uses the same backend functionality with a mobile-first navigation shell. No APK is required.
