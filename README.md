# Apex BI Studio - Telemetry Analytics Platform

An enterprise-grade telemetry analytics & interactive dashboard platform built with **Django**, **Django REST Framework (DRF)**, **Pandas**, and **Chart.js**. Replicates Microsoft Power BI Desktop styling, multi-page reports, dynamic slicers, format panes, and automated data quality validation & outlier detection.

---

## 🌟 Architecture Highlights

### 1. Data Quality & Outlier Detection Engine
- **Multi-Algorithm Outlier Detection**:
  - **IQR (Interquartile Range)**: Identifies extreme value spikes beyond $1.5 \times IQR$ and $3.0 \times IQR$.
  - **Z-Score & Modified MAD**: Robust outlier detection for non-Gaussian wireless telemetry metrics.
- **Validation Pipeline**:
  - Min/Max numerical boundary constraints (e.g. $0 \le \text{PFO} \le 1000\text{mW}$).
  - Automatic duplicate row detection and removal.
  - Standardized unit mapping (`PFO [mW]`, `Rectified Power [W]`, `Received Power [W]`).

### 2. Service-Oriented Architecture
Clean separation of domain concerns in `BI/analytics/services/`:
- `data_import_service.py`: Automated ingestion of CSV, Excel, and JSON datasets.
- `data_validation_service.py`: Schema verification and data quality rules.
- `outlier_detection_service.py`: Outlier detection algorithms.
- `dashboard_service.py`: Fast chart aggregations, 2-sigma limit lines, and Chart.js payloads.

### 3. Modular Settings Architecture
Split Django configuration in `BI/BI/settings/`:
- `base.py`: Shared core configuration, app registry, security middleware, and logging.
- `development.py`: SQLite fallback, debug logging, and relaxed CORS.
- `production.py`: Strict SSL/HTTPS headers, database URL parsing, and environment secrets.

---

## 🚀 Quickstart Guide

### 1. Local Development Setup
```bash
# Clone repository
git clone https://github.com/ManjunathGouda7/Django_PBI.git
cd Django_PBI

# Activate virtual environment
mgenv\Scripts\activate  # Windows
source mgenv/bin/activate  # Linux/Mac

# Run Django system check & migrations
python BI/manage.py check
python BI/manage.py migrate

# Launch local server
python BI/manage.py runserver
```

### 2. Docker Deployment
```bash
docker-compose up --build
```
Access the application at `http://localhost:8000`.

---

## 🧪 Testing Suite

Run full automated unit and integration tests:
```bash
python BI/manage.py test analytics
```

---

## 📐 Data Contract Schema

Telemetry datasets exported to or consumed by Power BI Studio adhere to standard field names:

| Metric Name | Unit | Field Key | Description |
| :--- | :--- | :--- | :--- |
| `Timestamp` | Seconds | `Timestamp [Sec]` | Test run time vector |
| `Rectified Power` | Watts | `Rectified Power [W]` | Output DC power |
| `Received Power` | Watts | `Received Power [W]` | Input RF power |
| `PFO Metric` | mW | `PFO [mW]` | Peak power offset metric |
| `Board` | Text | `Board` | DUT / Board Identifier |
| `Outlier Flag` | Boolean | `_is_outlier` | Outlier indicator flag |
