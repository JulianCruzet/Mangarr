from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.root_folder import RootFolder
    from app.models.volume import Volume
    from app.models.chapter import Chapter
    from app.models.imported_file import ImportedFile


class MonitorStatus(str, Enum):
    ALL = "all"
    FUTURE = "future"
    NONE = "none"


class Series(Base):
    __tablename__ = "series"
    __table_args__ = (
        Index("ix_series_mangadex_id", "mangadex_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    mangadex_id: Mapped[str] = mapped_column(String(36), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    alt_titles_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    content_rating: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    original_language: Mapped[Optional[str]] = mapped_column(String(8), nullable=True)
    tags_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    cover_filename: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    # Library location
    root_folder_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("root_folders.id", ondelete="SET NULL"), nullable=True
    )
    series_folder: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    # Monitoring
    monitor_status: Mapped[str] = mapped_column(String(16), default="all", nullable=False)

    # Timestamps
    metadata_updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )

    # Relationships
    root_folder: Mapped[Optional["RootFolder"]] = relationship(
        "RootFolder", back_populates="series"
    )
    volumes: Mapped[List["Volume"]] = relationship(
        "Volume",
        back_populates="series",
        cascade="all, delete-orphan",
    )
    chapters: Mapped[List["Chapter"]] = relationship(
        "Chapter",
        back_populates="series",
        cascade="all, delete-orphan",
    )
    imported_files: Mapped[List["ImportedFile"]] = relationship(
        "ImportedFile",
        back_populates="series",
        cascade="all, delete-orphan",
    )
