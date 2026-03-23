# Deploying Quiniela to GitHub Pages + Render

## Overview

- **Frontend** → GitHub Pages (https://yourusername.github.io/Quiniela/)
- **Backend** → Render (or Railway, Fly.io)

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

6. **Add a PostgreSQL database** (keeps data when the app sleeps):
   - Click **New** → **PostgreSQL**
   - Name it (e.g. `quiniela-db`), choose free plan, Create
   - Go back to your Web Service → **Environment**
   - Click **Add Database** (or **Link Resource**) and select the PostgreSQL instance
   - Render will add `DATABASE_URL` automatically. Data will now persist across restarts.

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
- Render free tier uses ephemeral storage; SQLite data is lost when the instance sleeps.
- Add a **PostgreSQL database** (New → PostgreSQL), link it to your web service. Render sets `DATABASE_URL` automatically. Redeploy. Data will persist.
