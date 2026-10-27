import hashlib
import io
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from docuquery.database import get_db
from docuquery.models.user import User
from docuquery.models.document import Document
from docuquery.schemas.document import DocumentOut, DocumentListResponse, DocumentStatusResponse
from docuquery.services.storage_service import get_storage_service
from docuquery.services.pdf_service import validate_pdf_bytes
from docuquery.worker.tasks import process_document_indexing
from docuquery.api.deps import get_current_user
from docuquery.config import settings

router = APIRouter(prefix="/documents", tags=["Documents"])


@router.post("/upload", response_model=DocumentOut, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Upload and queue a PDF document for indexing.
    Validates content, enforces user limits, and stores with a server-controlled key.
    """
    # 1. Stream file bytes with size enforcement to prevent memory exhaustion DoS
    CHUNK_READ_SIZE = 64 * 1024  # 64 KB chunks
    buffer = io.BytesIO()
    file_size = 0
    while True:
        chunk = await file.read(CHUNK_READ_SIZE)
        if not chunk:
            break
        file_size += len(chunk)
        if file_size > settings.MAX_UPLOAD_SIZE_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File exceeds maximum upload size of {settings.MAX_UPLOAD_SIZE_BYTES // (1024 * 1024)} MB",
            )
        buffer.write(chunk)

    if file_size == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty",
        )
    content = buffer.getvalue()

    # 2. Check per-user storage quota
    current_storage_usage = (
        db.query(func.coalesce(func.sum(Document.file_size), 0))
        .filter(Document.user_id == current_user.id)
        .scalar()
    )
    if (current_storage_usage + file_size) > settings.USER_STORAGE_LIMIT_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User storage quota exceeded. Please delete existing documents to upload more.",
        )

    # 3. Validate PDF format and structure
    try:
        pdf_doc = validate_pdf_bytes(content)
        detected_pages = pdf_doc.page_count
        pdf_doc.close()
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    # 4. Generate checksum and server-controlled storage key
    checksum = hashlib.sha256(content).hexdigest()
    doc_id = str(uuid.uuid4())
    safe_storage_key = f"documents/{current_user.id}/{doc_id}.pdf"

    # 5. Save to object storage
    storage = get_storage_service()
    try:
        storage.put_object(safe_storage_key, content, content_type="application/pdf")
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to store document file in object storage",
        )

    # 6. Sanitize display filename
    clean_filename = file.filename or "document.pdf"
    clean_filename = clean_filename.replace("\x00", "").strip()
    if len(clean_filename) > 255:
        clean_filename = clean_filename[:250] + ".pdf"

    # 7. Create database record
    doc_record = Document(
        id=doc_id,
        user_id=current_user.id,
        filename=clean_filename,
        storage_key=safe_storage_key,
        file_size=file_size,
        page_count=detected_pages,
        checksum=checksum,
        status="queued",
    )
    db.add(doc_record)
    db.commit()
    db.refresh(doc_record)

    # 8. Dispatch indexing task
    try:
        process_document_indexing.delay(doc_record.id, current_user.id)
    except Exception:
        # If worker queue dispatch fails, attempt synchronous run or mark error
        try:
            process_document_indexing(doc_record.id, current_user.id)
            db.refresh(doc_record)
        except Exception:
            doc_record.status = "failed"
            doc_record.error_message = "Indexing worker unavailable"
            db.commit()

    return doc_record


@router.get("", response_model=DocumentListResponse)
def list_documents(
    search: Optional[str] = Query(default=None, description="Search by filename"),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List documents belonging to the authenticated user."""
    query = db.query(Document).filter(Document.user_id == current_user.id)
    if search:
        query = query.filter(Document.filename.ilike(f"%{search.strip()}%"))

    total = query.count()
    items = query.order_by(Document.created_at.desc()).offset(offset).limit(limit).all()

    return DocumentListResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{document_id}", response_model=DocumentOut)
def get_document(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve details for a single document."""
    doc = (
        db.query(Document)
        .filter(Document.id == document_id, Document.user_id == current_user.id)
        .first()
    )
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )
    return doc


@router.get("/{document_id}/download")
def download_document(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Stream PDF document content for viewing or download."""
    doc = (
        db.query(Document)
        .filter(Document.id == document_id, Document.user_id == current_user.id)
        .first()
    )
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    storage = get_storage_service()
    try:
        data = storage.get_object(doc.storage_key)
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document file not found in storage",
        )

    return StreamingResponse(
        io.BytesIO(data),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="{doc.filename}"',
            "Content-Length": str(len(data)),
        },
    )


@router.get("/{document_id}/status", response_model=DocumentStatusResponse)
def get_document_status(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Check indexing status of a document."""
    doc = (
        db.query(Document)
        .filter(Document.id == document_id, Document.user_id == current_user.id)
        .first()
    )
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )
    return DocumentStatusResponse(
        id=doc.id,
        status=doc.status,
        page_count=doc.page_count,
        error_message=doc.error_message,
    )


@router.post("/{document_id}/retry", response_model=DocumentOut)
def retry_document_indexing(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retry indexing for a failed document."""
    doc = (
        db.query(Document)
        .filter(Document.id == document_id, Document.user_id == current_user.id)
        .first()
    )
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    doc.status = "queued"
    doc.error_message = None
    db.commit()
    db.refresh(doc)

    try:
        process_document_indexing.delay(doc.id, current_user.id)
    except Exception:
        try:
            process_document_indexing(doc.id, current_user.id)
            db.refresh(doc)
        except Exception:
            doc.status = "failed"
            doc.error_message = "Indexing worker unavailable"
            db.commit()

    return doc


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a document, its storage object, and its indexed chunks."""
    doc = (
        db.query(Document)
        .filter(Document.id == document_id, Document.user_id == current_user.id)
        .first()
    )
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    # Delete storage object
    storage = get_storage_service()
    storage.delete_object(doc.storage_key)

    # Delete from database (cascades to chunks)
    db.delete(doc)
    db.commit()
    return None
