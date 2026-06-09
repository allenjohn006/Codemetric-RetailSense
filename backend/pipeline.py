"""
RetailSense Data Processing Pipeline
Handles CSV loading, cleaning, EDA, and feature extraction.
"""
import pandas as pd
import numpy as np
from typing import Optional


def load_and_merge_csvs(file_paths: list[str]) -> pd.DataFrame:
    """Load one or more CSV files and concatenate them into a single DataFrame."""
    frames = []
    for path in file_paths:
        try:
            df = pd.read_csv(path, low_memory=False)
            frames.append(df)
        except Exception as e:
            raise ValueError(f"Error reading {path}: {e}")

    if not frames:
        raise ValueError("No valid CSV files provided.")
    
    combined = pd.concat(frames, ignore_index=True)
    return combined


def auto_detect_and_parse_dates(df: pd.DataFrame) -> pd.DataFrame:
    """
    Auto-detect date columns or create a date from YEAR/MONTH columns.
    Returns a DataFrame with a 'date' column of datetime type.
    """
    cols_lower = {c.lower().strip(): c for c in df.columns}

    # Case 1: Explicit YEAR + MONTH columns (like Retail & Warehouse Sale dataset)
    if "year" in cols_lower and "month" in cols_lower:
        year_col = cols_lower["year"]
        month_col = cols_lower["month"]
        df["date"] = pd.to_datetime(
            df[year_col].astype(int).astype(str) + "-" + df[month_col].astype(int).astype(str) + "-01"
        )
        return df

    # Case 2: Look for columns that parse as dates
    for col in df.columns:
        if df[col].dtype == "object":
            try:
                parsed = pd.to_datetime(df[col], infer_datetime_format=True, errors="coerce")
                if parsed.notna().sum() > len(df) * 0.7:  # >70% valid
                    df["date"] = parsed
                    return df
            except Exception:
                continue

    # Case 3: Check common date column names
    date_names = ["date", "order_date", "order date", "transaction_date", "transaction date", "ship_date"]
    for name in date_names:
        if name in cols_lower:
            df["date"] = pd.to_datetime(df[cols_lower[name]], errors="coerce")
            return df

    raise ValueError(
        "Could not auto-detect a date column. Please ensure your CSV has a date column "
        "or YEAR/MONTH columns."
    )


