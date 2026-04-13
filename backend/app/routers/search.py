from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy.orm import Session

from app.services import metadata_service
from app.schemas.search import MangaSearchResult, MangaSearchResponse, ChapterSearchResult
from app.models.series import Series

router = APIRouter(prefix="/search", tags=["search"])


@router.get("/manga", response_model=MangaSearchResponse)
async def search_manga(
    q: str = Query(..., min_length=1, description="Search query"),
    provider: str = Query("mangadex", description="Metadata provider"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """Search for manga by title from the specified metadata provider."""
    try:
        results, total = await metadata_service.search_manga(
            q, provider=provider, limit=limit, offset=offset
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Metadata provider error: {exc}")

    manga_results = []
    for m in results:
        cover_url = None
        # Build cover URL based on provider
        if m.get("cover_filename") and m.get("id"):
            if provider == "mangadex":
                from app.providers.mangadex import MangaDexProvider
                provider_instance = MangaDexProvider()
                cover_url = provider_instance._get_cover_url(m["id"], m["cover_filename"])
            elif provider == "mangabaka" and m.get("cover_url"):
                cover_url = m.get("cover_url")

        manga_results.append(
            MangaSearchResult(
                id=m["id"],
                title=m["title"],
                alt_titles=[],
                description=m.get("description"),
                status=m.get("status"),
                year=m.get("year"),
                content_rating=m.get("content_rating"),
                original_language=m.get("original_language"),
                tags=[],
                cover_url=cover_url,
                cover_filename=m.get("cover_filename"),
            )
        )

    return MangaSearchResponse(
        results=manga_results,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/manga/{manga_id}", response_model=MangaSearchResult)
async def get_manga_detail(
    manga_id: str,
    provider: str = Query("mangadex", description="Metadata provider"),
):
    """Get full details for a single manga from the specified metadata provider."""
    try:
        manga_data = await metadata_service.get_manga(provider, manga_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Metadata provider error: {exc}")

    if not manga_data:
        raise HTTPException(status_code=404, detail=f"Manga {manga_id} not found on {provider}")

    cover_url = None
    if manga_data.get("cover_filename") and manga_data.get("id"):
        if provider == "mangadex":
            from app.providers.mangadex import MangaDexProvider
            provider_instance = MangaDexProvider()
            cover_url = provider_instance._get_cover_url(
                manga_data["id"], manga_data["cover_filename"]
            )
        elif provider == "mangabaka" and manga_data.get("cover_url"):
            cover_url = manga_data.get("cover_url")

    import json

    alt_titles = []
    if manga_data.get("alt_titles_json"):
        try:
            alt_titles = json.loads(manga_data["alt_titles_json"])
        except (json.JSONDecodeError, TypeError):
            pass

    tags = []
    if manga_data.get("tags_json"):
        try:
            tags = json.loads(manga_data["tags_json"])
        except (json.JSONDecodeError, TypeError):
            pass

    return MangaSearchResult(
        id=manga_data["id"],
        title=manga_data["title"],
        alt_titles=alt_titles,
        description=manga_data.get("description"),
        status=manga_data.get("status"),
        year=manga_data.get("year"),
        content_rating=manga_data.get("content_rating"),
        original_language=manga_data.get("original_language"),
        tags=tags,
        cover_url=cover_url,
        cover_filename=manga_data.get("cover_filename"),
    )


@router.get("/manga/{manga_id}/chapters", response_model=List[ChapterSearchResult])
async def get_manga_chapters(
    manga_id: str,
    provider: str = Query("mangadex", description="Metadata provider"),
    lang: str = Query("en", description="Language code"),
):
    """Fetch all chapters for a manga from the specified metadata provider."""
    try:
        chapters = await metadata_service.get_manga_chapters(provider, manga_id, lang=lang)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Metadata provider error: {exc}")

    return [
        ChapterSearchResult(
            id=ch["id"],
            chapter_number=ch.get("chapter_number"),
            volume_number=ch.get("volume_number"),
            title=ch.get("title"),
            language=ch.get("language", lang),
            pages=ch.get("pages"),
            publish_at=ch.get("publish_at"),
        )
        for ch in chapters
    ]
