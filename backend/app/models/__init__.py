# Import all models so SQLAlchemy registers them before table creation
from app.models.root_folder import RootFolder
from app.models.series import Series, MonitorStatus
from app.models.volume import Volume
from app.models.chapter import Chapter
from app.models.imported_file import ImportedFile

__all__ = [
    "RootFolder",
    "Series",
    "MonitorStatus",
    "Volume",
    "Chapter",
    "ImportedFile",
]
