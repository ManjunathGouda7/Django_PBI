# ⚡ Apex BI Studio — Django Telemetry Analytics Platform

An enterprise-grade, high-performance telemetry analytics platform and interactive visual dashboard engine built with **Django 6.1**, **Django REST Framework**, **Pandas**, **NumPy**, **PyMongo**, and **Chart.js**.

---

## 🌟 Executive Features & Capabilities

- 📊 **Vectorized Scatter Telemetry Engine**: C-level `np.round()` serialization processing 37,500+ telemetry points in **~15ms**.
- 🔌 **MongoDB Server Connector & Offline Fallback**: Direct 500ms connection to MongoDB servers with offline fallback to local JSON dataset (`280,275 records`).
- 🔐 **Hardened Authentication & Security**: Route protection via `@login_required`, live password match confirmation, PBKDF2+SHA256 database password hashing, and Open Redirect protection.
- 👑 **Role-Based Access Control (RBAC)**: Supports `Administrator`, `Data Analyst`, and `Report Viewer` roles via `UserProfile` model.
- 🪄 **Natural Language Telemetry AI Q&A Assistant**: Instant query parsing in top ribbon header to auto-filter slicers and report cards.
- 📐 **Statistical Target Specification Limits**: Dynamic calculation of 2-sigma upper and lower specification threshold lines.
- 🛠️ **OpenAPI 3.0 Interactive Swagger Spec**: Live interactive API documentation at `/api/swagger/` and `/api/redoc/`.
- ⏱️ **1-Click CSV Export & Live Auto-Refresh**: Instant CSV telemetry streaming and automated polling options (5s, 10s, 30s).
- 🐋 **DevOps Docker Containerization**: Multi-stage `Dockerfile`, `docker-compose.yml` (Django, MongoDB, Redis), and GitHub Actions CI/CD pipeline.

---

## 🏗️ Architecture & Technology Stack

| Layer | Technologies Used |
| :--- | :--- |
| **Backend Core** | Django 6.1, Gunicorn WSGI Server, Python 3.11+ |
| **REST API Engine** | Django REST Framework (DRF), JWT SimpleJWT, DRF Yasg (Swagger) |
| **Data Engine** | Pandas, NumPy, PyMongo |
| **Caching & Async Tasks**| Redis Cache, Celery Async Task Workers |
| **Frontend UI Shell** | Vanilla JavaScript (ES6+), CSS3 Obsidian Dark & Light Design System, Chart.js with Zoom Plugin |
| **Database** | SQLite3 (Development) / PostgreSQL (Production) |
| **DevOps & CI/CD** | Docker, Docker Compose, GitHub Actions Pipeline |

---

## ⚙️ Local Development & Setup Guide

### 1. Prerequisites
- Python 3.10+
- Virtual environment (`mgenv` or `venv`)
- Git

### 2. Quick Setup Commands
```bash
# Clone the repository
git clone https://github.com/ManjunathGouda7/Django_PBI.git
cd Django_PBI

# Activate virtual environment (Windows PowerShell)
d:\Manju\PowerBI_Django\mgenv\Scripts\activate

# Install pinned production dependencies
pip install -r requirements.txt

# Run database migrations
cd BI
python manage.py migrate

# Create admin superuser (optional)
python manage.py createsuperuser

# Start Django development server
python manage.py runserver 0.0.0.0:8000
```

Access the platform in your browser:
- **Main Studio App**: `http://127.0.0.1:8000/`
- **Login Portal**: `http://127.0.0.1:8000/login/`
- **Swagger Interactive API Spec**: `http://127.0.0.1:8000/api/swagger/`
- **ReDoc API Spec**: `http://127.0.0.1:8000/api/redoc/`
- **Django Admin**: `http://127.0.0.1:8000/admin/`

---

## 🧪 Running Automated Unit Tests

To run the automated Django test suite covering models, schema inference, permissions, and auth views:

```bash
python manage.py test analytics
```

---

## 🐋 Running with Docker & Docker Compose

Launch Django App, MongoDB server, and Redis cache with 1 command:

```bash
# Launch multi-container stack
docker-compose up -d --build

# View container logs
docker-compose logs -f web

# Shutdown stack
docker-compose down
```

---

## 🔐 Environment Variables Reference (`.env`)

Create a `.env` file in the project root:

```ini
DEBUG=False
SECRET_KEY=your-production-django-secret-key-here
ALLOWED_HOSTS=127.0.0.1,localhost
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:8000
MONGODB_URL=mongodb://localhost:27017
REDIS_URL=redis://localhost:6379/1
LOG_LEVEL=INFO
```

---

## 📡 REST API Reference

| Endpoint | Method | Description |
| :--- | :---: | :--- |
| **`/api/v1/datasets/`** | `GET` / `POST` | List and upload telemetry datasets |
| **`/api/v1/dashboards/`** | `GET` / `POST` | List and create visual dashboards |
| **`/api/v1/widgets/`** | `GET` / `POST` / `PUT` / `DELETE` | Visual card CRUD operations |
| **`/api/token/`** | `POST` | Obtain JWT Access and Refresh Tokens |
| **`/api/swagger/`** | `GET` | Interactive Swagger API documentation |
| **`/export-csv/<dataset_id>/`** | `GET` | 1-Click CSV telemetry data stream |

---

## 📄 License & Author

Developed by **Manjunath Gouda** (`ManjunathGouda7`).
Licensed under the **MIT License**.
