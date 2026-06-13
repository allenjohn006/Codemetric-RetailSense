"""
RetailSense – /api/analyze
Stateless endpoint: accepts a CSV, auto-detects columns, and returns a rich
JSON payload for the interactive on-screen dashboard.

The existing PDF pipeline (/api/datasets, /api/reports) is NOT touched here.
"""
from __future__ import annotations

import io
import logging
import tempfile
from typing import Any

import numpy as np
import pandas as pd
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from auth import get_current_user
from models import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/analyze", tags=["analyze"])

# ── helpers ────────────────────────────────────────────────────────────────────

CURRENCY_FMT = "$"

SALES_KEYWORDS = {"sale", "revenue", "amount", "total", "price", "income", "earning", "profit", "turnover", "receipts"}
CATEGORY_KEYWORDS = {"category", "product", "type", "department", "segment", "class", "group", "brand", "item"}
DATE_KEYWORDS = {"date", "time", "period", "month", "day", "week", "year", "order", "transaction", "created"}


def _detect_date_column(df: pd.DataFrame) -> str | None:
    """
    Priority order:
    1. Combined YEAR + MONTH integer columns  →  synthetic 'date' column
    2. Any object column where ≥70 % of values parse as datetime
    3. Columns whose name contains a date keyword
    """
    cols_lower = {c.lower().strip(): c for c in df.columns}

    # 1. YEAR + MONTH synthetic date
    if "year" in cols_lower and "month" in cols_lower:
        yc, mc = cols_lower["year"], cols_lower["month"]
        years  = pd.to_numeric(df[yc], errors="coerce").fillna(0).astype(int)
        months = pd.to_numeric(df[mc], errors="coerce").fillna(1).astype(int)
        date_str = years.astype(str) + "-" + months.astype(str).str.zfill(2) + "-01"
        df["__date__"] = pd.to_datetime(date_str, errors="coerce")
        return "__date__"

    # 2. Parse each object column
    for col in df.columns:
        if df[col].dtype == "object":
            try:
                parsed = pd.to_datetime(df[col], errors="coerce", dayfirst=False)
                if parsed.notna().sum() > len(df) * 0.7:
                    return col
            except Exception:
                continue

    # 3. Name-based fallback
    for name in ["date", "order_date", "order date", "transaction_date", "ship_date", "created_at"]:
        if name in cols_lower:
            return cols_lower[name]

    return None


def _detect_sales_column(df: pd.DataFrame) -> str | None:
    """
    Priority order:
    1. Column name contains a sales keyword (picks largest-sum if ties)
    2. Largest-sum numeric column overall
    """
    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    if not numeric_cols:
        return None

    # keyword-named numeric columns
    kw_matches = [c for c in numeric_cols if any(kw in c.lower() for kw in SALES_KEYWORDS)]
    pool = kw_matches if kw_matches else numeric_cols

    # pick the one with the largest absolute sum (most likely to be revenue)
    return max(pool, key=lambda c: df[c].sum())


def _detect_category_column(df: pd.DataFrame) -> str | None:
    """
    Priority order:
    1. Object column whose name contains a category keyword
    2. Object column with the lowest cardinality below 50
    Returns None if nothing suitable is found (not a fatal error).
    """
    obj_cols = df.select_dtypes(include="object").columns.tolist()
    if not obj_cols:
        return None

    kw_matches = [c for c in obj_cols if any(kw in c.lower() for kw in CATEGORY_KEYWORDS)]
    if kw_matches:
        # among keyword matches, pick the one with lowest cardinality (most category-like)
        return min(kw_matches, key=lambda c: df[c].nunique())

    # low-cardinality fallback
    candidates = [(c, df[c].nunique()) for c in obj_cols if df[c].nunique() < 50]
    if candidates:
        return min(candidates, key=lambda x: x[1])[0]

    return None


def _clean_sales_col(series: pd.Series) -> pd.Series:
    """Strip currency symbols / commas and coerce to float."""
    if series.dtype == "object":
        series = series.astype(str).str.replace(r"[^\d.\-]", "", regex=True)
    return pd.to_numeric(series, errors="coerce").fillna(0.0)


def _moving_average_forecast(monthly: pd.Series, periods: int = 12, window: int = 6) -> list[dict]:
    """
    6-month moving average with ±20 % confidence band.
    `monthly` must be a pd.Series indexed by period strings ("YYYY-MM").
    """
    values = monthly.values
    window = min(window, len(values))
    avg = float(np.mean(values[-window:])) if window > 0 else 0.0

    last_period = monthly.index[-1]  # e.g. "2024-12"
    last_dt = pd.to_datetime(last_period + "-01")

    forecast = []
    for i in range(1, periods + 1):
        future_dt = last_dt + pd.DateOffset(months=i)
        period_str = future_dt.strftime("%Y-%m")
        forecast.append({
            "period":   period_str,
            "forecast": round(avg, 2),
            "lower":    round(avg * 0.80, 2),
            "upper":    round(avg * 1.20, 2),
        })
    return forecast


