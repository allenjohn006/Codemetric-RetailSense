"""
Upload router — handles multi-file CSV uploads (up to 500MB total).
"""
import os
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from auth import get_current_user
from config import settings
from database import get_db
from models import Dataset, User
from schemas import DatasetResponse, DatasetListResponse, TaskStatusResponse
from tasks import process_dataset

router = APIRouter(prefix="/api/datasets", tags=["datasets"])

ALLOWED_TYPES = {"text/csv", "application/vnd.ms-excel", "application/csv"}
MAX_BYTES = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024


@router.post("/upload", response_model=DatasetResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_files(
    files: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded.")

    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

    saved_paths = []
    original_names = []
    total_size = 0

    for upload in files:
        # Validate file type
        if upload.content_type not in ALLOWED_TYPES and not upload.filename.endswith(".csv"):
            raise HTTPException(
                status_code=400,
                detail=f"'{upload.filename}' is not a valid CSV file.",
            )

        # Read and check size
        content = await upload.read()
        total_size += len(content)
        if total_size > MAX_BYTES:
            raise HTTPException(
                status_code=413,
                detail=f"Total upload size exceeds {settings.MAX_UPLOAD_SIZE_MB}MB limit.",
            )

        # Save to disk
        file_id = str(uuid.uuid4())
        save_path = os.path.join(settings.UPLOAD_DIR, f"{file_id}_{upload.filename}")
        with open(save_path, "wb") as f:
            f.write(content)

        saved_paths.append(save_path)
        original_names.append(upload.filename)

    # Create Dataset record
    name = original_names[0] if len(original_names) == 1 else f"{len(original_names)} files"
    dataset = Dataset(
        user_id=current_user.id,
        name=name,
        original_filenames=",".join(original_names),
        file_paths=",".join(saved_paths),
        status="pending",
    )
    db.add(dataset)
    db.commit()
    db.refresh(dataset)

    # Enqueue background task
    task = process_dataset.delay(dataset.id, saved_paths)
    dataset.task_id = task.id
    dataset.status = "processing"
    db.commit()
    db.refresh(dataset)

    return dataset


@router.get("", response_model=DatasetListResponse)
def list_datasets(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    datasets = (
        db.query(Dataset)
        .filter(Dataset.user_id == current_user.id)
        .order_by(Dataset.created_at.desc())
        .all()
    )
    return DatasetListResponse(datasets=datasets)


@router.get("/{dataset_id}/status", response_model=TaskStatusResponse)
def get_status(
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

    # Get live Celery task progress if still processing
    progress = None
    if dataset.status == "processing" and dataset.task_id:
        from celery.result import AsyncResult
        from worker import celery_app
        result = AsyncResult(dataset.task_id, app=celery_app)
        if result.state == "PROGRESS":
            progress = result.info.get("step")

    return TaskStatusResponse(
        dataset_id=dataset.id,
        status=dataset.status,
        progress=progress,
        error_message=dataset.error_message,
    )


@router.delete("/{dataset_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_dataset(
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

    # Clean up uploaded files
    for path in dataset.file_paths.split(","):
        if os.path.exists(path):
            os.remove(path)

    db.delete(dataset)
    db.commit()
