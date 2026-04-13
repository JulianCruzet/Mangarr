from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple


class MetadataProvider(ABC):
    """Abstract base class for metadata providers."""

    name: str  # "mangadex" or "mangabaka"

    @abstractmethod
    async def search(
        self, query: str, limit: int = 20, offset: int = 0
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Search for manga by title.

        Returns (results_list, total_count).
        """
        pass

    @abstractmethod
    async def get_manga(self, provider_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetch a single manga by provider-specific ID.

        Returns normalized manga dict or None on 404/not found.
        """
        pass

    @abstractmethod
    async def get_chapters(
        self, provider_id: str, lang: str = "en"
    ) -> List[Dict[str, Any]]:
        """
        Fetch all chapters for a manga.

        Returns list of normalized chapter dicts.
        """
        pass

    @abstractmethod
    async def download_cover(
        self, provider_id: str, cover_info: Any
    ) -> Optional[str]:
        """
        Download a cover image and save it to DATA_DIR/covers/.

        Returns the saved filename (not full path) or None on failure.
        """
        pass
