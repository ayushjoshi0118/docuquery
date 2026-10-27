import uuid
import json
from datetime import datetime, timezone
from typing import List, Any
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.types import TypeDecorator, JSON
from docuquery.database import Base
from docuquery.config import settings


def utc_now():
    return datetime.now(timezone.utc)


class EmbeddingColumn(TypeDecorator):
    """
    Adaptive vector storage column.
    Handles list of floats and JSON serialization safely across database engines.
    """
    impl = JSON
    cache_ok = True

    def process_bind_param(self, value: Any, dialect: Any) -> Any:
        if value is None:
            return None
        if isinstance(value, str):
            try:
                return json.loads(value)
            except Exception:
                return value
        if hasattr(value, "tolist"):
            return value.tolist()
        return list(value)

    def process_result_value(self, value: Any, dialect: Any) -> Any:
        if value is None:
            return None
        if isinstance(value, str):
            try:
                return json.loads(value)
            except Exception:
                return value
        return value


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), index=True, nullable=False)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    page_number = Column(Integer, nullable=False)  # 1-indexed
    chunk_index = Column(Integer, nullable=False)  # 0-indexed within document
    content = Column(Text, nullable=False)
    token_count = Column(Integer, default=0, nullable=False)
    embedding = Column(EmbeddingColumn, nullable=True)
    metadata_json = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    __table_args__ = (
        UniqueConstraint("document_id", "chunk_index", name="uq_document_chunk_idx"),
    )

    document = relationship("Document", back_populates="chunks")
