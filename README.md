#  RetailSense Task-3 (Retail Sales Analysis & Forecasting)

AI-powered retail analytics & demand forecasting platform. Drag-and-drop CSV upload dashboard that automatically cleans data, generates a full Exploratory Data Analysis (EDA) report, detects seasonality patterns, and forecasts sales using advanced time series models.

---

##  Features

- **Multi-File CSV Upload & Merging**: Drag-and-drop one or multiple CSV sales exports (up to 500MB total). The system auto-merges, standardizes column formats, and cleans string values/whitespace.
- **Smart Data Cleaning**: Automatic type coercion, parsing of explicit `YEAR`/`MONTH` or implicit date columns, removal of currency symbols or thousands separators, and missing value cleanup.
- **Seasonality & Trend Detection**: Analyzes yearly, quarterly, and monthly trends. Detects business anomalies via IQR method and highlights peak/trough periods.
- **Demand Forecasting**: Generates 12-month demand forecasts with confidence intervals using **Facebook Prophet** (falls back to a robust 6-month Moving Average if Prophet is unavailable or data is insufficient).
- **Executive PDF Report**: Compiles all insights, KPIs, seasonality trends, and forecasts into a beautifully styled, print-ready PDF using **ReportLab**.
- **Interactive UI**: Sleek modern dashboard built with Tailwind v4, shadcn/ui, and Lucide Icons.

---

##  Architecture & Tech Stack

RetailSense is built using a modern, loosely coupled stack optimized for data processing and asynchronous execution:

###  Frontend
| Technology | Purpose |
|---|---|
| **React 18 + Vite + TypeScript** | Core framework and build tooling |
| **Tailwind CSS v4** | Utility-first styling |
| **shadcn/ui + Lucide Icons** | UI components and icons |
| **TanStack Query (React Query)** | Server state management, polling |
| **Axios** | HTTP client with auth token injection |
| **react-dropzone** | CSV drag-and-drop upload |

###  Backend
| Technology | Purpose |
|---|---|
| **FastAPI** | High-performance async Python API |
| **PostgreSQL** | Primary data store (via SQLAlchemy ORM) |
| **Celery** | Async task queue for pipeline execution |
| **Redis** | Celery message broker & result backend |
| **Pandas + NumPy** | Data cleaning & EDA engine |
| **Facebook Prophet** | Time series forecasting |
| **scikit-learn + scipy** | Statistical analysis |
| **ReportLab** | Professional PDF generation |
| **python-jose + passlib** | JWT auth and password hashing |

###  Infrastructure
| Technology | Purpose |
|---|---|
| **Docker + Docker Compose** | Containerized multi-service orchestration |
| **PostgreSQL 15** | Managed via official Docker image |
| **Redis 7** | Managed via official Docker image |

---

##  Quick Start (Docker Compose — Recommended)

The easiest way to run the entire enterprise stack (PostgreSQL, Redis, Celery Worker, FastAPI, and React Frontend) in one command:

```bash
# From the project root directory
docker-compose up --build -d
```

### Accessing the Application
| Service | URL |
|---|---|
| **Frontend Dashboard** | http://localhost:5173 |
| **Backend API** | http://localhost:8000 |
| **API Interactive Docs** | http://localhost:8000/docs |

###  Demo Account
A demo account is automatically seeded into the database on first startup:
- **Email**: `demo@retailsense.io`
- **Password**: `Demo@RetailSense2024`

### Stopping the Stack
```bash
docker-compose down
```

---

##  Running Locally (Manual Setup)

If you prefer to run the components directly on your system without Docker:

### Prerequisites
- Python 3.11+
- Node.js 20+
- PostgreSQL 15+
- Redis Server 7+

### 1. Database & Redis Setup
- Start PostgreSQL and create a database named `retailsense`.
- Start Redis (default port `6379`).

### 2. Configure Environment
```bash
# From the project root
cp backend/.env.example backend/.env
```
Open `backend/.env` and verify the connection strings for your local PostgreSQL and Redis instances.

### 3. Install & Run the Backend API
```bash
cd backend
python -m venv venv
# Windows:
venv\Scripts\activate
# macOS/Linux:
# source venv/bin/activate

pip install -r requirements.txt
uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

### 4. Run the Celery Worker
In a **new terminal** (with the same virtual environment activated):
```bash
cd backend
celery -A worker.celery_app worker --loglevel=info
```

### 5. Run the Frontend Development Server
In a **new terminal**:
```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173) to view the application.

---

##  Project Structure

```
RetailSense/
├── backend/
│   ├── main.py              # FastAPI application entry point
│   ├── config.py            # Pydantic settings (reads .env)
│   ├── database.py          # SQLAlchemy engine & session
│   ├── models.py            # ORM models (User, Dataset, Report)
│   ├── schemas.py           # Pydantic request/response schemas
│   ├── auth.py              # JWT auth & password hashing
│   ├── pipeline.py          # CSV cleaning & EDA pipeline
│   ├── forecasting.py       # Prophet & moving average forecasting
│   ├── pdf_generator.py     # ReportLab PDF report generator
│   ├── tasks.py             # Celery task definitions
│   ├── worker.py            # Celery app configuration
│   ├── requirements.txt     # Python dependencies
│   ├── Dockerfile           # Backend Docker image
│   └── routers/
│       ├── auth_router.py   # /api/auth endpoints
│       ├── upload_router.py # /api/datasets endpoints
│       └── report_router.py # /api/reports endpoints
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   │   ├── Login.tsx    # Login & signup page
│   │   │   └── Dashboard.tsx# Main upload & analysis dashboard
│   │   ├── components/ui/   # Reusable shadcn/ui components
│   │   ├── lib/
│   │   │   └── api.ts       # Axios API client with auth interceptor
│   │   └── App.tsx          # Root component with routing
│   ├── vite.config.ts       # Vite config + API proxy
│   └── Dockerfile           # Frontend Docker image
├── docker-compose.yml       # Multi-service orchestration
└── README.md
```

---

##  Supported CSV Formats

The pipeline auto-detects and handles:
- **Date columns**: Any column named `date`, `order_date`, `transaction_date`, `ship_date`, etc.
- **Year/Month columns**: Separate `YEAR` and `MONTH` integer columns (e.g., Retail & Warehouse datasets).
- **Sales columns**: Any column containing `sales`, `revenue`, `amount`, `profit`, or `transfers`.
- **Category columns**: Any column named `item type`, `category`, `product_category`, or `sub-category`.
- **Currency formats**: Values prefixed with `$`, `€`, `£` or containing commas are automatically stripped and converted to numeric.

