from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict


class Citation(BaseModel):
    document_id: str
    filename: str
    page_number: int
    excerpt: str
    chunk_id: str


class MessageCreate(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    selected_document_ids: Optional[List[str]] = None


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    conversation_id: str
    role: str
    content: str
    citations: Optional[List[Citation]] = None
    created_at: datetime


class ChatResponse(BaseModel):
    user_message: MessageOut
    assistant_message: MessageOut
