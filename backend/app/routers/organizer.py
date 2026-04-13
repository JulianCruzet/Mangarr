from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.services import organizer_service

router = APIRouter(prefix="/organizer", tags=["organizer"])


class OrganizePreviewRequest(BaseModel):
    series_id: Optional[int] = None


class OrganizeProposal(BaseModel):
    file_id: int
    series_id: int
    source: str
    destination: str
    would_conflict: bool
    moved: Optional[bool] = None
    error: Optional[str] = None
    note: Optional[str] = None


@router.post("/preview", response_model=List[OrganizeProposal])
def preview_organize(
    payload: OrganizePreviewRequest,
    db: Session = Depends(get_db),
):
    """
    Dry-run: return proposed renames/moves without making changes.
    Optionally filter to a single series.
    """
    try:
        proposals = organizer_service.preview_organize(db, series_id=payload.series_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Preview failed: {exc}")

    return [OrganizeProposal(**p) for p in proposals]


@router.post("/organize/{series_id}", response_model=List[OrganizeProposal])
def organize_series(
    series_id: int,
    db: Session = Depends(get_db),
):
    """Rename and move files for a single series."""
    from app.models.series import Series

    series = db.query(Series).filter(Series.id == series_id).first()
    if not series:
        raise HTTPException(status_code=404, detail=f"Series {series_id} not found")

    try:
        results = organizer_service.organize_series(db, series_id=series_id, dry_run=False)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Organize failed: {exc}")

    return [OrganizeProposal(**r) for r in results]


@router.post("/organize-all", response_model=List[OrganizeProposal])
def organize_all(db: Session = Depends(get_db)):
    """Rename and move files for all series in the library."""
    try:
        results = organizer_service.organize_all(db, dry_run=False)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Organize-all failed: {exc}")

    return [OrganizeProposal(**r) for r in results]
