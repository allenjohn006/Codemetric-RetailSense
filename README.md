# RetailSense

AI-powered retail analytics & demand forecasting platform. 
Drag-and-drop CSV upload dashboard that automatically cleans data, generates a full EDA report, detects seasonality patterns, and forecasts next quarter's sales using a time series model.

## 🚀 Quick Start (Docker)

To run the entire enterprise stack (PostgreSQL, Redis, Celery, FastAPI Backend, React Frontend):

```bash
docker-compose up --build -d
```

Once started:
- **Frontend Dashboard**: [http://localhost:5173](http://localhost:5173)
- **Backend API Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 🔑 Demo Account

A demo account is automatically seeded into the database on first startup. You can use this to log in immediately without signing up.

- **Email:** `demo@retailsense.io`
- **Password:** `Demo@RetailSense2024`

---

## 🏗️ Architecture Stack

- **Frontend**: React 18, Vite, TypeScript, Tailwind V4, `shadcn/ui`, React Router, TanStack Query, Recharts
- **Backend**: FastAPI, Python 3.11
- **Database**: PostgreSQL (via SQLAlchemy ORM)
- **Background Processing**: Celery + Redis
- **Data Engine**: Pandas, NumPy
- **Forecasting Engine**: Facebook Prophet
- **Exporting**: ReportLab (Professional PDF Generation)

## 📁 Data Uploads

You can upload the Kaggle `Superstore Sales CSV` or any standard sales export. The system handles files up to **500MB** and supports uploading **multiple files at once** (they will be auto-merged and cleaned).
