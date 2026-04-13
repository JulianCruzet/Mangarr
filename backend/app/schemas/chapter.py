from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class ChapterBase(BaseModel):
    chapter_number: Optional[str] = None
    volume_number: Optional[str] = None
    title: Optional[str] = None
    language: str = "en"
    pages: Optional[int] = None
    publish_at: Optional[datetime] = None


class ChapterCreate(ChapterBase):
    series_id: int
    volume_id: Optional[int] = None
    mangadex_id: Optional[str] = None


class ChapterResponse(ChapterBase):
    id: int
    series_id: int
    volume_id: Optional[int] = None
    mangadex_id: Optional[str] = None
    is_downloaded: bool
    imported_file_id: Optional[int] = None

    model_config = {"from_attributes": True}


class MangaDexChapter(BaseModel):
    """Represents a chapter as returned from MangaDex API."""
    id: str
    chapter_number: Optional[str] = None
    volume_number: Optional[str] = None
    title: Optional[str] = None
    language: str = "en"
    pages: Optional[int] = None
    publish_at: Optional[datetime] = None
