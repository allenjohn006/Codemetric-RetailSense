import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, ForeignKey, Integer, Text, JSON, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String, nullable=False)
    is_demo: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    datasets: Mapped[list["Dataset"]] = relationship("Dataset", back_populates="owner", cascade="all, delete-orphan")


class Dataset(Base):
    __tablename__ = "datasets"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    original_filenames: Mapped[str] = mapped_column(Text, nullable=False)  # comma-separated
    file_paths: Mapped[str] = mapped_column(Text, nullable=False)  # comma-separated
    row_count: Mapped[int] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String, default="pending")  # pending, processing, done, error
    task_id: Mapped[str] = mapped_column(String, nullable=True)
    error_message: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)

    owner: Mapped["User"] = relationship("User", back_populates="datasets")
    report: Mapped["Report"] = relationship("Report", back_populates="dataset", uselist=False, cascade="all, delete-orphan")


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    dataset_id: Mapped[str] = mapped_column(String, ForeignKey("datasets.id"), nullable=False)
    summary_stats: Mapped[dict] = mapped_column(JSON, nullable=True)
    eda_data: Mapped[dict] = mapped_column(JSON, nullable=True)
    forecast_data: Mapped[dict] = mapped_column(JSON, nullable=True)
    seasonality_data: Mapped[dict] = mapped_column(JSON, nullable=True)
    category_data: Mapped[dict] = mapped_column(JSON, nullable=True)
    insights: Mapped[dict] = mapped_column(JSON, nullable=True)
    pdf_path: Mapped[str] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    dataset: Mapped["Dataset"] = relationship("Dataset", back_populates="report")
