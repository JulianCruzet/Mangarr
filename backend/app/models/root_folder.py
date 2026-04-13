from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import BigInteger, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.series import Series


class RootFolder(Base):
    __tablename__ = "root_folders"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    path: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    label: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    free_space: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)

    # Relationships
    series: Mapped[List["Series"]] = relationship(
        "Series",
        back_populates="root_folder",
        cascade="all, delete-orphan",
    )
