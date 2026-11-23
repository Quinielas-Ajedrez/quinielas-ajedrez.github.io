# Deploying Quiniela to GitHub Pages + Render + Neon

## Overview

- **Frontend** → GitHub Pages (https://yourusername.github.io/Quiniela/)
- **Backend** → Render (free web service)
- **Database** → Neon (free Postgres)

---

## Step 1: Deploy the backend (Render)

1. Push your Quiniela project to GitHub.

2. Go to [render.com](https://render.com) and sign up (GitHub login is fine).

3. Click **New** → **Web Service**.

4. Connect your GitHub repo and select the Quiniela repository.

5. Configure:
   - **Name:** `quiniela` (or anything)
   - **Build Command:** `uv sync`
   - **Start Command:** `uv run uvicorn backend.main:app --host 0.0.0.0 --port $PORT`

6. **Connect the Neon database** (keeps data when the app sleeps):
   - Don't use Render's free PostgreSQL. Render deletes free databases after 30 days, which takes the app down. Neon's free tier doesn't expire; it suspends when idle and wakes on the next connection.
   - The project is linked through `neon.ts`. From the project root, with the Neon CLI installed (`npm i -g neon@latest`):
     ```bash
     neon login
     neon env pull   # writes DATABASE_URL and DATABASE_URL_UNPOOLED to .env.local (git-ignored)
     ```
     You can also copy both connection strings from the Neon console (**Connect**, pooled and direct).
   - In your Web Service → **Environment**, set:
     - `DATABASE_URL` = the **pooled** connection string (hostname contains `-pooler`), used for app traffic
     - `DATABASE_URL_UNPOOLED` = the **direct** connection string (no `-pooler`), used at startup to create and migrate tables
   - Tables are created automatically on first startup.

7. Add other environment variables (if not already set):
   - `SITE_PASSWORD` = your gate password
   - `BOOTSTRAP_SECRET` = a long random string - used to promote your first super-admin
   - `CORS_ORIGINS` = `https://yourusername.github.io`

8. Click **Create Web Service** (or save) and wait for the first deploy.

9. Copy your service URL, e.g. `https://quiniela-xyz.onrender.com`

---

## Step 2: Add the API URL as a GitHub secret

1. On GitHub, open your Quiniela repo.

2. Go to **Settings** → **Secrets and variables** → **Actions**.

3. Click **New repository secret**.

4. Name: `VITE_API_URL`  
   Value: `https://quiniela-xyz.onrender.com` (your Render URL, no trailing slash)

5. Click **Add secret**.

---

## Step 3: Enable GitHub Pages

1. In your repo, go to **Settings** → **Pages**.

2. Under **Build and deployment**, set:
   - **Source:** GitHub Actions (not "Deploy from a branch")

3. Save. If you had "Deploy from a branch" selected before, GitHub was serving the repo root (no `index.html`). Switching to GitHub Actions fixes that.

---

## Step 4: Deploy the frontend

1. Push to the `main` branch (or merge a PR).

2. The workflow in `.github/workflows/deploy-pages.yml` will run automatically.

3. It will:
   - Build the frontend with `VITE_API_URL`
   - Deploy it to GitHub Pages

4. When it finishes, your site will be at:  
   `https://yourusername.github.io/Quiniela/`

(Replace `Quiniela` with your actual repo name if different.)

---

## Step 5: Make yourself super-admin

Render's free tier has no Shell, so use the bootstrap endpoint:

1. Register via the app (site gate password → sign up).
2. From your machine, run (use your Render URL and the `BOOTSTRAP_SECRET` you set):

```bash
curl -X POST https://your-app.onrender.com/auth/bootstrap \
  -H "Content-Type: application/json" \
  -d '{"secret":"YOUR_BOOTSTRAP_SECRET","username":"YOUR_USERNAME"}'
```

3. Log in again – you'll see **Manage users**.

---

## Step 6: Update CORS on Render

1. Go back to Render → your service → **Environment**.

2. Ensure `CORS_ORIGINS` is your GitHub Pages URL:
   ```
   https://yourusername.github.io
   ```

3. Render will redeploy with the new env var.

---

## Building locally (without GitHub Actions)

If you want to build and test the production build locally:

```bash
cd frontend

# Replace with your Render backend URL
VITE_API_URL=https://quiniela-xyz.onrender.com VITE_BASE_PATH=/Quiniela/ npm run build
```

The built files will be in `frontend/dist/`. For GitHub Pages, the workflow handles this automatically.

---

## Troubleshooting

**Site shows blank page or directory listing**  
- Ensure **Settings → Pages → Source** is **GitHub Actions**, not "Deploy from a branch". The branch option serves the repo root, which has no `index.html`.
- Check the browser console for 404s.

**Assets load from wrong path (MIME type "text/html" errors)**  
- For a **user/org site** (repo named `yourusername.github.io`): base path is `/`, site at `https://yourusername.github.io/`.
- For a **project site** (repo named `Quiniela`): base path is `/Quiniela/`, site at `https://yourusername.github.io/Quiniela/`.  
- The workflow auto-detects this. If your repo is `quinielas-ajedrez.github.io`, it will use base `/`.

**“CORS” or “blocked” errors**  
- Confirm `CORS_ORIGINS` on Render includes your GitHub Pages URL exactly (no trailing slash).

**Login / API fails**  
- Confirm `VITE_API_URL` is correct and the Render service is running.

**Data (users, tournaments) disappears after inactivity**  
- `DATABASE_URL` isn't set, so the app fell back to SQLite, which is lost when the Render instance sleeps. Set the Neon variables (Step 1.6) and redeploy.

**Backend never responds (requests hang, site doesn't load)**  
- Check the Render logs for database connection errors at startup. This happened when the old free Render PostgreSQL expired. Confirm `DATABASE_URL` / `DATABASE_URL_UNPOOLED` point at a live Neon database.
- The first request after ~15 minutes idle takes 30–60s while Render wakes the service. That's normal.

**Running locally against Neon**  
```bash
set -a; source .env.local; set +a
uv run uvicorn backend.main:app --reload
```
