import functools
import os

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings.

    Normal deployments only need DATA_DIR: the SQLite database is stored as
    ``{DATA_DIR}/mangarr.db`` unless DATABASE_URL is explicitly set (advanced).
    """

    DATABASE_URL: str = ""
    DATA_DIR: str = "./data"
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:3000"]
    DEFAULT_LANGUAGE: str = "en"
    SERIES_FOLDER_FORMAT: str = "{Series Title} ({Year})"
    FILE_FORMAT: str = "{Series Title} - Vol.{Volume} Ch.{Chapter} - {Chapter Title}{Extension}"
    FILE_FORMAT_NO_VOLUME: str = "{Series Title} - Ch.{Chapter} - {Chapter Title}{Extension}"
    MANGA_EXTENSIONS: list[str] = [".cbz", ".cbr", ".zip", ".pdf", ".epub"]

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @model_validator(mode="after")
    def default_sqlite_url_from_data_dir(self) -> "Settings":
        if self.DATABASE_URL.strip():
            return self

        data_dir = os.path.abspath(self.DATA_DIR)
        db_path = os.path.join(data_dir, "mangarr.db")
        # Four slashes: sqlite absolute path on disk (see SQLAlchemy SQLite URLs)
        self.DATABASE_URL = f"sqlite:///{db_path}"
        return self


@functools.lru_cache()
def get_settings() -> Settings:
    return Settings()
