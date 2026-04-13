from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional
from sqlalchemy import BigInteger, DateTime, ForeignKey, String, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.series import Series


class ImportedFile(Base):
    __tablename__ = "imported_files"
    __table_args__ = (
        Index("ix_imported_files_series_id", "series_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    series_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("series.id", ondelete="SET NULL"), nullable=True
    )
    chapter_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("chapters.id", ondelete="SET NULL"), nullable=True
    )

    file_path: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    file_name: Mapped[str] = mapped_column(String, nullable=False)
    file_size: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    extension: Mapped[str] = mapped_column(String(16), nullable=False)

    # Parsed metadata
    parsed_series_title: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    parsed_chapter_number: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    parsed_volume_number: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    # State: unmatched | matched | organized | ignored
    scan_state: Mapped[str] = mapped_column(String(16), default="unmatched", nullable=False)

    imported_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )

    # Relationships
    series: Mapped[Optional["Series"]] = relationship("Series", back_populates="imported_files")
