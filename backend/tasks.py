"""
RetailSense Celery Tasks
Background processing: data pipeline + forecasting + PDF generation.
"""
import os
import logging
from datetime import datetime, timezone

from worker import celery_app
from database import SessionLocal
from models import Dataset, Report
from pipeline import run_full_pipeline
from forecasting import run_forecast
from pdf_generator import generate_pdf
from config import settings

logger = logging.getLogger(__name__)


def _update_dataset_status(dataset_id: str, status: str, error: str = None, task_id: str = None):
    db = SessionLocal()
    try:
        dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
        if dataset:
            dataset.status = status
            if error:
                dataset.error_message = error
            if task_id:
                dataset.task_id = task_id
            if status in ("done", "error"):
                dataset.completed_at = datetime.now(timezone.utc)
            db.commit()
    except Exception as e:
        logger.error(f"Failed to update dataset status: {e}")
        db.rollback()
    finally:
        db.close()


@celery_app.task(bind=True, name="tasks.process_dataset")
def process_dataset(self, dataset_id: str, file_paths: list[str]):
    """
    Main background task: runs the full analysis pipeline on uploaded CSVs.
    Stores results in the database.
    """
    logger.info(f"[Task] Starting analysis for dataset {dataset_id}")
    _update_dataset_status(dataset_id, "processing", task_id=self.request.id)

    try:
        # ─── Step 1: Run EDA pipeline ─────────────────────────
        self.update_state(state="PROGRESS", meta={"step": "Cleaning & analyzing data..."})
        result = run_full_pipeline(file_paths)
        df = result.pop("df")
        sales_col = result.pop("sales_col")
        result.pop("category_col", None)

        # ─── Step 2: Forecasting ──────────────────────────────
        self.update_state(state="PROGRESS", meta={"step": "Running demand forecast..."})
        forecast_data = run_forecast(df, sales_col)
        result["forecast_data"] = forecast_data

        # ─── Step 3: Generate PDF ─────────────────────────────
        self.update_state(state="PROGRESS", meta={"step": "Generating PDF report..."})
        os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
        pdf_path = os.path.join(settings.UPLOAD_DIR, f"report_{dataset_id}.pdf")

        generate_pdf(
            summary_stats=result["summary_stats"],
            eda_data=result["eda_data"],
            forecast_data=forecast_data,
            seasonality_data=result["seasonality_data"],
            category_data=result.get("category_data"),
            insights=result["insights"],
            output_path=pdf_path,
        )

        # ─── Step 4: Save to database ─────────────────────────
        self.update_state(state="PROGRESS", meta={"step": "Saving results..."})
        db = SessionLocal()
        try:
            # Update dataset
            dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
            if dataset:
                dataset.row_count = result["summary_stats"]["total_rows"]
                dataset.status = "done"
                dataset.completed_at = datetime.now(timezone.utc)

            # Create report
            existing_report = db.query(Report).filter(Report.dataset_id == dataset_id).first()
            if existing_report:
                db.delete(existing_report)
                db.flush()

            report = Report(
                dataset_id=dataset_id,
                summary_stats=result["summary_stats"],
                eda_data=result["eda_data"],
                forecast_data=forecast_data,
                seasonality_data=result["seasonality_data"],
                category_data=result.get("category_data"),
                insights=result["insights"],
                pdf_path=pdf_path,
            )
            db.add(report)
            db.commit()
            logger.info(f"[Task] Analysis complete for dataset {dataset_id}")
        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()

        return {"status": "done", "dataset_id": dataset_id}

    except Exception as e:
        logger.error(f"[Task] Analysis failed for dataset {dataset_id}: {e}")
        _update_dataset_status(dataset_id, "error", error=str(e))
        raise
