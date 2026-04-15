from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel

from app.schemas.chapter import ChapterResponse


class VolumeResponse(BaseModel):
    id: int
    series_id: int
    volume_number: Optional[str] = None
    cover_filename: Optional[str] = None
    chapters: List[ChapterResponse] = []

    model_config = {"from_attributes": True}


class SeriesBase(BaseModel):
    title: str
    description: Optional[str] = None
    status: Optional[str] = None
    year: Optional[int] = None
    content_rating: Optional[str] = None
    original_language: Optional[str] = None
    monitor_status: str = "all"


class SeriesCreate(BaseModel):
    metadata_id: str
    metadata_provider: str = "mangadex"
    root_folder_id: int
    monitor_status: str = "all"


class SeriesUpdate(BaseModel):
    monitor_status: Optional[str] = None
    root_folder_id: Optional[int] = None


class SeriesResponse(SeriesBase):
    id: int
    metadata_provider: str = "mangadex"
    metadata_id: str
    mangadex_id: Optional[str] = None
    alt_titles_json: Optional[str] = None
    tags_json: Optional[str] = None
    cover_filename: Optional[str] = None
    root_folder_id: Optional[int] = None
    series_folder: Optional[str] = None
    metadata_updated_at: Optional[datetime] = None
    created_at: datetime
    anilist_id: Optional[int] = None
    anilist_volumes: Optional[int] = None
    anilist_chapters: Optional[int] = None

    model_config = {"from_attributes": True}


class SeriesWithStats(SeriesResponse):
    chapter_count: int = 0
    downloaded_count: int = 0
    missing_count: int = 0
    volumes: List[VolumeResponse] = []
    chapters: List[ChapterResponse] = []


class SeriesListResponse(BaseModel):
    items: List[SeriesResponse]
    total: int
