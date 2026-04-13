from typing import Optional
from pydantic import BaseModel, field_validator
import os


class RootFolderCreate(BaseModel):
    path: str
    label: Optional[str] = None

    @field_validator("path")
    @classmethod
    def path_must_be_absolute(cls, v: str) -> str:
        v = v.strip()
        if not os.path.isabs(v):
            raise ValueError("Path must be an absolute path")
        return v


class RootFolderUpdate(BaseModel):
    label: Optional[str] = None


class RootFolderResponse(BaseModel):
    id: int
    path: str
    label: Optional[str] = None
    free_space: Optional[int] = None
    series_count: int = 0
    accessible: bool = False

    model_config = {"from_attributes": True}


class RootFolderValidation(BaseModel):
    accessible: bool
    free_space: Optional[int] = None
    error: Optional[str] = None
