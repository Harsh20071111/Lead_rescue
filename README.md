# LeadRescue

**AI-powered Real Estate Lead Management & Analytics** — built for Indian real estate agencies.

LeadRescue ensures your team never loses track of a single lead — so every commission you've earned, stays earned.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.13+, Django 5.2 |
| Database | PostgreSQL |
| Frontend | Django Templates, HTMX, Tailwind CSS |
| Charts | Chart.js |
| Background Tasks | Celery + Redis |
| CSV Processing | Pandas |
| PDF Generation | WeasyPrint |
| Deployment | Railway / Render |

---

## Project Structure

```
leadrescue/
├── manage.py
├── config/                 # Settings, URLs, WSGI, ASGI, Celery
├── apps/
│   ├── common/             # Shared base models & utilities
│   ├── accounts/           # Custom User model (Owner/Admin/Agent)
│   ├── agencies/           # Agency model
│   ├── core/               # Landing page, health check
│   ├── leads/              # Lead management (stub)
│   ├── dashboard/          # Dashboard (stub)
│   ├── notifications/      # Notifications (stub)
│   └── reports/            # Reports & PDF (stub)
├── templates/              # Global Django templates
├── static/                 # CSS, JS, fonts, images
└── media/                  # User uploads
```

---

## Quick Start

### 1. Clone the repository

```bash
git clone <your-repo-url>
cd Real-estate
```

### 2. Set up Python environment

```bash
python3.13 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` with your actual values:

```env
SECRET_KEY=your-random-secret-key-here
DEBUG=True
DATABASE_URL=postgres://user:password@localhost:5432/leadrescue_db
CELERY_BROKER_URL=redis://localhost:6379/0
```

### 4. Set up PostgreSQL

```bash
createdb leadrescue_db
# Or use SQLite for quick local dev (default fallback)
```

### 5. Run migrations

```bash
cd leadrescue
python manage.py makemigrations
python manage.py migrate
```

### 6. Create superuser

```bash
python manage.py createsuperuser
```

### 7. Build Tailwind CSS

```bash
# Install Node dependencies (one time)
npm install

# Build CSS
npm run build:css

# Or watch for changes during development
npm run watch:css
```

### 8. Run the development server

```bash
python manage.py runserver
```

Visit:
- **Landing page**: http://localhost:8000/
- **Admin panel**: http://localhost:8000/admin/
- **Health check**: http://localhost:8000/health/

---

## Running Celery (Background Tasks)

```bash
# Start Redis (if not running)
redis-server

# Start Celery worker
celery -A config worker --loglevel=info
```

---

## Environment Variables

| Variable | Description | Default |
|---|---|---|
| `SECRET_KEY` | Django secret key | (insecure default) |
| `DEBUG` | Enable debug mode | `False` |
| `ALLOWED_HOSTS` | Comma-separated hostnames | `localhost,127.0.0.1` |
| `DATABASE_URL` | PostgreSQL connection URL | `sqlite:///db.sqlite3` |
| `CELERY_BROKER_URL` | Redis URL for Celery | `redis://localhost:6379/0` |
| `CELERY_RESULT_BACKEND` | Redis URL for results | `redis://localhost:6379/0` |
| `EMAIL_BACKEND` | Email backend class | Console backend |

---

## User Roles

| Role | Description |
|---|---|
| **Owner** | Agency owner with full platform access |
| **Admin** | Administrative staff with management access |
| **Agent** | Sales agent with operational access |

---

## Deployment

The project includes a `Procfile` for Railway/Render deployment:

```
web: gunicorn config.wsgi --chdir leadrescue --bind 0.0.0.0:$PORT
worker: celery -A config worker --loglevel=info --chdir leadrescue
```

### Railway / Render

1. Set all environment variables from `.env.example`
2. Set `DEBUG=False`
3. Set `ALLOWED_HOSTS` to your domain
4. Provision PostgreSQL and Redis add-ons
5. Deploy

---

## License

Proprietary — All rights reserved.
