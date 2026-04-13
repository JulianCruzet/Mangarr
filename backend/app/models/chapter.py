from datetime import datetime
from typing import TYPE_CHECKING, Optional
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.series import Series
    from app.models.volume import Volume


class Chapter(Base):
    __tablename__ = "chapters"
    __table_args__ = (
        Index("ix_chapters_series_id", "series_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    series_id: Mapped[int] = mapped_column(
        ForeignKey("series.id", ondelete="CASCADE"), nullable=False
    )
    volume_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("volumes.id", ondelete="SET NULL"), nullable=True
    )
    mangadex_id: Mapped[Optional[str]] = mapped_column(
        String(36), unique=True, nullable=True
    )
    chapter_number: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    volume_number: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    title: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    language: Mapped[str] = mapped_column(String(8), default="en", nullable=False)
    pages: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    publish_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    is_downloaded: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    imported_file_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("imported_files.id", ondelete="SET NULL"), nullable=True
    )

    # Relationships
    series: Mapped["Series"] = relationship("Series", back_populates="chapters")
    volume: Mapped[Optional["Volume"]] = relationship("Volume", back_populates="chapters")
