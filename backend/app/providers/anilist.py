"""AniList GraphQL lookup helper.

Standalone module — NOT a MetadataProvider subclass.
Used to enrich series records with total volume/chapter counts.
All functions are best-effort: exceptions are caught and None is returned
so that AniList failures never break the main add_series / refresh_series flow.
"""

from typing import Optional

import httpx

ANILIST_API = "https://graphql.anilist.co"
USER_AGENT = "Mangarr/1.0"

SEARCH_QUERY = """
query ($search: String) {
  Media(search: $search, type: MANGA) {
    id
    title { romaji english native }
    volumes
    chapters
    status
    synonyms
  }
}
"""

BY_ID_QUERY = """
query ($id: Int) {
  Media(id: $id, type: MANGA) {
    id
    title { romaji english native }
    volumes
    chapters
    status
    synonyms
  }
}
"""


async def search_anilist(title: str) -> Optional[dict]:
    """Search AniList for a manga by title.

    Returns a dict with ``id``, ``volumes``, ``chapters``, ``status`` or
    ``None`` on any error / no result.
    """
    try:
        async with httpx.AsyncClient(timeout=15.0, headers={"User-Agent": USER_AGENT}) as client:
            resp = await client.post(
                ANILIST_API,
                json={"query": SEARCH_QUERY, "variables": {"search": title}},
            )
            resp.raise_for_status()
            data = resp.json()
            media = data.get("data", {}).get("Media")
            if not media:
                return None
            return {
                "id": media.get("id"),
                "volumes": media.get("volumes"),
                "chapters": media.get("chapters"),
                "status": media.get("status"),
            }
    except Exception:
        return None


async def get_anilist_by_id(anilist_id: int) -> Optional[dict]:
    """Fetch AniList media by numeric ID.

    Returns a dict with ``id``, ``volumes``, ``chapters``, ``status`` or
    ``None`` on any error / no result.
    """
    try:
        async with httpx.AsyncClient(timeout=15.0, headers={"User-Agent": USER_AGENT}) as client:
            resp = await client.post(
                ANILIST_API,
                json={"query": BY_ID_QUERY, "variables": {"id": anilist_id}},
            )
            resp.raise_for_status()
            data = resp.json()
            media = data.get("data", {}).get("Media")
            if not media:
                return None
            return {
                "id": media.get("id"),
                "volumes": media.get("volumes"),
                "chapters": media.get("chapters"),
                "status": media.get("status"),
            }
    except Exception:
        return None
