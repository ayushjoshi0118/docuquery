from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    filename: str
    file_size: int
    page_count: int
    checksum: str
    status: str
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class DocumentListResponse(BaseModel):
    items: List[DocumentOut]
    total: int
    limit: int
    offset: int


class DocumentStatusResponse(BaseModel):
    id: str
    status: str
    page_count: int
    error_message: Optional[str] = None
