# 🚀 DevOps & CI/CD Production Architecture Guide

This document outlines the DevOps, Docker containerization, and GitHub Actions CI/CD setup for the **Power BI Django Telemetry Analytics Platform**.

---

## 🐋 1. Docker Containerization

The platform includes production multi-container orchestration via Docker & Docker Compose.

### Quick Start with Docker Compose:
```bash
# Build and launch all services (Django Web, MongoDB, Redis)
docker-compose up -d --build

# View container logs
docker-compose logs -f web

# Stop containers
docker-compose down
```

### Services Included in `docker-compose.yml`:
- **`web`**: Django WSGI App running Gunicorn server on port `8000`.
- **`mongo`**: Official MongoDB server instance on port `27017` with volume persistence (`mongo_data`).
- **`redis`**: Redis caching store on port `6379`.

---

## ⚡ 2. GitHub Actions CI/CD Pipeline

Location: `.github/workflows/django-ci-cd.yml`

On every `push` or `pull_request` to the `main` branch, GitHub Actions automatically executes:
1. **Environment Setup**: Provisions Python 3.11 runner with MongoDB test service.
2. **Dependency Installation**: Installs all required packages from `requirements.txt`.
3. **Django Integrity Verification**: Executes `python manage.py check` & migration dry-run checks.
4. **Syntax Compilation**: Compiles Python files to verify syntax integrity across all modules.
5. **Docker Build Validation**: Builds the production Docker image to verify container readiness.

---

## 🛡️ 3. Production Environment Variables (`.env`)

For deployment to cloud platforms (AWS EC2, DigitalOcean, Azure, Render, Heroku):

```ini
DEBUG=False
SECRET_KEY=your-production-django-secret-key-here
ALLOWED_HOSTS=yourdomain.com,127.0.0.1
MONGODB_URL=mongodb://localhost:27017
REDIS_URL=redis://localhost:6379/1
```

---

## 🌐 4. Nginx Reverse Proxy & SSL (Optional Production Setup)

Example Nginx server block to proxy traffic to Gunicorn on port `8000`:

```nginx
server {
    listen 80;
    server_name telemetry.yourcompany.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static/ {
        alias /app/BI/analytics/static/;
    }
}
```
