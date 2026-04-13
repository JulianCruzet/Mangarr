import asyncio
import json
import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.imported_file import ImportedFile
from app.models.root_folder import RootFolder
from app.models.series import Series
from app.utils.file_helpers import MANGA_EXTENSIONS, get_file_size

try:
    from rapidfuzz import fuzz, process as rfuzz_process
    RAPIDFUZZ_AVAILABLE = True
except ImportError:
    RAPIDFUZZ_AVAILABLE = False

# ---------------------------------------------------------------------------
# Filename parsing patterns (in priority order)
# ---------------------------------------------------------------------------

# Strips parenthesized/bracketed noise groups: (2022), [Digital], (1r0n), etc.
_NOISE_RE = re.compile(r'\s*[\(\[][^\)\]]*[\)\]]')

def _strip_noise(s: str) -> str:
    return _NOISE_RE.sub('', s).strip()

_PATTERNS = [
    # ── Dash-separated ────────────────────────────────────────────────────────
    # "Series - Vol.01 Ch.001"
    re.compile(
        r"(?P<series>.+?)\s*[-–]\s*[Vv]ol\.?\s*(?P<vol>[\d.]+)\s*[Cc]h\.?\s*(?P<ch>[\d.]+)",
        re.IGNORECASE,
    ),
    # "Series - Ch.001"
    re.compile(
        r"(?P<series>.+?)\s*[-–]\s*[Cc]h(?:apter)?\.?\s*(?P<ch>[\d.]+)",
        re.IGNORECASE,
    ),
    # "Series - Vol.01"
    re.compile(
        r"(?P<series>.+?)\s*[-–]\s*[Vv]ol(?:ume)?\.?\s*(?P<vol>[\d.]+)",
        re.IGNORECASE,
    ),

    # ── No-dash: digital/scene release format ─────────────────────────────────
    # "Series v01c001" or "Series v01 c001" (vol + chapter, no dash)
    re.compile(
        r"(?P<series>.+?)\s+[Vv](?:ol(?:ume)?\.?)?\s*(?P<vol>\d+(?:\.\d+)?)\s*[Cc](?:h(?:apter)?\.?)?\s*(?P<ch>\d+(?:\.\d+)?)",
        re.IGNORECASE,
    ),
    # "Series v01 (Year) (Quality) (Group)" — most common digital format
    re.compile(
        r"(?P<series>.+?)\s+[Vv](?:ol(?:ume)?\.?)?\s*(?P<vol>\d+(?:\.\d+)?)(?=\s|$|[\(\[])",
        re.IGNORECASE,
    ),
    # "Series c001 (noise)" or "Series ch001"
    re.compile(
        r"(?P<series>.+?)\s+[Cc](?:h(?:apter)?\.?)?\s*(?P<ch>\d+(?:\.\d+)?)(?=\s|$|[\(\[])",
        re.IGNORECASE,
    ),

    # ── Fallback: bare number at end ──────────────────────────────────────────
    re.compile(r"(?P<series>.+?)\s+(?P<ch>[\d.]+)$"),
]

FUZZY_THRESHOLD = 80


# ---------------------------------------------------------------------------
# Scan job state
# ---------------------------------------------------------------------------
@dataclass
class ScanJob:
    status: str = "idle"  # idle | running | completed | error
    total_files: int = 0
    processed_files: int = 0
    matched: int = 0
    unmatched: int = 0
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    error: Optional[str] = None
    cancel_requested: bool = False


# Module-level singleton
_current_job: ScanJob = ScanJob()


def get_scan_job() -> ScanJob:
    return _current_job


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------
def parse_filename(stem: str) -> dict:
    """
    Try each pattern in priority order against both the raw stem and a
    noise-stripped version (removes groups like (2022), [Digital], (1r0n)).
    Returns dict with keys: series, chapter, volume (all may be None).
    """
    cleaned = _strip_noise(stem)

    for pattern in _PATTERNS:
        # Try raw first, then noise-stripped
        m = pattern.search(stem) or (pattern.search(cleaned) if cleaned != stem else None)
        if m:
            groups = m.groupdict()
            series = (groups.get("series") or "").strip() or None
            # Strip any trailing noise that crept into the series capture group
            if series:
                series = _strip_noise(series).strip() or series
            return {
                "series": series,
                "chapter": groups.get("ch") or None,
                "volume": groups.get("vol") or None,
            }
    return {"series": None, "chapter": None, "volume": None}


def _collect_alt_titles(series: Series) -> List[str]:
    """Return all known titles for a series (title + alt_titles)."""
    titles = [series.title]
    if series.alt_titles_json:
        try:
            alt_list = json.loads(series.alt_titles_json)
            for alt_dict in alt_list:
                if isinstance(alt_dict, dict):
                    titles.extend(alt_dict.values())
                elif isinstance(alt_dict, str):
                    titles.append(alt_dict)
        except (json.JSONDecodeError, TypeError):
            pass
    return [t for t in titles if t]


def fuzzy_match_series(parsed_title: str, all_series: List[Series]) -> Optional[Series]:
    """
    Find the best-matching Series using rapidfuzz.
    Returns the Series if score >= FUZZY_THRESHOLD, else None.
    """
    if not parsed_title or not all_series:
        return None

    if not RAPIDFUZZ_AVAILABLE:
        # Fallback: simple case-insensitive substring match
        lower = parsed_title.lower()
        for s in all_series:
            for title in _collect_alt_titles(s):
                if title.lower() == lower:
                    return s
        return None

    best_series = None
    best_score = 0

    for series in all_series:
        for title in _collect_alt_titles(series):
            score = fuzz.token_set_ratio(parsed_title, title)
            if score > best_score:
                best_score = score
                best_series = series

    if best_score >= FUZZY_THRESHOLD:
        return best_series
    return None


