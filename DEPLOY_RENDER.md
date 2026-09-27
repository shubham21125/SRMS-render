# Deploying SRMS to Render

This project is ready to deploy on [Render](https://render.com) using either the
one-click Blueprint (`render.yaml`) or a manually configured Web Service.

## Option A — Blueprint (recommended)

1. Push this folder to a GitHub/GitLab repo.
2. In the Render dashboard, click **New → Blueprint** and point it at the repo.
   Render will read `render.yaml` and provision:
   - A free PostgreSQL database (`srms-db`)
   - A web service (`srms-web`) that runs `build.sh` then Gunicorn
3. After the first deploy, open the service's **Environment** tab and add the
   secrets that are intentionally *not* in `render.yaml` (see below).
4. Once live, open a shell on the service (**Shell** tab) and run:
   ```bash
   python manage.py createsuperuser
   ```

## Option B — Manual Web Service

1. **New → Web Service**, connect your repo.
2. Runtime: **Python 3**
3. Build command: `./build.sh`
4. Start command:
   ```
   gunicorn StudentResultManagement.wsgi:application --bind 0.0.0.0:$PORT --workers 3
   ```
5. **New → PostgreSQL** to create a database, then copy its **Internal
   Connection String** into the web service's `DATABASE_URL` env var.
6. Add the environment variables listed below.

## Required environment variables

| Variable | Notes |
|---|---|
| `SECRET_KEY` | Generate a new random value — never reuse a key that was ever committed to git. |
| `DEBUG` | `False` |
| `DATABASE_URL` | Auto-filled if using the Blueprint / a linked Render Postgres DB. |
| `ALLOWED_HOSTS` | `.onrender.com` (or your custom domain) |
| `CSRF_TRUSTED_ORIGINS` | `https://<your-service>.onrender.com` |
| `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `DEFAULT_FROM_EMAIL` | Gmail SMTP (use an **App Password**, not your account password) |
| `GOOGLE_OAUTH2_CLIENT_ID`, `GOOGLE_OAUTH2_CLIENT_SECRET`, `GOOGLE_OAUTH2_REDIRECT_URI` | From Google Cloud Console; redirect URI must be `https://<your-service>.onrender.com/admin-google-callback/` and added to the OAuth client's Authorized redirect URIs |
| `GOOGLE_ADMIN_ALLOWED_EMAILS` | Comma-separated admin emails allowed to use Google SSO |
| `GEMINI_API_KEY` | For the chatbot |
| `WHATSAPP_TOKEN`, `WHATSAPP_PHONE_NUMBER_ID` | Meta WhatsApp Cloud API |
| `REDIS_URL` | Optional — add a Render Key Value (Redis) instance for shared caching/rate-limiting across workers. Falls back to in-process memory cache if unset. |

## ⚠️ Rotate leaked credentials first

The original `.env` in this project contained **real, working secrets** committed
in plain text (a Gmail app password, a Google OAuth client secret, and a Gemini
API key). Those have been stripped from this package and replaced with
placeholders, but the exposed values are still valid until you act:

- Revoke/regenerate the Gmail **App Password** in the Google Account security settings.
- Regenerate the **Google OAuth2 Client Secret** in Google Cloud Console.
- Regenerate the **Gemini API key** at https://aistudio.google.com/app/apikey.
- Generate a brand-new Django `SECRET_KEY` (never reuse the one that shipped in `.env`).

Do this regardless of whether you deploy on Render — the old values are
compromised because they were exposed in a file that left your control.

## What changed to make this deploy-ready

- `StudentResultManagement/settings.py`: added WhiteNoise middleware + static
  storage, `DATABASE_URL` support (Postgres in production, SQLite fallback for
  local dev), and automatic `ALLOWED_HOSTS`/`CSRF_TRUSTED_ORIGINS` entries for
  Render's `RENDER_EXTERNAL_HOSTNAME`.
- `requirements.txt`: added `gunicorn`, `whitenoise`, `psycopg2-binary`,
  `dj-database-url`.
- `build.sh`: installs dependencies, runs `collectstatic`, runs `migrate`.
- `render.yaml`: Render Blueprint definition (web service + managed Postgres).
- Removed from the package: git history, `__pycache__`, `.coverage`,
  `django_errors.log`, `smoke_test_results.json`, the `scratch/` dev folder,
  the dev `db.sqlite3`, and sample test photos — none of these belong in a
  production deploy.
