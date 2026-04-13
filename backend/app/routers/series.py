from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.series import Series
from app.models.chapter import Chapter
from app.models.volume import Volume
from app.schemas.series import (
    SeriesCreate,
    SeriesUpdate,
    SeriesResponse,
    SeriesWithStats,
    SeriesListResponse,
    VolumeResponse,
)
from app.schemas.chapter import ChapterResponse
from app.services import series_service

router = APIRouter(prefix="/series", tags=["series"])


@router.get("", response_model=SeriesListResponse)
def list_series(
    status: Optional[str] = Query(None, description="Filter by status"),
    monitor_status: Optional[str] = Query(None, description="Filter by monitor status"),
    db: Session = Depends(get_db),
):
    """List all series in the library."""
    query = db.query(Series)

    if status:
        query = query.filter(Series.status == status)
    if monitor_status:
        query = query.filter(Series.monitor_status == monitor_status)

    series_list = query.order_by(Series.title).all()
    return SeriesListResponse(
        items=[SeriesResponse.model_validate(s) for s in series_list],
        total=len(series_list),
    )


@router.post("", response_model=SeriesResponse, status_code=201)
async def add_series(
    payload: SeriesCreate,
    db: Session = Depends(get_db),
):
    """Add a manga to the library by MangaDex ID."""
    try:
        series = await series_service.add_series(
            db,
            mangadex_id=payload.mangadex_id,
            root_folder_id=payload.root_folder_id,
            monitor_status=payload.monitor_status,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to add series: {exc}")

    return SeriesResponse.model_validate(series)


@router.get("/{series_id}", response_model=SeriesWithStats)
def get_series(series_id: int, db: Session = Depends(get_db)):
    """Get a single series with volumes, chapters, and stats."""
    result = series_service.get_series_with_stats(db, series_id)
    if not result:
        raise HTTPException(status_code=404, detail=f"Series {series_id} not found")

    series: Series = result["series"]

    # Load volumes with their chapters
    volumes = db.query(Volume).filter(Volume.series_id == series_id).all()
    volumes_response = []
    for vol in volumes:
        vol_chapters = (
            db.query(Chapter)
            .filter(Chapter.volume_id == vol.id)
            .order_by(Chapter.chapter_number)
            .all()
        )
        volumes_response.append(
            VolumeResponse(
                id=vol.id,
                series_id=vol.series_id,
                volume_number=vol.volume_number,
                cover_filename=vol.cover_filename,
                chapters=[ChapterResponse.model_validate(c) for c in vol_chapters],
            )
        )

    # Chapters without a volume
    all_chapters = (
        db.query(Chapter)
        .filter(Chapter.series_id == series_id)
        .order_by(Chapter.chapter_number)
        .all()
    )

    response = SeriesWithStats(
        **SeriesResponse.model_validate(series).model_dump(),
        chapter_count=result["chapter_count"],
        downloaded_count=result["downloaded_count"],
        missing_count=result["missing_count"],
        volumes=volumes_response,
        chapters=[ChapterResponse.model_validate(c) for c in all_chapters],
    )
    return response


@router.put("/{series_id}", response_model=SeriesResponse)
def update_series(
    series_id: int,
    payload: SeriesUpdate,
    db: Session = Depends(get_db),
):
    """Update monitor status or root folder for a series."""
    series = db.query(Series).filter(Series.id == series_id).first()
    if not series:
        raise HTTPException(status_code=404, detail=f"Series {series_id} not found")

    if payload.monitor_status is not None:
        valid_statuses = {"all", "future", "none"}
        if payload.monitor_status not in valid_statuses:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid monitor_status. Must be one of: {valid_statuses}",
            )
        series.monitor_status = payload.monitor_status

    if payload.root_folder_id is not None:
        from app.models.root_folder import RootFolder
        folder = db.query(RootFolder).filter(RootFolder.id == payload.root_folder_id).first()
        if not folder:
            raise HTTPException(
                status_code=400,
                detail=f"Root folder {payload.root_folder_id} not found",
            )
        series.root_folder_id = payload.root_folder_id

    db.commit()
    db.refresh(series)
    return SeriesResponse.model_validate(series)


@router.delete("/{series_id}", status_code=204)
def delete_series(series_id: int, db: Session = Depends(get_db)):
    """Remove a series from the library (does NOT delete files)."""
    deleted = series_service.delete_series(db, series_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Series {series_id} not found")


@router.post("/{series_id}/refresh", response_model=SeriesResponse)
async def refresh_series(series_id: int, db: Session = Depends(get_db)):
    """Re-fetch metadata and chapters from MangaDex."""
    try:
        series = await series_service.refresh_series(db, series_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Refresh failed: {exc}")

    return SeriesResponse.model_validate(series)
