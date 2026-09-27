# Production Deployment Checklist — SRMS

Follow these instructions systematically to deploy the Student Result Management System (SRMS) in a production environment.

---

## 1. Pre-Deployment Security Audit
- [ ] **Git Secrets Leak**: Ensure no credentials (e.g. SMTP passwords, Google OAuth client secrets, or Google API keys) exist in active code files. (Run a scan or checkout history for previous leaks).
- [ ] **Production Settings Gating**: Verify that `DEBUG=False` is set.
- [ ] **Secure Cookies**: Confirm that `SESSION_COOKIE_SECURE` and `CSRF_COOKIE_SECURE` are active.
- [ ] **CSRF Trusted Origins**: Set the `CSRF_TRUSTED_ORIGINS` environment variable to match the correct domain.

---

## 2. Environment Variables Configuration
- [ ] Copy `.env.example` to `.env`:
  ```bash
  cp .env.example .env
  ```
- [ ] Configure the following critical keys:
  - `SECRET_KEY`: Set to a secure, random cryptographic key.
  - `EMAIL_HOST_USER` & `EMAIL_HOST_PASSWORD`: Required for transactional alerts. *Must be set, or the application will fail to start*.
  - `GOOGLE_OAUTH2_CLIENT_ID` & `GOOGLE_OAUTH2_CLIENT_SECRET`: For SSO admin logins.
  - `WHATSAPP_TOKEN` & `WHATSAPP_PHONE_NUMBER_ID`: Meta API keys for sending WhatsApp notifications.
  - `GEMINI_API_KEY`: For the unified parent/student AI Chatbot.

---

## 3. Docker Deployment Setup
- [ ] Build and start the containers using Docker Compose:
  ```bash
  docker-compose up -d --build
  ```
- [ ] Verify that all three services are running:
  - `srms_web` (Django application listening on port 8000)
  - `srms_db` (PostgreSQL database server listening on port 5432)
  - `srms_redis` (Redis cache listening on port 6379)
- [ ] Inspect container health:
  ```bash
  docker-compose ps
  ```

---

## 4. Database Setup & Initialization
- [ ] Verify migrations applied successfully (automatically run by Docker entrypoint):
  - In case manual execution is needed:
    ```bash
    docker-compose exec web python manage.py migrate
    ```
- [ ] Create the primary superuser (Admin account):
  ```bash
  docker-compose exec web python manage.py createsuperuser
  ```
- [ ] Register default classes and branch structures in the admin dashboard.

---

## 5. Caching & Performance Verification
- [ ] Confirm Redis service is active. The application will fallback to local memory caching (`LocMemCache`) if Redis is unavailable, but Redis is required in multi-worker environments to share rate limits and analytics caches.
- [ ] Test analytics loading speed (caches the computed results for 5 minutes and invalidates on Result modifications).

---

## 6. Functional Verification
- [ ] **Login & Lockouts**: Verify that attempting 6 incorrect logins triggers a `429 Too Many Attempts` rate-limit screen.
- [ ] **SSO Authentication**: Test signing in with Google OAuth.
- [ ] **Result Card PDF**: Download a student marksheet from the parent dashboard and verify that `xhtml2pdf` compiles it cleanly.
- [ ] **WhatsApp Alerts**: Trigger a notice publishing or result entry, and check `WhatsAppLog` database entries in the django admin dashboard to verify notifications were sent.
