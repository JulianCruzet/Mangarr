import os
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.models.imported_file import ImportedFile
from app.models.chapter import Chapter
from app.models.series import Series
from app.utils.naming import (
    build_file_name,
    select_file_template,
    build_series_folder_name,
)
from app.utils.file_helpers import safe_move
from app.config import get_settings


def _build_target_path(
    imported: ImportedFile,
    series: Series,
    chapter: Optional[Chapter] = None,
) -> Optional[str]:
    """
    Compute the target path for an imported file.
    Returns full destination path string, or None if series has no root folder.
    """
    settings = get_settings()

    if not series.root_folder or not series.root_folder.path:
        return None

    # Determine series folder
    series_folder = series.series_folder
    if not series_folder:
        series_folder = build_series_folder_name(
            template=settings.SERIES_FOLDER_FORMAT,
            title=series.title,
            year=series.year,
        )

    # Pick file naming template
    volume_number = chapter.volume_number if chapter else imported.parsed_volume_number
    template = select_file_template(
        base_template=settings.FILE_FORMAT,
        no_volume_template=settings.FILE_FORMAT_NO_VOLUME,
        volume_number=volume_number,
    )

    chapter_number = chapter.chapter_number if chapter else imported.parsed_chapter_number
    chapter_title = chapter.title if chapter else None

    file_name = build_file_name(
        template=template,
        series_title=series.title,
        extension=imported.extension,
        chapter_number=chapter_number,
        volume_number=volume_number,
        chapter_title=chapter_title,
        year=series.year,
    )

    target_path = os.path.join(
        series.root_folder.path,
        series_folder,
        file_name,
    )
    return target_path


def preview_organize(
    db: Session,
    series_id: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    Dry-run: compute proposed renames for all matched/organized files.
    Returns a list of dicts: {source, destination, would_conflict, series_id, file_id}.
    """
    query = db.query(ImportedFile).filter(
        ImportedFile.scan_state.in_(["matched", "organized"])
    )
    if series_id is not None:
        query = query.filter(ImportedFile.series_id == series_id)

    files = query.all()
    proposals = []

    # Pre-load series with eager root_folder
    series_cache: Dict[int, Series] = {}

    for imported in files:
        if not imported.series_id:
            continue

        if imported.series_id not in series_cache:
            s = (
                db.query(Series)
                .filter(Series.id == imported.series_id)
                .first()
            )
            if s:
                series_cache[imported.series_id] = s

        series = series_cache.get(imported.series_id)
        if not series:
            continue

        # Load associated chapter if any
        chapter = None
        if imported.chapter_id:
            chapter = db.query(Chapter).filter(Chapter.id == imported.chapter_id).first()

        target_path = _build_target_path(imported, series, chapter)
        if not target_path:
            continue

        # Check for conflict
        would_conflict = (
            os.path.exists(target_path) and target_path != imported.file_path
        )

        proposals.append(
            {
                "file_id": imported.id,
                "series_id": imported.series_id,
                "source": imported.file_path,
                "destination": target_path,
                "would_conflict": would_conflict,
            }
        )

    return proposals


def organize_series(
    db: Session,
    series_id: int,
    dry_run: bool = False,
) -> List[Dict[str, Any]]:
    """
    Rename/move files for a single series.
    Returns list of operation results.
    """
    proposals = preview_organize(db, series_id=series_id)
    results = []

    for proposal in proposals:
        result = dict(proposal)
        result["moved"] = False
        result["error"] = None

        if dry_run:
            results.append(result)
            continue

        src = proposal["source"]
        dst = proposal["destination"]

        if src == dst:
            result["moved"] = False
            result["note"] = "already at destination"
            results.append(result)
            continue

        if proposal["would_conflict"]:
            result["error"] = f"Destination already exists: {dst}"
            results.append(result)
            continue

        try:
            safe_move(src, dst)

            # Update DB record
            imported = (
                db.query(ImportedFile).filter(ImportedFile.id == proposal["file_id"]).first()
            )
            if imported:
                imported.file_path = dst
                imported.file_name = os.path.basename(dst)
                imported.scan_state = "organized"
            db.commit()

            result["moved"] = True
        except Exception as exc:
            result["error"] = str(exc)

        results.append(result)

    return results


def organize_all(db: Session, dry_run: bool = False) -> List[Dict[str, Any]]:
    """Rename/move files for all series in the library."""
    proposals = preview_organize(db, series_id=None)
    results = []

    for proposal in proposals:
        result = dict(proposal)
        result["moved"] = False
        result["error"] = None

        if dry_run:
            results.append(result)
            continue

        src = proposal["source"]
        dst = proposal["destination"]

        if src == dst:
            result["moved"] = False
            result["note"] = "already at destination"
            results.append(result)
            continue

        if proposal["would_conflict"]:
            result["error"] = f"Destination already exists: {dst}"
            results.append(result)
            continue

        try:
            safe_move(src, dst)

            imported = (
                db.query(ImportedFile).filter(ImportedFile.id == proposal["file_id"]).first()
            )
            if imported:
                imported.file_path = dst
                imported.file_name = os.path.basename(dst)
                imported.scan_state = "organized"

            result["moved"] = True
        except Exception as exc:
            result["error"] = str(exc)

        results.append(result)

    if not dry_run:
        db.commit()

    return results
