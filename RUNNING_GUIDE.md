# APEX BI STUDIO — COMPLETE EXECUTION & USER GUIDE

Welcome to **APEX BI Studio** (Django Telemetry Analytics & Power BI Interactive Studio). This guide provides step-by-step instructions on how to run, build, and deploy the application **with the Standalone Executable (.exe)**, **directly through Source Code (Python Environment)**, and **via Docker Containers**.

---

## 📋 TABLE OF CONTENTS
1. [Overview & Tech Architecture](#1-overview--tech-architecture)
2. [Method 1: Running via Standalone Executable (.exe)](#method-1-running-via-standalone-executable-exe)
   - [How to Launch the Executable](#how-to-launch-the-executable)
   - [How to Rebuild the Executable (.exe)](#how-to-rebuild-the-executable-exe)
3. [Method 2: Running directly through Source Code](#method-2-running-directly-through-source-code)
   - [Prerequisites](#prerequisites)
   - [Step-by-Step Commands](#step-by-step-commands)
   - [Running Automated Unit Tests](#running-automated-unit-tests)
4. [Method 3: Running via Docker & Celery Services](#method-3-running-via-docker--celery-services)
5. [Key Application Endpoints & Features](#key-application-endpoints--features)

---

## 1. OVERVIEW & TECH ARCHITECTURE

- **Backend**: Python 3.12 / Django 6.1 / Django REST Framework (DRF) / Waitress WSGI
- **Analytics & Data Engine**: Pandas / NumPy Z-Score Anomaly Engine / PyMongo / openpyxl
- **Database & Storage**: SQLite3 (Local Dev & Executable) / MongoDB / Redis Cache
- **Task Queue**: Celery + Redis (Background upload parsing, joins, scheduled refreshes)
- **Frontend UI**: Power BI Obsidian Dark Desktop Theme (3-pane layout: Sidebar, Canvas, Viz Pane)

---

## METHOD 1: RUNNING VIA STANDALONE EXECUTABLE (.EXE)

The executable package allows end-users to launch APEX BI Studio on any Windows 10/11 computer **without needing Python installed**.

### How to Launch the Executable

You have two easy options to run the application:

#### Option A: 1-Click Root Shortcut
Double-click [`Launch_ApexBIStudio.bat`](file:///d:/Manju/PowerBI_Django/Launch_ApexBIStudio.bat) located in the project root directory.

#### Option B: Direct `.exe` File
Navigate to `BI/dist/ApexBIStudio/` and double-click **`ApexBIStudio.exe`**.

```text
d:\Manju\PowerBI_Django\
└── BI\
    └── dist\
        └── ApexBIStudio\
            ├── ApexBIStudio.exe   <-- Double-click to run!
            └── _internal\
```

#### What Happens When You Launch the Executable:
1. Automatically synchronizes database migrations (`db.sqlite3`).
2. Starts an embedded production Waitress WSGI server on `http://127.0.0.1:8000/`.
3. Opens your default web browser (Chrome, Edge, Firefox) automatically to APEX BI Studio.

---

### How to Rebuild the Executable (.exe)

If you modify source code and want to generate an updated `.exe` package, follow these steps:

#### 1-Click Rebuild Script:
Double-click [`Build_EXE.bat`](file:///d:/Manju/PowerBI_Django/Build_EXE.bat) in the project root directory.

#### Manual Command Line Rebuild:
Open PowerShell or Command Prompt in `d:\Manju\PowerBI_Django` and execute:

```powershell
# Navigate to the BI directory
cd BI

# Set Django settings environment variable
$env:DJANGO_SETTINGS_MODULE="BI.settings"

# Run PyInstaller build
..\mgenv\Scripts\pyinstaller.exe `
  --noconfirm `
  --onedir `
  --name="ApexBIStudio" `
  --add-data="analytics/templates;analytics/templates" `
  --add-data="analytics/static;analytics/static" `
  --hidden-import="analytics" `
  --hidden-import="rest_framework" `
  --hidden-import="rest_framework_simplejwt" `
  --hidden-import="drf_yasg" `
  --hidden-import="corsheaders" `
  --hidden-import="django_filters" `
  --hidden-import="pandas" `
  --hidden-import="openpyxl" `
  --hidden-import="waitress" `
  desktop_launcher.py
```

---

## METHOD 2: RUNNING DIRECTLY THROUGH SOURCE CODE

To develop, customize, or debug the code directly using the Python environment:

### Prerequisites
- Python 3.12+ installed
- Virtual environment (`mgenv`) configured with requirements

### Step-by-Step Commands

#### Step 1: Open Terminal and Navigate to `BI` Directory
```cmd
cd /d d:\Manju\PowerBI_Django\BI
```

#### Step 2: Activate Virtual Environment
```cmd
..\mgenv\Scripts\activate
```

#### Step 3: Check System Sanity
```cmd
python manage.py check
```

#### Step 4: Apply Database Migrations
```cmd
python manage.py migrate
```

#### Step 5: Start Development Web Server
```cmd
python manage.py runserver 0.0.0.0:8000
```

#### Step 6: Access Application in Browser
Open your browser and visit:
👉 **[http://127.0.0.1:8000/](http://127.0.0.1:8000/)**

---

### Running Automated Unit Tests

To run the complete automated test suite (32 unit & integration tests):

```cmd
cd /d d:\Manju\PowerBI_Django\BI
..\mgenv\Scripts\python.exe manage.py test analytics --verbosity=2
```

---

## METHOD 3: RUNNING VIA DOCKER & CELERY SERVICES

For production deployments or multi-container containerized execution:

### Step 1: Build and Launch Containers
From the root project directory `d:\Manju\PowerBI_Django`:

```bash
docker compose up --build -d
```

### Services Launched:
- `powerbi_django_web`: Main Django web application (Gunicorn) on port `8000`.
- `powerbi_celery_worker`: Background Celery task processor for joins & refreshes.
- `powerbi_celery_beat`: Celery scheduled task beat runner.
- `powerbi_mongodb`: MongoDB document database server on port `27017`.
- `powerbi_redis`: Redis cache and Celery broker on port `6379`.

### Step 2: Access Containerized Application
Open your browser and visit:
👉 **[http://localhost:8000/](http://localhost:8000/)**

### Step 3: Stop Docker Services
```bash
docker compose down
```

---

## KEY APPLICATION ENDPOINTS & FEATURES

| Feature Area | Endpoint / Command | Description |
| :--- | :--- | :--- |
| **Main UI Studio** | `GET /` | 3-Pane Power BI Obsidian Dark layout shell |
| **Login / Register** | `GET/POST /login/` | Secure authentication portal with session persistence |
| **JWT Token Auth** | `POST /api/token/` | Obtain JWT Access and Refresh tokens |
| **Datasets List & Upload** | `GET/POST /api/datasets/` | Drag-and-drop CSV, Excel, JSON upload with validation |
| **MongoDB Connector** | `POST /api/datasets/mongodb/` | Auto-fetch MongoDB collections into pandas DataFrames |
| **AI Data Chat Drawer** | `POST /api/datasets/<id>/chat/` | Natural Language Q&A assistant with 1-click chart generation |
| **Auto-Dashboard Builder**| `POST /api/datasets/<id>/auto-dashboard/` | 1-Click auto visual grid builder (Scatter, Bar, Matrix Table) |
| **Data Quality Cleaning** | `POST /api/datasets/<id>/clean/` | Impute missing mean/zero, drop nulls, deduplicate rows |
| **VLOOKUP Dataset Join** | `POST /api/datasets/join/` | Merge two datasets on shared key (Inner, Left, Full joins) |
| **Dashboard Sharing** | `POST /api/dashboards/<id>/share/` | Grant view/edit/export permissions to users |
| **Scheduled Refresh** | `POST /api/datasets/<id>/schedules/` | Automated background dataset refresh engine |
| **Audit Logs** | `GET /api/audit-logs/` | System-wide audit trail inspector |
| **Excel Export** | `GET /export-excel/<id>/` | Download multi-sheet workbook (.xlsx) with formatting |
| **Executive PDF Export** | `GET /export-pdf/<id>/` | Download executive report PDF template |
