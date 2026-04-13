from app.providers.mangadex import MangaDexProvider
from app.providers.mangabaka import MangaBakaProvider

PROVIDERS = {
    "mangadex": MangaDexProvider(),
    "mangabaka": MangaBakaProvider(),
}

__all__ = ["PROVIDERS", "MangaDexProvider", "MangaBakaProvider"]
