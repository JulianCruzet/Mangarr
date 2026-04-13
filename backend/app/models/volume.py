from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import ForeignKey, String, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.series import Series
    from app.models.chapter import Chapter


class Volume(Base):
    __tablename__ = "volumes"
    __table_args__ = (
        Index("ix_volumes_series_id", "series_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    series_id: Mapped[int] = mapped_column(
        ForeignKey("series.id", ondelete="CASCADE"), nullable=False
    )
    volume_number: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    cover_filename: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    # Relationships
    series: Mapped["Series"] = relationship("Series", back_populates="volumes")
    chapters: Mapped[List["Chapter"]] = relationship("Chapter", back_populates="volume")
