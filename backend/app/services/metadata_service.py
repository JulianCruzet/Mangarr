from typing import Any, Dict, List, Optional, Tuple

from app.providers import PROVIDERS


async def search_manga(
    query: str,
    provider: str = "mangadex",
    limit: int = 20,
    offset: int = 0,
) -> Tuple[List[Dict[str, Any]], int]:
    """
    Search for manga using the specified provider.
    Returns (list_of_manga_dicts, total_count).
    """
    if provider not in PROVIDERS:
        raise ValueError(f"Unknown provider: {provider}")

    return await PROVIDERS[provider].search(query, limit=limit, offset=offset)


async def get_manga(provider: str, provider_id: str) -> Optional[Dict[str, Any]]:
    """
    Fetch a single manga by provider-specific ID.
    Returns parsed manga dict or None on 404.
    """
    if provider not in PROVIDERS:
        raise ValueError(f"Unknown provider: {provider}")

    return await PROVIDERS[provider].get_manga(provider_id)


async def get_manga_chapters(
    provider: str,
    provider_id: str,
    lang: str = "en",
) -> List[Dict[str, Any]]:
    """
    Fetch all chapters for a manga from the specified provider.
    Returns list of chapter dicts.
    """
    if provider not in PROVIDERS:
        raise ValueError(f"Unknown provider: {provider}")

    return await PROVIDERS[provider].get_chapters(provider_id, lang=lang)


async def download_cover(
    provider: str,
    provider_id: str,
    cover_info: Any,
) -> Optional[str]:
    """
    Download a cover image and save it to DATA_DIR/covers/.
    Returns the saved filename (not full path) or None on failure.
    """
    if provider not in PROVIDERS:
        raise ValueError(f"Unknown provider: {provider}")

    return await PROVIDERS[provider].download_cover(provider_id, cover_info)


def get_available_providers() -> List[str]:
    """Get list of available provider names."""
    return list(PROVIDERS.keys())
