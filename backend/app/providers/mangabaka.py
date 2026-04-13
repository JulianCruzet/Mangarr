import asyncio
import json
import os
from typing import Any, Dict, List, Optional, Tuple

import httpx

from app.config import get_settings
from app.providers.base import MetadataProvider

MANGABAKA_BASE_URL = "https://api.mangabaka.dev"
USER_AGENT = "Mangarr/1.0"

# Rate limiter: at most 5 concurrent requests
_semaphore = asyncio.Semaphore(5)


class MangaBakaProvider(MetadataProvider):
    name = "mangabaka"

    @staticmethod
    def _normalize_title(title: str) -> str:
        """Normalize title from MangaBaka."""
        if isinstance(title, dict):
            # If title is a dict, try to extract English or first value
            if "en" in title:
                return title["en"]
            return next(iter(title.values()), "Unknown")
        return title or "Unknown"

    @staticmethod
    def _parse_manga_data(manga_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract normalized fields from a MangaBaka manga object."""
        # MangaBaka API structure differs from MangaDex, normalize it
        title = manga_data.get("title", manga_data.get("name", "Unknown"))

        alt_titles_list: List[Dict[str, str]] = []
        if "alternate_titles" in manga_data:
            for alt in manga_data.get("alternate_titles", []):
                if isinstance(alt, str):
                    alt_titles_list.append({"en": alt})
                elif isinstance(alt, dict):
                    alt_titles_list.append(alt)

        # Tags/genres
        tags = []
        for tag in manga_data.get("genres", []):
            if isinstance(tag, str):
                tags.append(tag)
            elif isinstance(tag, dict) and "name" in tag:
                tags.append(tag["name"])

        # Cover image
        cover_filename = None
        if "cover_url" in manga_data:
            # Extract filename from URL if available
            cover_url = manga_data["cover_url"]
            if cover_url:
                cover_filename = cover_url.split("/")[-1]

        description = manga_data.get("description", manga_data.get("synopsis"))

        return {
            "id": manga_data.get("id"),
            "title": title,
            "alt_titles_json": json.dumps(alt_titles_list),
            "description": description,
            "status": manga_data.get("status"),
            "year": manga_data.get("year"),
            "content_rating": None,  # MangaBaka doesn't have content rating
            "original_language": manga_data.get("original_language", "ja"),
            "tags_json": json.dumps(tags),
            "cover_filename": cover_filename,
            "cover_url": manga_data.get("cover_url"),  # Store full URL for cover download
        }

    async def search(
        self, query: str, limit: int = 20, offset: int = 0
    ) -> Tuple[List[Dict[str, Any]], int]:
        """Search for manga on MangaBaka."""
        async with _semaphore:
            async with httpx.AsyncClient(
                base_url=MANGABAKA_BASE_URL,
                headers={"User-Agent": USER_AGENT},
                timeout=30.0,
            ) as client:
                params = {
                    "q": query,
                    "limit": limit,
                    "offset": offset,
                }
                try:
                    resp = await client.get("/manga/search", params=params)
                    resp.raise_for_status()
                    data = resp.json()
                except Exception as e:
                    # If search endpoint doesn't exist, return empty results
                    return [], 0

        # Handle different response structures
        if isinstance(data, dict):
            results_list = data.get("results", data.get("data", []))
            total = data.get("total", len(results_list))
        elif isinstance(data, list):
            results_list = data
            total = len(data)
        else:
            return [], 0

        results = [self._parse_manga_data(m) for m in results_list]
        return results, total

    async def get_manga(self, provider_id: str) -> Optional[Dict[str, Any]]:
        """Fetch a single manga by MangaBaka ID."""
        async with _semaphore:
            async with httpx.AsyncClient(
                base_url=MANGABAKA_BASE_URL,
                headers={"User-Agent": USER_AGENT},
                timeout=30.0,
            ) as client:
                try:
                    resp = await client.get(f"/manga/{provider_id}")
                    if resp.status_code == 404:
                        return None
                    resp.raise_for_status()
                    data = resp.json()
                except Exception:
                    return None

        # Handle both direct object and nested response
        if isinstance(data, dict) and "data" in data:
            manga_data = data["data"]
        else:
            manga_data = data

        if not manga_data:
            return None

        return self._parse_manga_data(manga_data)

    async def get_chapters(
        self, provider_id: str, lang: str = "en"
    ) -> List[Dict[str, Any]]:
        """Fetch all chapters for a manga."""
        chapters: List[Dict[str, Any]] = []
        offset = 0
        page_size = 100

        async with httpx.AsyncClient(
            base_url=MANGABAKA_BASE_URL,
            headers={"User-Agent": USER_AGENT},
            timeout=30.0,
        ) as client:
            while True:
                try:
                    async with _semaphore:
                        params = {
                            "limit": page_size,
                            "offset": offset,
                        }
                        resp = await client.get(
                            f"/manga/{provider_id}/chapters",
                            params=params,
                        )
                        resp.raise_for_status()
                        data = resp.json()
                except Exception:
                    break

                # Handle different response structures
                if isinstance(data, dict):
                    page_data = data.get("results", data.get("data", []))
                elif isinstance(data, list):
                    page_data = data
                else:
                    break

                for ch in page_data:
                    chapters.append(
                        {
                            "id": ch.get("id"),
                            "chapter_number": ch.get("chapter_number", ch.get("chapter")),
                            "volume_number": ch.get("volume_number"),
                            "title": ch.get("title"),
                            "language": lang,
                            "pages": ch.get("pages"),
                            "publish_at": ch.get("published_at", ch.get("publish_at")),
                        }
                    )

                if len(page_data) < page_size:
                    break
                offset += page_size

        return chapters

    async def download_cover(
        self, provider_id: str, cover_info: Any
    ) -> Optional[str]:
        """Download a cover image from MangaBaka."""
        if not cover_info:
            return None

        settings = get_settings()
        covers_dir = os.path.join(settings.DATA_DIR, "covers")
        os.makedirs(covers_dir, exist_ok=True)

        # cover_info might be a filename or a full URL depending on how we store it
        if cover_info.startswith("http"):
            url = cover_info
            # Extract filename from URL
            save_name = cover_info.split("/")[-1].split("?")[0]
        else:
            # Assume it's a filename/path component
            url = f"https://mangabaka.org/images/covers/{cover_info}"
            save_name = cover_info.split("/")[-1]

        if not save_name:
            save_name = f"{provider_id}_cover.jpg"

        save_path = os.path.join(covers_dir, save_name)

        # Don't re-download if already present
        if os.path.exists(save_path):
            return save_name

        try:
            async with _semaphore:
                async with httpx.AsyncClient(
                    headers={"User-Agent": USER_AGENT},
                    timeout=60.0,
                    follow_redirects=True,
                ) as client:
                    resp = await client.get(url)
                    if resp.status_code == 404:
                        return None
                    resp.raise_for_status()
                    with open(save_path, "wb") as f:
                        f.write(resp.content)
            return save_name
        except Exception:
            return None
