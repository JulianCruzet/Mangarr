import os
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.root_folder import RootFolder
from app.models.series import Series
from app.schemas.root_folder import (
    RootFolderCreate,
    RootFolderResponse,
    RootFolderValidation,
)
from app.utils.file_helpers import get_free_space

router = APIRouter(prefix="/library", tags=["library"])


def _folder_to_response(folder: RootFolder, db: Session) -> RootFolderResponse:
    series_count = db.query(Series).filter(Series.root_folder_id == folder.id).count()
    accessible = os.path.isdir(folder.path)

    free_space = None
    if accessible:
        try:
            free_space = get_free_space(folder.path)
        except Exception:
            pass

    return RootFolderResponse(
        id=folder.id,
        path=folder.path,
        label=folder.label,
        free_space=free_space,
        series_count=series_count,
        accessible=accessible,
    )


@router.get("/folders", response_model=List[RootFolderResponse])
def list_root_folders(db: Session = Depends(get_db)):
    """List all configured root folders."""
    folders = db.query(RootFolder).order_by(RootFolder.id).all()
    return [_folder_to_response(f, db) for f in folders]


@router.post("/folders", response_model=RootFolderResponse, status_code=201)
def create_root_folder(payload: RootFolderCreate, db: Session = Depends(get_db)):
    """Add a new root folder to the library."""
    # Check for duplicate path
    existing = db.query(RootFolder).filter(RootFolder.path == payload.path).first()
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Root folder already exists: {payload.path}",
        )

    # Compute initial free space
    free_space = None
    if os.path.isdir(payload.path):
        try:
            free_space = get_free_space(payload.path)
        except Exception:
            pass

    folder = RootFolder(
        path=payload.path,
        label=payload.label,
        free_space=free_space,
    )
    db.add(folder)
    db.commit()
    db.refresh(folder)

    return _folder_to_response(folder, db)


@router.delete("/folders/{folder_id}", status_code=204)
def delete_root_folder(folder_id: int, db: Session = Depends(get_db)):
    """Remove a root folder (does NOT delete files or series)."""
    folder = db.query(RootFolder).filter(RootFolder.id == folder_id).first()
    if not folder:
        raise HTTPException(status_code=404, detail=f"Root folder {folder_id} not found")

    # Check if any series still reference this folder
    series_count = db.query(Series).filter(Series.root_folder_id == folder_id).count()
    if series_count > 0:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot delete folder with {series_count} series. Remove or reassign series first.",
        )

    db.delete(folder)
    db.commit()


@router.get("/folders/{folder_id}/validate", response_model=RootFolderValidation)
def validate_root_folder(folder_id: int, db: Session = Depends(get_db)):
    """Check if a root folder path is accessible and return free space."""
    folder = db.query(RootFolder).filter(RootFolder.id == folder_id).first()
    if not folder:
        raise HTTPException(status_code=404, detail=f"Root folder {folder_id} not found")

    if not os.path.isdir(folder.path):
        return RootFolderValidation(
            accessible=False,
            free_space=None,
            error=f"Path not found or not a directory: {folder.path}",
        )

    try:
        free_space = get_free_space(folder.path)
        # Update stored free_space
        folder.free_space = free_space
        db.commit()
        return RootFolderValidation(accessible=True, free_space=free_space)
    except Exception as exc:
        return RootFolderValidation(
            accessible=False,
            free_space=None,
            error=str(exc),
        )


@router.get("/folders/validate-path")
def validate_path(path: str):
    """Validate an arbitrary filesystem path before adding it as a root folder."""
    if not path or not path.strip():
        return {"valid": False, "exists": False, "writable": False, "free_space": None, "error": "Path is required"}

    cleaned = path.strip()
    exists = os.path.isdir(cleaned)
    writable = os.access(cleaned, os.W_OK) if exists else False
    free_space = None
    error = None

    if exists:
        try:
            free_space = get_free_space(cleaned)
        except Exception as exc:
            error = str(exc)
    else:
        error = f"Path not found or not a directory: {cleaned}"

    return {
        "valid": exists and writable and error is None,
        "exists": exists,
        "writable": writable,
        "free_space": free_space,
        "error": error,
    }
