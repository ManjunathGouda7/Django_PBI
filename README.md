# 📊 Django Power BI Studio

A feature-complete, high-performance Business Intelligence & Telemetry Analytics platform inspired by Microsoft Power BI, built using **Django**, **Pandas**, **MongoDB (PyMongo)**, **NumPy**, **Chart.js**, and custom **Obsidian Dark** & **Power BI Classic** design themes.

![Django Power BI Studio](https://img.shields.io/badge/Django-6.1-092E20?style=for-the-badge&logo=django)
![MongoDB](https://img.shields.io/badge/MongoDB-Data_Server-47A248?style=for-the-badge&logo=mongodb)
![Pandas](https://img.shields.io/badge/Pandas-Data_Engine-150458?style=for-the-badge&logo=pandas)
![Chart.js](https://img.shields.io/badge/Chart.js-Visuals-FF6384?style=for-the-badge&logo=chartdotjs)
![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python)
![OpenAPI 3.0](https://img.shields.io/badge/OpenAPI-3.0_Swagger-85EA2D?style=for-the-badge&logo=openapi-initiative)

---

## 🔐 User Authentication & Authorization Architecture

The platform features comprehensive authentication and role-based authorization:

### 1. User Ownership & Dataset Privacy
- **User Models**: Integrates Django's `User` model with `Dataset.owner` and `Dashboard.owner`.
- **Public & Private Datasets**: Supports private user-owned datasets as well as public shared team datasets.

### 2. Granular Sharing Permissions (`DatasetSharePermission`)
- **`read`**: Read-only visualization and report access.
- **`edit`**: Ability to modify datasets, configure visual cards, and adjust DAX aggregations.
- **`admin`**: Full control including sharing permissions and deletion rights.

### 3. Authentication REST APIs
- `POST /api/auth/register/` — Register a new user account.
- `POST /api/auth/login/` — Authenticate and start a session.
- `POST /api/auth/logout/` — End current user session.
- `GET /api/auth/me/` — Retrieve active user profile, permissions, and dataset ownership details.

---

## 🔥 Key Features

### 1. Data Ingestion ("Get Data")
* **MongoDB Server Connector**: Directly connect to local or cloud MongoDB databases (`mongodb://192.168.100.123:27017` or Atlas). Automatically flattens BSON/JSON telemetry collections into clean Pandas DataFrames with a fast 500ms timeout check + local JSON fallback (`data/GRL.25MPLA.json`).
* **Custom Dataset Uploads**: Ingest `.csv` and `.xlsx` (Excel) spreadsheets.
* **Automatic Column Schema Inference**: Automatically detects column types:
  * `#` **Numeric**: `Rectified Power [W]`, `PFO [mW]`, `Timestamp [Sec]`
  * `Aa` **Categorical**: `Board`, `PowerMode`, `Position`, `DUT`, `CRX`, `RUN`
  * `📅` **Date & Time**: `Transaction_Date`, `Order_Date`

### 2. High-Performance Scatter Engine & Vectorized Calculations
* **NumPy C-Level Vectorization**: Point serialization powered by `np.round()`, serializing 37,500+ scatter data points across 15 series groups in **~15ms**.
* **Interactive Drag-to-Zoom & Pan**: Drag a selection rectangle on scatter plots to zoom into specific power clusters (e.g. `0W–5W`). Scroll wheel to zoom in/out, double-click to reset view.
* **Click-to-Filter (Point Cross-Filtering)**: Clicking any scatter point or legend item cross-filters all other dashboard cards and updates slicer pills live across the canvas.
* **Exact Power BI Tooltip**: Custom card tooltips matching Power BI Desktop styling (`Board`, `Rectified Power [W]`, `PFO [mW]`).

### 3. Interactive Report Canvas & Visual Card Selection
* **Visual Card Selection & Edit Persistence**: Highlighting visual cards with gold active borders. Changing X/Y axes or title updates the selected card in place.
* **`+ New Visual` Mode Switcher**: Explicit mode toggle bar to switch between editing existing cards and creating brand-new visual cards.
* **Multiple Visual Types**: Scatter Plots, Telemetry Line Charts, Bar Charts, Column Charts, Pie/Donut Charts, KPI Scorecards, and Matrix Tables.

### 4. Interactive Slicers & Filters Pane
* **Categorical Slicers**: Select all, search filter, item row counts (`GTPT118 — 3,009`), clear buttons, and active filter cards.
* **Dynamic Range Metadata**: Automatic `min` and `max` detection for numeric filter range sliders.

### 5. Color Themes & 1-Click High-Res Export
* **5 Built-in Themes**:
  * 🖤 *Obsidian Dark (Power BI Dark Mode)*
  * 💛 *Power BI Classic (Yellow/Navy)*
  * 💜 *Cyberpunk Neon*
  * 💚 *Emerald Teal*
  * 🤍 *Slate Light (with persistent user theme selection)*
* **1-Click High-Res Canvas Export**: Instant 2x resolution PNG screenshot / PDF export via `html2canvas`.

---

## 🗄️ Enhanced Dataset Models

```python
class Dataset(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='datasets', null=True, blank=True)
    name = models.CharField(max_length=255)
    file_type = models.CharField(max_length=20, choices=FILE_TYPES, default='csv')
    row_count = models.IntegerField(default=0)
    column_count = models.IntegerField(default=0)
    column_schema = models.JSONField(default=dict)
    is_public = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

class DatasetColumn(models.Model):
    dataset = models.ForeignKey(Dataset, on_delete=models.CASCADE, related_name='columns')
    name = models.CharField(max_length=255)
    data_type = models.CharField(max_length=20, choices=DATA_TYPES)
    distinct_count = models.IntegerField(default=0)
    null_count = models.IntegerField(default=0)
    min_value = models.CharField(max_length=255, blank=True, null=True)
    max_value = models.CharField(max_length=255, blank=True, null=True)
    sample_values = models.JSONField(default=list, blank=True)

class DatasetSharePermission(models.Model):
    dataset = models.ForeignKey(Dataset, on_delete=models.CASCADE, related_name='permissions')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='shared_datasets')
    permission_level = models.CharField(max_length=20, choices=PERMISSION_LEVELS, default='read')
```

---

## 🛠️ Project Structure

```
PowerBI_Django/
├── BI/
│   ├── BI/
│   │   ├── settings.py           # Environment variable parsing, Django CACHES, database config
│   │   ├── urls.py               # Root URL routing
│   │   └── wsgi.py
│   ├── analytics/
│   │   ├── models.py             # Dataset, DatasetColumn, DatasetSharePermission, Dashboard, Widget models
│   │   ├── services.py           # DatasetEngine: Vectorized NumPy scatter engine, MongoDB connector, memory cache
│   │   ├── views.py              # HTML shell controller, export view, SVG favicon view
│   │   ├── api_views.py          # REST API endpoints & Auth handlers
│   │   ├── urls.py               # App URL routing
│   │   ├── static/analytics/
│   │   │   ├── css/powerbi.css   # Dark Modern Obsidian design system
│   │   │   └── js/powerbi_app.js # Reactive JavaScript state manager & Chart.js engine
│   │   └── templates/analytics/
│   │       ├── base.html         # HTML5 document shell with Chart.js zoom plugin
│   │       ├── index.html        # Main 3-pane Power BI Studio UI
│   │       └── export_pdf.html   # Clean print & PDF export template
│   ├── manage.py
│   ├── db.sqlite3
│   └── .env                      # Environment variable configuration
├── data/
│   └── GRL.25MPLA.json           # Offline fallback telemetry dataset (280,275 records)
├── requirements.txt
└── README.md
```

---

## ⚙️ Installation & Setup Guide

### 1. Prerequisites
* Python 3.10+
* Virtual Environment (`venv` or `mgenv`)
* MongoDB Server (Optional, local or MongoDB Atlas)

### 2. Environment Configuration
Create a `.env` file in `BI/`:
```ini
SECRET_KEY=django-insecure-key
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost
DATABASE_URL=sqlite:///db.sqlite3
REDIS_URL=redis://127.0.0.1:6379/0
MONGODB_URL=mongodb://192.168.100.123:27017
```

### 3. Install Dependencies & Migrate
```bash
mgenv\Scripts\activate
cd BI
pip install -r requirements.txt
python manage.py makemigrations analytics
python manage.py migrate
```

### 4. Run Development Server
```bash
python manage.py runserver 0.0.0.0:8000
```

Open your browser and navigate to **`http://127.0.0.1:8000/`**.

---

## 🔌 REST API & Swagger Reference

Interactive OpenAPI 3.0 / Swagger documentation is available at **`/api/docs/`**.

| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `/api/auth/register/` | `POST` | Register a new user account |
| `/api/auth/login/` | `POST` | User login session authentication |
| `/api/auth/logout/` | `POST` | End user session |
| `/api/auth/me/` | `GET` | Get current logged-in user profile & ownership |
| `/api/datasets/` | `GET` | List all available datasets |
| `/api/datasets/` | `POST` | Upload a new `.csv` / `.xlsx` dataset file |
| `/api/datasets/mongodb/` | `POST` | Connect & import MongoDB server collection |
| `/api/datasets/<id>/` | `GET` | Get dataset details & column schema |
| `/api/datasets/<id>/rows/` | `GET` | Get paginated raw rows (supports `?search=` and `?sort_col=`) |
| `/api/datasets/<id>/filter-values/` | `GET` | Get unique column values and counts for slicers (supports `?slicers=`) |
| `/api/dashboards/` | `GET` | List all dashboards |
| `/api/dashboards/` | `POST` | Create a new dashboard |
| `/api/dashboards/<id>/` | `GET` | Get dashboard details, widgets, & rendered query payload (supports `?slicers=`) |
| `/api/dashboards/<id>/widgets/` | `POST` | Add a new visual card to a dashboard |
| `/api/widgets/<id>/` | `PUT` / `DELETE` | Update or delete a visual card |
| `/api/docs/` | `GET` | OpenAPI 3.0 / Swagger interactive API specification |
| `/export/<id>/` | `GET` | View clean printable dashboard report |
