from typing import List, Optional
from pydantic import BaseModel


class SettingsResponse(BaseModel):
    database_url: str
    data_dir: str
    host: str
    port: int
    cors_origins: List[str]
    default_language: str
    series_folder_format: str
    file_format: str
    file_format_no_volume: str
    manga_extensions: List[str]


class SettingsUpdate(BaseModel):
    default_language: Optional[str] = None
    series_folder_format: Optional[str] = None
    file_format: Optional[str] = None
    file_format_no_volume: Optional[str] = None
    manga_extensions: Optional[List[str]] = None
    cors_origins: Optional[List[str]] = None
