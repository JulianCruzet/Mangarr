import os
import shutil
from pathlib import Path
from typing import Set


MANGA_EXTENSIONS: Set[str] = {".cbz", ".cbr", ".zip", ".pdf", ".epub"}


def is_manga_file(path: Path) -> bool:
    """Return True if the file has a recognized manga extension."""
    return path.suffix.lower() in MANGA_EXTENSIONS


def get_file_size(path: Path) -> int:
    """Return file size in bytes, or 0 if the file doesn't exist."""
    try:
        return path.stat().st_size
    except (OSError, FileNotFoundError):
        return 0


def safe_move(src: str, dst: str) -> None:
    """
    Move a file from src to dst.
    Handles cross-device moves by falling back to copy + remove.
    Creates destination directory if it doesn't exist.
    """
    dst_dir = os.path.dirname(dst)
    if dst_dir:
        os.makedirs(dst_dir, exist_ok=True)

    try:
        shutil.move(src, dst)
    except OSError:
        # Cross-device move: copy then remove
        shutil.copy2(src, dst)
        os.remove(src)


def get_free_space(path: str) -> int:
    """Return free disk space in bytes for the given path."""
    try:
        stat = shutil.disk_usage(path)
        return stat.free
    except (OSError, FileNotFoundError):
        return 0


def ensure_dir(path: str) -> None:
    """Create directory and all parents if they don't exist."""
    os.makedirs(path, exist_ok=True)