def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean and normalize the DataFrame:
    - Strip whitespace from string columns
    - Normalize category names
    - Fill/drop missing values intelligently
    """
    # Strip whitespace from column names
    df.columns = [c.strip() for c in df.columns]

    # Strip whitespace from string columns
    for col in df.select_dtypes(include=["object"]).columns:
        df[col] = df[col].str.strip()

    # Detect and normalize 'category-like' columns
    category_candidates = []
    cols_lower = {c.lower(): c for c in df.columns}
    for name in ["item type", "item_type", "category", "sub-category", "sub_category", "product_category"]:
        if name in cols_lower:
            category_candidates.append(cols_lower[name])

    for col in category_candidates:
        df[col] = df[col].str.title().str.strip()

    # Detect sales-like numeric columns and fill NaN with 0
    sales_keywords = ["sales", "revenue", "amount", "profit", "quantity", "transfers"]
    for col in df.columns:
        if any(kw in col.lower() for kw in sales_keywords):
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    # Drop rows where date is missing
    if "date" in df.columns:
        df = df.dropna(subset=["date"])

    return df


def detect_sales_column(df: pd.DataFrame) -> str:
    """Heuristically pick the primary sales column."""
    cols_lower = {c.lower(): c for c in df.columns}
    priority = ["retail sales", "retail_sales", "sales", "revenue", "amount", "total_sales"]
    for name in priority:
        if name in cols_lower:
            return cols_lower[name]

    # Fallback: pick the first numeric column with 'sale' in its name
    for col in df.columns:
        if "sale" in col.lower() and pd.api.types.is_numeric_dtype(df[col]):
            return col

    raise ValueError("Could not detect a sales column in the dataset.")


def detect_category_column(df: pd.DataFrame) -> Optional[str]:
    """Heuristically pick the category column."""
    cols_lower = {c.lower(): c for c in df.columns}
    priority = ["item type", "item_type", "category", "product_category", "sub-category"]
    for name in priority:
        if name in cols_lower:
            return cols_lower[name]
    return None


def compute_summary_stats(df: pd.DataFrame, sales_col: str, category_col: Optional[str]) -> dict:
    """Compute high-level summary statistics."""
    stats = {
        "total_rows": len(df),
        "date_range": {
            "start": df["date"].min().isoformat(),
            "end": df["date"].max().isoformat(),
        },
        "total_sales": round(float(df[sales_col].sum()), 2),
    }

    # Add warehouse sales if present
    cols_lower = {c.lower(): c for c in df.columns}
    if "warehouse sales" in cols_lower:
        stats["total_warehouse_sales"] = round(float(df[cols_lower["warehouse sales"]].sum()), 2)

    if category_col:
        stats["num_categories"] = int(df[category_col].nunique())
        stats["top_category"] = df.groupby(category_col)[sales_col].sum().idxmax()

    # Suppliers
    for name in ["supplier", "vendor", "manufacturer"]:
        if name in cols_lower:
            stats["num_suppliers"] = int(df[cols_lower[name]].nunique())
            break

    # YoY Growth
    if "date" in df.columns:
        yearly = df.groupby(df["date"].dt.year)[sales_col].sum()
        if len(yearly) >= 2:
            last_two = yearly.iloc[-2:]
            growth = ((last_two.iloc[-1] - last_two.iloc[-2]) / last_two.iloc[-2]) * 100
            stats["yoy_growth"] = round(float(growth), 2)

    return stats


def compute_trend_data(df: pd.DataFrame, sales_col: str) -> dict:
    """Compute sales trends at different granularities."""
    trends = {}

    # Monthly trend
    monthly = df.groupby(pd.Grouper(key="date", freq="MS"))[sales_col].sum().reset_index()
    monthly.columns = ["date", "value"]
    monthly = monthly.sort_values("date")

    # Detect anomalies using IQR
    q1 = monthly["value"].quantile(0.25)
    q3 = monthly["value"].quantile(0.75)
    iqr = q3 - q1
    lower_bound = q1 - 1.5 * iqr
    upper_bound = q3 + 1.5 * iqr

    trends["monthly"] = [
        {
            "date": row["date"].strftime("%Y-%m-%d"),
            "value": round(float(row["value"]), 2),
            "is_anomaly": bool(row["value"] < lower_bound or row["value"] > upper_bound),
        }
        for _, row in monthly.iterrows()
    ]

    # Quarterly trend
    quarterly = df.groupby(pd.Grouper(key="date", freq="QS"))[sales_col].sum().reset_index()
    quarterly.columns = ["date", "value"]
    quarterly = quarterly.sort_values("date")
    trends["quarterly"] = [
        {
            "date": row["date"].strftime("%Y-%m-%d"),
            "value": round(float(row["value"]), 2),
        }
        for _, row in quarterly.iterrows()
    ]

    # Yearly trend
    yearly = df.groupby(df["date"].dt.year)[sales_col].sum().reset_index()
    yearly.columns = ["year", "value"]
    trends["yearly"] = [
        {"date": str(int(row["year"])), "value": round(float(row["value"]), 2)}
        for _, row in yearly.iterrows()
    ]

    return trends


def compute_category_data(df: pd.DataFrame, sales_col: str, category_col: str) -> dict:
    """Compute category breakdown with growth rates."""
    cat_total = df.groupby(category_col)[sales_col].sum().sort_values(ascending=False)

    # Category growth rate (first year vs last year)
    yearly_cat = df.groupby([df["date"].dt.year, category_col])[sales_col].sum().unstack(fill_value=0)
    growth_rates = {}
    if len(yearly_cat) >= 2:
        first_year = yearly_cat.iloc[0]
        last_year = yearly_cat.iloc[-1]
        for cat in cat_total.index:
            if cat in first_year.index and first_year[cat] > 0:
                rate = ((last_year.get(cat, 0) - first_year[cat]) / first_year[cat]) * 100
                growth_rates[cat] = round(float(rate), 2)

    categories = [
        {
            "name": str(cat),
            "total_sales": round(float(val), 2),
            "growth_rate": growth_rates.get(cat),
        }
        for cat, val in cat_total.items()
    ]

    return {
        "categories": categories,
        "top_5": categories[:5],
        "bottom_5": categories[-5:] if len(categories) >= 5 else categories,
    }


def compute_seasonality_data(df: pd.DataFrame, sales_col: str) -> dict:
    """Detect seasonality patterns from the data."""
    # Monthly seasonality (average sales per month across years)
    monthly_avg = df.groupby(df["date"].dt.month)[sales_col].mean()
    month_names = [
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December"
    ]
    monthly_seasonality = [
        {"period": month_names[int(m) - 1], "value": round(float(v), 2)}
        for m, v in monthly_avg.items()
    ]

    # Quarterly seasonality
    quarterly_avg = df.groupby(df["date"].dt.quarter)[sales_col].mean()
    quarterly_seasonality = [
        {"period": f"Q{int(q)}", "value": round(float(v), 2)}
        for q, v in quarterly_avg.items()
    ]

    # Find peak and trough
    peak_month = monthly_avg.idxmax()
    trough_month = monthly_avg.idxmin()

    # Build heatmap data: year x month
    heatmap = df.groupby([df["date"].dt.year, df["date"].dt.month])[sales_col].sum().reset_index()
    heatmap.columns = ["year", "month", "value"]
    heatmap_list = [
        {
            "year": int(row["year"]),
            "month": int(row["month"]),
            "value": round(float(row["value"]), 2),
        }
        for _, row in heatmap.iterrows()
    ]

    return {
        "monthly": monthly_seasonality,
        "quarterly": quarterly_seasonality,
        "heatmap": heatmap_list,
        "peak_month": month_names[int(peak_month) - 1],
        "trough_month": month_names[int(trough_month) - 1],
        "insight": (
            f"Sales consistently peak in {month_names[int(peak_month) - 1]} "
            f"and dip in {month_names[int(trough_month) - 1]}."
        ),
    }


def generate_insights(
    summary: dict, seasonality: dict, category_data: dict, trend_data: dict
) -> dict:
    """Generate actionable business insights from the analysis."""
    insights = []

    # Insight 1: Overall performance
    if summary.get("yoy_growth") is not None:
        growth = summary["yoy_growth"]
        if growth > 0:
            insights.append({
                "title": "Revenue Growth Detected",
                "description": f"Year-over-year sales grew by {growth}%. Maintain current strategy and consider scaling marketing during peak periods.",
                "severity": "success",
            })
        else:
            insights.append({
                "title": "Revenue Decline Alert",
                "description": f"Year-over-year sales declined by {abs(growth)}%. Investigate underperforming categories and consider promotional strategies.",
                "severity": "warning",
            })

    # Insight 2: Seasonal opportunity
    if seasonality.get("peak_month") and seasonality.get("trough_month"):
        insights.append({
            "title": "Seasonal Pattern Identified",
            "description": (
                f"Peak sales occur in {seasonality['peak_month']}. "
                f"Consider ramping up inventory 1-2 months before. "
                f"Lowest sales in {seasonality['trough_month']} — ideal for clearance events."
            ),
            "severity": "info",
        })

    # Insight 3: Category analysis
    if category_data.get("categories"):
        cats = category_data["categories"]
        declining = [c for c in cats if c.get("growth_rate") is not None and c["growth_rate"] < -10]
        if declining:
            names = ", ".join([c["name"] for c in declining[:3]])
            insights.append({
                "title": "Declining Categories Detected",
                "description": f"The following categories show >10% decline: {names}. Consider phasing out low performers or running targeted promotions.",
                "severity": "warning",
            })

        growing = [c for c in cats if c.get("growth_rate") is not None and c["growth_rate"] > 20]
        if growing:
            names = ", ".join([c["name"] for c in growing[:3]])
            insights.append({
                "title": "High-Growth Categories",
                "description": f"Categories growing >20%: {names}. Consider increasing inventory allocation for these segments.",
                "severity": "success",
            })

    # Insight 4: Anomaly detection
    if trend_data.get("monthly"):
        anomalies = [p for p in trend_data["monthly"] if p.get("is_anomaly")]
        if anomalies:
            dates = ", ".join([a["date"][:7] for a in anomalies[:3]])
            insights.append({
                "title": "Sales Anomalies Detected",
                "description": f"Unusual sales volume detected in: {dates}. Investigate whether these were caused by promotions, stockouts, or external events.",
                "severity": "warning",
            })

    # Fallback insight
    if not insights:
        insights.append({
            "title": "Data Analysis Complete",
            "description": f"Analyzed {summary['total_rows']:,} records. No major anomalies detected. Business appears to be operating steadily.",
            "severity": "info",
        })

    return {"items": insights}


def run_full_pipeline(file_paths: list[str]) -> dict:
    """Execute the complete data processing pipeline."""
    # Step 1: Load & merge
    df = load_and_merge_csvs(file_paths)

    # Step 2: Detect dates
    df = auto_detect_and_parse_dates(df)

    # Step 3: Clean
    df = clean_dataframe(df)

    # Step 4: Detect columns
    sales_col = detect_sales_column(df)
    category_col = detect_category_column(df)

    # Step 5: Compute everything
    summary = compute_summary_stats(df, sales_col, category_col)
    trends = compute_trend_data(df, sales_col)
    seasonality = compute_seasonality_data(df, sales_col)

    category_data = None
    if category_col:
        category_data = compute_category_data(df, sales_col, category_col)

    insights = generate_insights(summary, seasonality, category_data or {}, trends)

    return {
        "summary_stats": summary,
        "eda_data": trends,
        "seasonality_data": seasonality,
        "category_data": category_data,
        "insights": insights,
        "sales_col": sales_col,
        "category_col": category_col,
        "df": df,  # Pass to forecasting
    }
