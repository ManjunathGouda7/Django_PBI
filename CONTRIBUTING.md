# Contributing to APEX BI Studio

Thank you for your interest in contributing to APEX BI Studio! This guide covers setup, testing, and contribution standards.

---

## 🛠️ Local Development Setup

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/ManjunathGouda7/Django_PBI.git
   cd Django_PBI
   ```

2. **Set up Virtual Environment**:
   ```bash
   python -m venv venv
   # Windows:
   .\venv\Scripts\activate
   # Linux/macOS:
   source venv/bin/activate
   ```

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Apply Migrations & Start Server**:
   ```bash
   cd BI
   python manage.py migrate
   python manage.py runserver 127.0.0.1:8000
   ```

---

## 🧪 Running Automated Tests

Run the full automated test suite:
```bash
python manage.py test analytics --verbosity=2
```

Using PowerShell CLI:
```powershell
.\scripts\manage.ps1 test
```

---

## 📦 Building Standalone Windows Executable (.exe)

```cmd
.\Build_EXE.bat
```
The compiled standalone executable will be located in `BI/dist/ApexBIStudio/ApexBIStudio.exe`.

---

## 🐳 Docker Deployment

To launch the multi-container stack (PostgreSQL, Redis, Celery Worker, MongoDB, and Django Web App):
```bash
docker-compose up --build
```
Check health:
```bash
curl http://localhost:8000/health/
```
