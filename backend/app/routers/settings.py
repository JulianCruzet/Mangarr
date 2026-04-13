import json
import os
from typing import Any, Dict

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.config import get_settings
from app.schemas.settings import SettingsResponse, SettingsUpdate

router = APIRouter(prefix="/settings", tags=["settings"])


def _get_settings_file_path() -> str:
    settings = get_settings()
    return os.path.join(settings.DATA_DIR, "settings.json")


def _load_overrides() -> Dict[str, Any]:
    """Load user overrides from settings.json, return {} if not present."""
    path = _get_settings_file_path()
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def _save_overrides(overrides: Dict[str, Any]) -> None:
    """Persist overrides to settings.json."""
    path = _get_settings_file_path()
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(overrides, f, indent=2)


def _merge_settings() -> Dict[str, Any]:
    """Merge config defaults with persisted overrides."""
    config = get_settings()
    base = {
        "database_url": config.DATABASE_URL,
        "data_dir": config.DATA_DIR,
        "host": config.HOST,
        "port": config.PORT,
        "cors_origins": config.CORS_ORIGINS,
        "default_language": config.DEFAULT_LANGUAGE,
        "series_folder_format": config.SERIES_FOLDER_FORMAT,
        "file_format": config.FILE_FORMAT,
        "file_format_no_volume": config.FILE_FORMAT_NO_VOLUME,
        "manga_extensions": config.MANGA_EXTENSIONS,
    }
    overrides = _load_overrides()
    base.update(overrides)
    return base


@router.get("", response_model=SettingsResponse)
def get_settings_endpoint():
    """Return current effective settings (defaults + user overrides)."""
    merged = _merge_settings()
    return SettingsResponse(**merged)


@router.put("", response_model=SettingsResponse)
def update_settings(payload: SettingsUpdate):
    """
    Update writable settings. Changes are persisted to DATA_DIR/settings.json
    and merged with config defaults on reads.
    """
    overrides = _load_overrides()

    update_data = payload.model_dump(exclude_none=True)
    overrides.update(update_data)

    try:
        _save_overrides(overrides)
    except OSError as exc:
        raise HTTPException(status_code=500, detail=f"Failed to save settings: {exc}")

    merged = _merge_settings()
    return SettingsResponse(**merged)
