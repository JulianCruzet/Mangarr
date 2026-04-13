import asyncio
import os
from typing import Any, Dict, List, Optional, Tuple

import httpx

from app.config import get_settings

MANGADEX_BASE_URL = "https://api.mangadex.org"
MANGADEX_UPLOADS_URL = "https://uploads.mangadex.org"
USER_AGENT = "Mangarr/1.0"

# Rate limiter: at most 5 concurrent requests
_semaphore = asyncio.Semaphore(5)


def _normalize_title(titles: Dict[str, str]) -> str:
    """Prefer 'en', fallback to 'ja-ro', then first available key."""
    if "en" in titles:
        return titles["en"]
    if "ja-ro" in titles:
        return titles["ja-ro"]
    if titles:
        return next(iter(titles.values()))
    return "Unknown"


def _parse_manga_data(manga_data: Dict[str, Any]) -> Dict[str, Any]:
    """Extract normalised fields from a MangaDex manga object."""
    attributes = manga_data.get("attributes", {})

    # Build title dict from title + altTitles
    titles: Dict[str, str] = {}
    raw_title = attributes.get("title", {})
    if isinstance(raw_title, dict):
        titles.update(raw_title)

    alt_titles_list: List[Dict[str, str]] = []
    for alt in attributes.get("altTitles", []):
        if isinstance(alt, dict):
            alt_titles_list.append(alt)
            titles.update(alt)

    primary_title = _normalize_title(titles)

    # Tags
    tags = []
    for tag in attributes.get("tags", []):
        tag_name = tag.get("attributes", {}).get("name", {})
        if isinstance(tag_name, dict) and "en" in tag_name:
            tags.append(tag_name["en"])

    # Cover filename from relationships
    cover_filename = None
    for rel in manga_data.get("relationships", []):
        if rel.get("type") == "cover_art":
            cover_filename = rel.get("attributes", {}).get("fileName")
            break

    # Description: prefer 'en'
    description_dict = attributes.get("description", {})
    description = description_dict.get("en") if isinstance(description_dict, dict) else None
    if not description and isinstance(description_dict, dict):
        description = next(iter(description_dict.values()), None)

    import json

    return {
        "id": manga_data.get("id"),
        "title": primary_title,
        "alt_titles_json": json.dumps(alt_titles_list),
        "description": description,
        "status": attributes.get("status"),
        "year": attributes.get("year"),
        "content_rating": attributes.get("contentRating"),
        "original_language": attributes.get("originalLanguage"),
        "tags_json": json.dumps(tags),
        "cover_filename": cover_filename,
    }


async def search_manga(
    q: str,
    limit: int = 20,
    offset: int = 0,
) -> Tuple[List[Dict[str, Any]], int]:
    """
    Search for manga on MangaDex.
    Returns (list_of_manga_dicts, total_count).
    """
    async with _semaphore:
        async with httpx.AsyncClient(
            base_url=MANGADEX_BASE_URL,
            headers={"User-Agent": USER_AGENT},
            timeout=30.0,
        ) as client:
            params = {
                "title": q,
                "limit": limit,
                "offset": offset,
                "includes[]": ["cover_art"],
                "order[relevance]": "desc",
            }
            resp = await client.get("/manga", params=params)
            resp.raise_for_status()
            data = resp.json()

    results = [_parse_manga_data(m) for m in data.get("data", [])]
    total = data.get("total", len(results))
    return results, total


async def get_manga(mangadex_id: str) -> Optional[Dict[str, Any]]:
    """
    Fetch a single manga by MangaDex UUID.
    Returns parsed manga dict or None on 404.
    """
    async with _semaphore:
        async with httpx.AsyncClient(
            base_url=MANGADEX_BASE_URL,
            headers={"User-Agent": USER_AGENT},
            timeout=30.0,
        ) as client:
            resp = await client.get(
                f"/manga/{mangadex_id}",
                params={"includes[]": ["cover_art"]},
            )
            if resp.status_code == 404:
                return None
            resp.raise_for_status()
            data = resp.json()

    return _parse_manga_data(data.get("data", {}))


async def get_manga_chapters(
    mangadex_id: str,
    lang: str = "en",
) -> List[Dict[str, Any]]:
    """
    Fetch all chapters for a manga, paginating 100 at a time.
    Returns list of chapter dicts.
    """
    chapters: List[Dict[str, Any]] = []
    offset = 0
    page_size = 100

    async with httpx.AsyncClient(
        base_url=MANGADEX_BASE_URL,
        headers={"User-Agent": USER_AGENT},
        timeout=30.0,
    ) as client:
        while True:
            async with _semaphore:
                params = {
                    "translatedLanguage[]": lang,
                    "order[chapter]": "asc",
                    "limit": page_size,
                    "offset": offset,
                }
                resp = await client.get(f"/manga/{mangadex_id}/feed", params=params)
                resp.raise_for_status()
                data = resp.json()

            page_data = data.get("data", [])
            for ch in page_data:
                attrs = ch.get("attributes", {})
                chapters.append(
                    {
                        "id": ch.get("id"),
                        "chapter_number": attrs.get("chapter"),
                        "volume_number": attrs.get("volume"),
                        "title": attrs.get("title"),
                        "language": attrs.get("translatedLanguage", lang),
                        "pages": attrs.get("pages"),
                        "publish_at": attrs.get("publishAt"),
                    }
                )

            if len(page_data) < page_size:
                break
            offset += page_size

    return chapters


def get_cover_url(manga_id: str, filename: str, size: int = 512) -> str:
    """Build the URL for a manga cover image."""
    return f"{MANGADEX_UPLOADS_URL}/covers/{manga_id}/{filename}.{size}.jpg"


async def download_cover(manga_id: str, filename: str) -> Optional[str]:
    """
    Download a cover image and save it to DATA_DIR/covers/.
    Returns the saved filename (not full path) or None on failure.
    """
    settings = get_settings()
    covers_dir = os.path.join(settings.DATA_DIR, "covers")
    os.makedirs(covers_dir, exist_ok=True)

    # Use the base filename without size suffix for storage
    save_name = filename
    save_path = os.path.join(covers_dir, save_name)

    # Don't re-download if already present
    if os.path.exists(save_path):
        return save_name

    url = get_cover_url(manga_id, filename, size=512)

    try:
        async with _semaphore:
            async with httpx.AsyncClient(
                headers={"User-Agent": USER_AGENT},
                timeout=60.0,
                follow_redirects=True,
            ) as client:
                resp = await client.get(url)
                if resp.status_code == 404:
                    # Try without the size suffix
                    alt_url = f"{MANGADEX_UPLOADS_URL}/covers/{manga_id}/{filename}"
                    resp = await client.get(alt_url)
                resp.raise_for_status()
                with open(save_path, "wb") as f:
                    f.write(resp.content)
        return save_name
    except Exception:
        return None
