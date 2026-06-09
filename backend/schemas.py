from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime


# ─── Auth Schemas ─────────────────────────────────────────────
class UserCreate(BaseModel):
    email: EmailStr
    full_name: str
    password: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    is_demo: bool
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


# ─── Dataset Schemas ──────────────────────────────────────────
class DatasetResponse(BaseModel):
    id: str
    name: str
    original_filenames: str
    row_count: Optional[int]
    status: str
    task_id: Optional[str]
    error_message: Optional[str]
    created_at: datetime
    completed_at: Optional[datetime]

    class Config:
        from_attributes = True


class DatasetListResponse(BaseModel):
    datasets: list[DatasetResponse]


# ─── Report / Analysis Schemas ────────────────────────────────
class SummaryStats(BaseModel):
    total_rows: int
    date_range: Optional[dict] = None
    total_sales: Optional[float] = None
    total_warehouse_sales: Optional[float] = None
    num_categories: Optional[int] = None
    num_suppliers: Optional[int] = None
    top_category: Optional[str] = None
    yoy_growth: Optional[float] = None


class TrendPoint(BaseModel):
    date: str
    value: float
    is_anomaly: bool = False


class CategoryBreakdown(BaseModel):
    name: str
    total_sales: float
    growth_rate: Optional[float] = None


class ForecastPoint(BaseModel):
    date: str
    forecast: float
    lower_bound: Optional[float] = None
    upper_bound: Optional[float] = None


class SeasonalityEntry(BaseModel):
    period: str  # e.g. "January", "Q1"
    value: float


class InsightItem(BaseModel):
    title: str
    description: str
    severity: str = "info"  # info, warning, success


class ReportResponse(BaseModel):
    id: str
    dataset_id: str
    summary_stats: Optional[dict] = None
    eda_data: Optional[dict] = None
    forecast_data: Optional[dict] = None
    seasonality_data: Optional[dict] = None
    category_data: Optional[dict] = None
    insights: Optional[dict] = None
    created_at: datetime

    class Config:
        from_attributes = True


class TaskStatusResponse(BaseModel):
    dataset_id: str
    status: str
    progress: Optional[str] = None
    error_message: Optional[str] = None