# ---------------------------------------------------------------------------
# Core scan logic (runs in a thread via run_in_executor)
# ---------------------------------------------------------------------------
def _scan_root_folder(db: Session, root_folder: RootFolder, job: ScanJob) -> None:
    """Walk one root folder and upsert ImportedFile records."""
    base_path = Path(root_folder.path)
    if not base_path.exists():
        return

    # Load all known extensions from config
    try:
        from app.config import get_settings
        settings = get_settings()
        extensions = set(settings.MANGA_EXTENSIONS)
    except Exception:
        extensions = MANGA_EXTENSIONS

    all_series = db.query(Series).all()

    for file_path in base_path.rglob("*"):
        if job.cancel_requested:
            return

        if not file_path.is_file():
            continue
        if file_path.suffix.lower() not in extensions:
            continue

        job.total_files += 1
        abs_path = str(file_path.resolve())
        stem = file_path.stem
        ext = file_path.suffix.lower()

        parsed = parse_filename(stem)

        # Check if already tracked
        existing = db.query(ImportedFile).filter(ImportedFile.file_path == abs_path).first()
        if existing:
            existing.last_seen_at = datetime.now(timezone.utc)
            existing.file_size = get_file_size(file_path)
            if existing.scan_state not in ("organized", "ignored", "matched"):
                # Re-attempt matching
                if parsed["series"] and existing.scan_state == "unmatched":
                    matched_series = fuzzy_match_series(parsed["series"], all_series)
                    if matched_series:
                        existing.series_id = matched_series.id
                        existing.scan_state = "matched"
                        job.matched += 1
                    else:
                        job.unmatched += 1
                else:
                    job.matched += 1
            else:
                job.matched += 1
            job.processed_files += 1
            continue

        # New file — attempt to match
        matched_series = None
        scan_state = "unmatched"

        if parsed["series"]:
            matched_series = fuzzy_match_series(parsed["series"], all_series)
            if matched_series:
                scan_state = "matched"

        imported = ImportedFile(
            series_id=matched_series.id if matched_series else None,
            file_path=abs_path,
            file_name=file_path.name,
            file_size=get_file_size(file_path),
            extension=ext,
            parsed_series_title=parsed["series"],
            parsed_chapter_number=parsed["chapter"],
            parsed_volume_number=parsed["volume"],
            scan_state=scan_state,
        )
        db.add(imported)

        if matched_series:
            job.matched += 1
        else:
            job.unmatched += 1

        job.processed_files += 1

    db.commit()


def _run_full_scan(root_folder_id: Optional[int] = None) -> None:
    """
    Synchronous scan function that runs in an executor thread.
    """
    global _current_job

    _current_job.status = "running"
    _current_job.started_at = datetime.now(timezone.utc)
    _current_job.total_files = 0
    _current_job.processed_files = 0
    _current_job.matched = 0
    _current_job.unmatched = 0
    _current_job.error = None

    db: Session = SessionLocal()
    try:
        if root_folder_id is not None:
            folders = db.query(RootFolder).filter(RootFolder.id == root_folder_id).all()
        else:
            folders = db.query(RootFolder).all()

        for folder in folders:
            _scan_root_folder(db, folder, _current_job)
            if _current_job.cancel_requested:
                break

        if _current_job.cancel_requested:
            _current_job.status = "cancelled"
        else:
            _current_job.status = "completed"
    except Exception as exc:
        _current_job.status = "error"
        _current_job.error = str(exc)
    finally:
        _current_job.finished_at = datetime.now(timezone.utc)
        db.close()


async def trigger_scan(root_folder_id: Optional[int] = None) -> ScanJob:
    """
    Start a scan in a background thread.
    Returns the current ScanJob (status will be 'running').
    """
    global _current_job

    if _current_job.status == "running":
        return _current_job

    _current_job = ScanJob()

    loop = asyncio.get_event_loop()
    loop.run_in_executor(None, lambda: _run_full_scan(root_folder_id))

    return _current_job


def manual_match(db: Session, imported_file_id: int, chapter_id: int) -> ImportedFile:
    """Manually match an ImportedFile to a Chapter."""
    from app.models.chapter import Chapter

    imported = db.query(ImportedFile).filter(ImportedFile.id == imported_file_id).first()
    if not imported:
        raise ValueError(f"ImportedFile {imported_file_id} not found")

    chapter = db.query(Chapter).filter(Chapter.id == chapter_id).first()
    if not chapter:
        raise ValueError(f"Chapter {chapter_id} not found")

    imported.chapter_id = chapter_id
    imported.series_id = chapter.series_id
    imported.scan_state = "matched"

    chapter.is_downloaded = True
    chapter.imported_file_id = imported_file_id

    db.commit()
    db.refresh(imported)
    return imported


def manual_assign_series(db: Session, imported_file_id: int, series_id: int) -> ImportedFile:
    """Manually classify an ImportedFile to a Series without chapter linkage."""
    imported = db.query(ImportedFile).filter(ImportedFile.id == imported_file_id).first()
    if not imported:
        raise ValueError(f"ImportedFile {imported_file_id} not found")

    series = db.query(Series).filter(Series.id == series_id).first()
    if not series:
        raise ValueError(f"Series {series_id} not found")

    imported.series_id = series_id
    imported.scan_state = "matched"

    db.commit()
    db.refresh(imported)
    return imported


def cancel_scan() -> bool:
    """Request cancellation of the current scan job."""
    if _current_job.status != "running":
        return False
    _current_job.cancel_requested = True
    return True