def _generate_insights(
    monthly: pd.Series,
    category_breakdown: list[dict],
    anomalies: list[dict],
    total_sales: float,
) -> list[str]:
    insights: list[str] = []

    if monthly.empty:
        insights.append("Not enough monthly data to generate insights.")
        return insights

    peak_period  = monthly.idxmax()
    trough_period = monthly.idxmin()
    peak_val  = monthly.max()
    trough_val = monthly.min()

    insights.append(
        f"Peak sales occurred in {peak_period} "
        f"(${peak_val:,.0f}). "
        f"Consider increasing inventory and marketing spend ahead of this period."
    )
    insights.append(
        f"Lowest sales recorded in {trough_period} "
        f"(${trough_val:,.0f}). "
        f"This may be an ideal window for clearance promotions or demand-generation campaigns."
    )

    # YoY growth (if more than 12 months)
    if len(monthly) >= 13:
        last_12  = monthly.iloc[-12:].sum()
        prev_12  = monthly.iloc[-24:-12].sum() if len(monthly) >= 24 else monthly.iloc[:-12].sum()
        if prev_12 > 0:
            growth = (last_12 - prev_12) / prev_12 * 100
            direction = "grew" if growth >= 0 else "declined"
            insights.append(
                f"Year-over-year revenue {direction} by {abs(growth):.1f} % "
                f"compared to the previous period."
            )

    # Top category
    if category_breakdown:
        top = category_breakdown[0]
        share = (top["total_sales"] / total_sales * 100) if total_sales else 0
        insights.append(
            f"Top-performing category: \"{top['category']}\" "
            f"contributes {share:.1f} % of total revenue (${top['total_sales']:,.0f})."
        )
        if len(category_breakdown) >= 2:
            bottom = category_breakdown[-1]
            insights.append(
                f"Lowest-performing category: \"{bottom['category']}\" "
                f"(${bottom['total_sales']:,.0f}). "
                f"Consider evaluating whether it merits continued investment."
            )

    # Anomalies
    if anomalies:
        anomaly_list = ", ".join(a["period"] for a in anomalies[:3])
        insights.append(
            f"Unusual sales spikes or drops detected in: {anomaly_list}. "
            f"Investigate whether these were driven by promotions, stockouts, or external events."
        )

    return insights


# ── main endpoint ──────────────────────────────────────────────────────────────

@router.post("")
async def analyze_csv(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Accept a single CSV upload and return a JSON analysis payload.
    No data is persisted; the existing PDF pipeline is completely unchanged.
    """
    if not (file.filename or "").lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are supported.")

    raw = await file.read()
    try:
        df = pd.read_csv(io.BytesIO(raw), low_memory=False)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Could not parse CSV: {exc}")

    # ── 1. Detect date column ──────────────────────────────────────────────────
    date_col = _detect_date_column(df)
    if date_col is None:
        return {
            "error": (
                "Could not detect a date column. "
                "Please ensure your CSV has a date column (or YEAR + MONTH columns) "
                "and a numeric sales column."
            )
        }

    # Parse / normalise dates
    if date_col == "__date__":
        # Already created by _detect_date_column
        df["__date__"] = pd.to_datetime(df["__date__"], errors="coerce")
    else:
        df["__date__"] = pd.to_datetime(df[date_col], errors="coerce", dayfirst=False)

    df = df.dropna(subset=["__date__"])

    # ── 2. Detect sales column ────────────────────────────────────────────────
    sales_col = _detect_sales_column(df)
    if sales_col is None:
        return {
            "error": (
                "Could not detect a sales column. "
                "Please ensure your CSV has a numeric column representing sales, "
                "revenue, or amount."
            )
        }

    df["__sales__"] = _clean_sales_col(df[sales_col])

    # ── 3. Detect category column (optional) ──────────────────────────────────
    category_col = _detect_category_column(df)

    # ── 4. Summary ────────────────────────────────────────────────────────────
    total_sales     = float(df["__sales__"].sum())
    num_categories  = int(df[category_col].nunique()) if category_col else 0
    period_start    = df["__date__"].min().strftime("%Y-%m-%d")
    period_end      = df["__date__"].max().strftime("%Y-%m-%d")

    summary = {
        "total_records":  len(df),
        "total_sales":    round(total_sales, 2),
        "num_categories": num_categories,
        "period_start":   period_start,
        "period_end":     period_end,
        "currency_symbol": CURRENCY_FMT,
    }

    # ── 5. Monthly trend ──────────────────────────────────────────────────────
    df["__period__"] = df["__date__"].dt.to_period("M").astype(str)
    monthly_series = (
        df.groupby("__period__")["__sales__"]
        .sum()
        .sort_index()
    )
    monthly_trend = [
        {"period": period, "total_sales": round(float(val), 2)}
        for period, val in monthly_series.items()
    ]

    # ── 6. Category breakdown ─────────────────────────────────────────────────
    category_breakdown: list[dict] = []
    if category_col:
        cat_series = (
            df.groupby(category_col)["__sales__"]
            .sum()
            .sort_values(ascending=False)
        )
        category_breakdown = [
            {"category": str(cat), "total_sales": round(float(val), 2)}
            for cat, val in cat_series.items()
        ]

    # ── 7. Anomaly detection (> 2 σ from mean) ────────────────────────────────
    if len(monthly_series) >= 3:
        mean = monthly_series.mean()
        std  = monthly_series.std()
        anomalies = [
            {"period": p, "value": round(float(v), 2)}
            for p, v in monthly_series.items()
            if abs(v - mean) > 2 * std
        ]
    else:
        anomalies = []

    # ── 8. Forecast (6-month MA, 12 periods ahead) ────────────────────────────
    if len(monthly_series) >= 1:
        forecast = _moving_average_forecast(monthly_series, periods=12, window=6)
    else:
        forecast = []

    # ── 9. Insights ───────────────────────────────────────────────────────────
    insights = _generate_insights(monthly_series, category_breakdown, anomalies, total_sales)

    return {
        "summary":            summary,
        "monthly_trend":      monthly_trend,
        "category_breakdown": category_breakdown,
        "forecast":           forecast,
        "insights":           insights,
        "anomalies":          anomalies,
    }
