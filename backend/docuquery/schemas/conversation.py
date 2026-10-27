from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict
from docuquery.schemas.chat import MessageOut


class ConversationCreate(BaseModel):
    title: Optional[str] = Field(default="New Conversation", max_length=255)


class ConversationUpdate(BaseModel):
    title: str = Field(min_length=1, max_length=255)


class ConversationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    created_at: datetime
    updated_at: datetime
    message_count: int = 0


class ConversationDetailOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    created_at: datetime
    updated_at: datetime
    messages: List[MessageOut]
