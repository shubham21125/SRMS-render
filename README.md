# Student Result Management System (SRMS)

SRMS is a high-performance, commercial-ready Django application designed for educational institutions. It includes role-based student, parent, teacher, and administrator portals, NEP 2020 compliant SGPA calculations, automated WhatsApp alerts, REST APIs, dynamic caching, and rich GSAP animations.

---

## 🚀 Key Features

### 🔐 Security & Access Control (RBAC)
*   **Unified Role-Based Portals**: Segmented views for Students, Parents, Teachers, and Admins.
*   **Google OAuth2 SSO**: Secure Single Sign-On for administrators.
*   **Privilege Escalation Controls**: Hardened boundaries utilizing custom `@role_required` decorators across all view functions and AJAX endpoints.
*   **Rate-Limiting**: Lockouts (via `django-ratelimit`) on login and OTP recovery endpoints preventing brute-force entries (too many attempts triggers lockouts for 10 minutes).

### 📊 Academic Analytics & NEP 2020 Compliance
*   **NEP 2020 Grading Scale**: Implements Mumbai University's UGC 10-point credit-weighted grading system (O, A+, A, B+, B, C, D, F).
*   **Advanced Visual Analytics**: Dynamic bar, radar, and trend charts powered by Chart.js.
*   **Secure PDF Generation**: Downloadable result marksheets compiled using `xhtml2pdf` that replicate exact card views securely.

### 🔌 Developer API & Integration
*   **Versioned REST API**: Gated endpoints (`/api/v1/students/`, `/api/v1/results/`) respecting strict user-scope visibility filters using Token Authentication.
*   **WhatsApp Cloud API**: Immediate transactional notifications (result publishing, absent alerts, notices) sent to parent phone numbers via Meta's Graph API, with automatic formatting for India (`91` country code).
*   **Comprehensive Audit Logs**: Every administrative CREATE, UPDATE, or DELETE operation on Student and Result records is automatically logged along with client IP addresses.

### ⚡ Performance & Caching
*   **N+1 Query Resolution**: Heavy database operations are optimized to execute in O(1) query complexity.
*   **Redis Caching Layer**: Analytics context is cached for 5 minutes (using `django-redis`) with instant signal-based cache invalidation whenever results are updated.

---

## 🛠️ Technology Stack
*   **Backend**: Django 4.2.30, Django REST Framework 3.15.2
*   **Database**: PostgreSQL 15, SQLite (development fallback)
*   **Caching**: Redis 7 / `django-redis`
*   **PDF Generation**: `xhtml2pdf`
*   **Rate Limiting**: `django-ratelimit`
*   **Frontend**: HTML5, CSS3 Variables (Stitch Premier Design System, Dark Mode support), JavaScript (GSAP 3, Chart.js)

---

## 📦 Getting Started

### Prerequisites
*   Python 3.13+
*   Docker & Docker Compose (for containerized deployments)
*   PostgreSQL & Redis (if running locally without Docker)

### Local Development Setup
1.  **Clone the Repository** and navigate to the project directory.
2.  **Create and Activate a Virtual Environment**:
    ```bash
    python -m venv venv
    venv\Scripts\activate   # On Windows
    source venv/bin/activate  # On macOS/Linux
    ```
3.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```
4.  **Configure Environment**:
    Copy `.env.example` to `.env` and fill out your local credentials:
    ```bash
    cp .env.example .env
    ```
5.  **Initialize Database & Run Server**:
    ```bash
    python manage.py makemigrations
    python manage.py migrate
    python manage.py runserver
    ```

### Docker Compose Quickstart
Start all services (Django web app, PostgreSQL database, and Redis cache) with a single command:
```bash
docker-compose up -d --build
```
The application will build, apply migrations, and be available at `http://localhost:8000`.

---

## 🧪 Testing
Run the complete automated test suite (including auth, RBAC, REST API, audit logs, and performance caching validation):
```bash
python manage.py test
```

Generate a test coverage report:
```bash
coverage run manage.py test
coverage report -m
```
