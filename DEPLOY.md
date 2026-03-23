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

6. Add environment variables (Environment tab):
   - `SITE_PASSWORD` = your gate password
   - `CORS_ORIGINS` = `https://yourusername.github.io` (you’ll add your real GitHub Pages URL in Step 3)

7. Click **Create Web Service** and wait for the first deploy.

8. Copy your service URL, e.g. `https://quiniela-xyz.onrender.com`

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
   - **Source:** GitHub Actions

3. Save.

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

## Step 5: Update CORS on Render

1. Go back to Render → your service → **Environment**.

2. Set `CORS_ORIGINS` to your GitHub Pages URL:
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

**Site shows blank page**  
- Check the browser console for 404s. Ensure `VITE_BASE_PATH` matches your repo name (e.g. `/Quiniela/` for repo `Quiniela`).

**“CORS” or “blocked” errors**  
- Confirm `CORS_ORIGINS` on Render includes your GitHub Pages URL exactly (no trailing slash).

**Login / API fails**  
- Confirm `VITE_API_URL` is correct and the Render service is running.
