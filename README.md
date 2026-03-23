# Quiniela

A chess tournament prediction system: users make predictions for each round, and points are awarded based on a scoring criteria.

## Setup

```bash
uv sync
```

## Database

Initialize the database:

```bash
uv run python -m backend.import_tournament --init
```

Import a tournament from YAML:

```bash
uv run python -m backend.import_tournament examples/sample_tournament.yaml
```

See `examples/sample_tournament.yaml` for the expected YAML format.

## Users

Create a user (for bootstrapping):

```bash
# Regular user
uv run python -m backend.create_user "Your Name" username password

# Admin (tournaments, games, rounds)
uv run python -m backend.create_user "Your Name" username password --admin

# Super-admin (can also assign admin to others)
uv run python -m backend.create_user "Your Name" username password --super-admin

# Promote an existing user to super-admin
uv run python -m backend.create_user --promote-super-admin username
```

Or register via API: `POST /auth/register` with `{ "name", "username", "password" }`.

## Frontend

```bash
cd frontend && npm install && npm run dev
```

Opens at http://localhost:5173. The first screen is a password gate (default password: `quiniela`). Set `SITE_PASSWORD` env var when running the backend to change it.

## API

Start the server (run this before the frontend):

```bash
uv run uvicorn backend.main:app --reload
```

Then open http://127.0.0.1:8000/docs for interactive API docs.

**Site gate:** Set `SITE_PASSWORD` env var to customize the gate password (default: `quiniela`). Set `CORS_ORIGINS` for production (default: `http://localhost:5173`).

**Auth:** All endpoints except `/auth/login` and `/auth/register` require `Authorization: Bearer <token>`.

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/auth/login` | Login, returns token |
| POST | `/auth/register` | Self-register |
| GET | `/auth/me` | Current user |
| GET | `/tournaments` | List tournaments |
| GET | `/tournaments/{id}` | Get tournament with rounds & games |
| POST | `/tournaments/import` | Import from YAML (admin) |
| PUT | `/tournaments/{id}` | Update tournament (admin) |
| GET | `/tournaments/{id}/leaderboard` | Leaderboard |
| POST | `/predictions` | Submit or update prediction (before deadline) |
| GET | `/predictions?round_id=` | My predictions for round |
| GET | `/predictions?tournament_id=` | My predictions for tournament |
| PATCH | `/games/{id}` | Update result or soft-delete (admin) |
| PATCH | `/rounds/{id}` | Update round (admin) |

## Deployment

### Build the frontend

```bash
cd frontend && npm install && npm run build
```

Output goes to `frontend/dist/`.

### Run the backend

```bash
uv sync
uv run uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

For production, set environment variables:

- `SITE_PASSWORD` — shared gate password (default: `quiniela`)
- `CORS_ORIGINS` — comma-separated allowed origins, e.g. `https://yourdomain.com`
- `SECRET_KEY` — JWT signing key (optional; generate a long random string for production)

### Serve the app

Two options:

**Option A: Backend serves frontend (single process)**

Mount the built frontend as static files. Add to your reverse proxy (nginx, Caddy) or use FastAPI's `StaticFiles`:

- Route `/api/*` → backend (uvicorn)
- Route `/*` → `frontend/dist/` (SPA fallback to `index.html`)

**Option B: Separate frontend and backend**

- Serve `frontend/dist/` with nginx/Caddy/Vercel/Netlify
- Point `VITE_API_URL` at your backend URL when building: `VITE_API_URL=https://api.yourdomain.com npm run build`
- Run backend with `CORS_ORIGINS` including your frontend origin

### Systemd example (Linux)

```ini
# /etc/systemd/system/quiniela.service
[Unit]
Description=Quiniela API
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/path/to/Quiniela
Environment="SITE_PASSWORD=your-secure-password"
Environment="CORS_ORIGINS=https://yourdomain.com"
ExecStart=/path/to/.local/bin/uv run uvicorn backend.main:app --host 127.0.0.1 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

### Database

SQLite is used by default (`data/quiniela.db`). Ensure the `data/` directory is writable. For higher concurrency, consider PostgreSQL (would require code changes to support `DATABASE_URL`).
