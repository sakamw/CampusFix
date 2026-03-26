# CampusFix

CampusFix is a full-stack issue reporting and management platform designed for campus facilities management. Students can report issues anonymously or publicly, track progress with photo evidence, provide feedback, and receive real-time notifications. Admin and staffs manage assignments, SLAs, maintenance windows, and analytics with AI-assisted report generation analysis.

## Features

### Core Functionality

- **Issue Reporting & Tracking**: Anonymous/public reporting, progress notes with photo uploads (Cloudinary), estimated resolution times, recurring issues.
- **SLA Management**: Configurable SLA rules, breach detection, pausable deadlines, overdue alerts.
- **Staff Workflow**: Assignment, progress logs, resolution evidence, admin interface for bulk actions.
- **Feedback System**: Post-resolution ratings/comments with AI frustration scoring.
- **Leaderboards**: User rankings based on reported/resolved issues.

### User Features

- Role-based access (Student, Staff, Admin).
- Two-Factor Authentication for students(TOTP).
- Email verification, password reset, forgot password.
- Real-time notifications (WebSockets), announcement dismissals, email preferences.
- Settings: Theme toggle, email notifications, issue update subscriptions.
- Public issue browsing, personal issue lists, notifications center.

### Admin/Staff Tools

- Dashboard analytics.
- Maintenance mode scheduling with notifications.
- Issue trashing (soft delete), search/filtering.
- AI services for comment analysis.

### Security

- Custom Django permissions/decorators.
- Rate limiting, CSRF/XSS protection.
- Secure file uploads, token-based resets/verification.

## Tech Stack

| Frontend | React 19 (TypeScript), Vite, TailwindCSS, shadcn/ui, Zustand contexts   |
| -------- | ----------------------------------------------------------------------- |
| Backend  | Django 5+, Django REST Framework, Django Channels (WebSockets), SQLite  |
| Database | SQLite (with migrations for production scalability)                     |
| Other    | Cloudinary (images), pyotp (2FA), Celery-ready, AI services integration |

## Architecture

```
CampusFix/
├── client/              # React frontend
│   ├── src/
│   │   ├── components/  # UI components (ChatWidget, Timeline, 2FA modals, dashboard)
│   │   ├── contexts/    # Auth, Theme, UserSettings
│   │   ├── hooks/       # Custom hooks (mobile detect, toast)
│   │   ├── lib/         # API client, utils, Cloudinary
│   │   └── pages/       # Routed pages (Dashboard, ReportIssue, Leaderboard, etc.)
│   └── vite.config.ts
├── server/              # Django backend
│   ├── accounts/        # Auth: Custom User, 2FA, tokens
│   ├── issues/          # Core models/views: Issues, SLA, Progress, Feedback
│   ├── notifications/   # WebSockets, models, services
│   ├── dashboard/       # Staff views
│   ├── campusfix/       # Settings, URLs, ASGI
│   └── manage.py
└── README.md
```

Frontend communicates with backend via REST API + WebSockets. API base: `/api/`.

## Quick Start (Development)

### Prerequisites

- Node.js 20+, Python 3.12+, pnpm (client), pip (server)
- Cloudinary account (free tier OK): Add `CLOUDINARY_*` env vars.

### Backend

```bash
cd server
python -m venv venv
source venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
cp campusfix/settings.py.example campusfix/settings.py  # If needed, add keys
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py runserver
```

Server runs on `http://localhost:8000`. Admin: `http://localhost:8000/admin/`

### Frontend

```bash
cd client
pnpm install
pnpm dev
```

App runs on `http://localhost:5173`. Update `VITE_API_URL` in `.env` if backend port differs.

### Full Stack

1. Start backend (port 8000).
2. Start frontend (port 5173).
3. Create superuser: `python manage.py createsuperuser`
4. Register/login via app (2FA setup prompted).
5. Test issue reporting flow.

### Email (Development)

Uses console backend by default. For SMTP, update `EMAIL_*` in `settings.py`.

## API Endpoints (Django REST)

| Endpoint              | Method   | Description          | Auth  |
| --------------------- | -------- | -------------------- | ----- |
| `/api/auth/`          | POST     | Login                | No    |
| `/api/issues/`        | GET/POST | List/Create issues   | Yes   |
| `/api/issues/{id}/`   | GET/PUT  | Issue details/update | Yes   |
| `/api/notifications/` | GET      | User notifications   | Yes   |
| `/ws/notifications/`  | WS       | Real-time updates    | Token |

See `server/*/serializers.py` and `client/src/lib/api.ts` for schemas.

## Environment Variables

Backend (`server/campusfix/settings.py`):

```
DEBUG=True
SECRET_KEY=your-secret
CLOUDINARY_CLOUD_NAME=...
CLOUDINARY_API_KEY=...
CLOUDINARY_API_SECRET=...
EMAIL_HOST=...
DATABASE_URL=sqlite:///db.sqlite3  # PostgreSQL in prod
```

Frontend (`.env`):

```
VITE_API_URL=http://localhost:8000
VITE_CLOUDINARY_CLOUD_NAME=...
```

## Migrations & Seeding

```
python manage.py makemigrations
python manage.py migrate
python manage.py loaddata fixtures  # If any
```

## Production Deployment

- Backend: Gunicorn + Daphne (ASGI), PostgreSQL/Redis, Nginx.
- Frontend: Vite build (`pnpm build`), serve static.
- Env: HTTPS, secure cookies, Celery for emails/AI tasks.
- Docker-ready (add Dockerfile/compose).

## Contributing

1. Fork & clone.
2. Backend: `make migrate dev` (add Makefile if needed).
3. Frontend: `pnpm lint && pnpm dev`.
4. Submit PR to `main`.

## License

MIT License
