# 📊 Django Power BI Studio

A feature-complete, modern Business Intelligence & Analytics web platform inspired by Microsoft Power BI, built using **Django**, **Pandas**, **MongoDB (PyMongo)**, **Chart.js**, and custom **Obsidian Dark** & **Power BI Classic** design themes.

![Django Power BI Studio](https://img.shields.io/badge/Django-6.1-092E20?style=for-the-badge&logo=django)
![MongoDB](https://img.shields.io/badge/MongoDB-Data_Server-47A248?style=for-the-badge&logo=mongodb)
![Pandas](https://img.shields.io/badge/Pandas-Data_Engine-150458?style=for-the-badge&logo=pandas)

---

## ⚙️ Quick Start with MongoDB

```bash
# Install packages
pip install -r requirements.txt

# Run migrations
python manage.py makemigrations analytics
python manage.py migrate

# Run dev server
python manage.py runserver 0.0.0.0:8000
```

1. Open **`http://127.0.0.1:8000/`**.
2. Click **Get Data** > Select **MongoDB Server** tab.
3. Enter Connection URI (`mongodb://localhost:27017` or Atlas URL), Database Name, and Collection Name.
4. Click **Connect & Import MongoDB Collection**.
