"""
Report router — serves the processed analytics and the PDF file.
"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
import os

from auth import get_current_user
from database import get_db
from models import Dataset, Report, User
from schemas import ReportResponse

router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.get("/{dataset_id}", response_model=ReportResponse)
def get_report(
    dataset_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    dataset = db.query(Dataset).filter(
        Dataset.id == dataset_id,
        Dataset.user_id == current_user.id,
    ).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found.")

    if dataset.status != "done":
        raise HTTPException(
            status_code=400,
            detail=f"Report is not ready. Current status: {dataset.status}",
        )

    report = db.query(Report).filter(Report.dataset_id == dataset_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report data not found.")

    return report


@router.get("/{dataset_id}/download")
def download_pdf(
    dataset_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    dataset = db.query(Dataset).filter(
        Dataset.id == dataset_id,
        Dataset.user_id == current_user.id,
    ).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found.")

    report = db.query(Report).filter(Report.dataset_id == dataset_id).first()
    if not report or not report.pdf_path:
        raise HTTPException(status_code=404, detail="PDF report not found or not generated yet.")

    if not os.path.exists(report.pdf_path):
        raise HTTPException(status_code=404, detail="PDF file is missing on the server.")

    return FileResponse(
        path=report.pdf_path,
        media_type="application/pdf",
        filename=f"RetailSense_Report_{dataset.name}.pdf",
    )
