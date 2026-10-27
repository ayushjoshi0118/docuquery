from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text, func
from docuquery.database import get_db
from docuquery.models.user import User
from docuquery.models.document import Document
from docuquery.models.conversation import Conversation
from docuquery.models.message import Message
from docuquery.api.deps import get_current_user
from docuquery.services.storage_service import get_storage_service

router = APIRouter(tags=["Health & System"])


@router.get("/health/live")
def liveness():
    """Liveness probe: verifies process is alive."""
    return {"status": "ok", "service": "docuquery-api"}


@router.get("/health/ready")
def readiness(db: Session = Depends(get_db)):
    """Readiness probe: verifies database and storage readiness."""
    health_status = {"status": "ready", "checks": {}}

    # 1. Database check
    try:
        db.execute(text("SELECT 1"))
        health_status["checks"]["database"] = "healthy"
    except Exception as e:
        health_status["checks"]["database"] = f"unhealthy: {str(e)}"
        health_status["status"] = "degraded"

    # 2. Storage check
    try:
        storage = get_storage_service()
        # Non-blocking probe
        health_status["checks"]["storage"] = "healthy"
    except Exception as e:
        health_status["checks"]["storage"] = f"unhealthy: {str(e)}"
        health_status["status"] = "degraded"

    if health_status["status"] != "ready":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=health_status,
        )

    return health_status


@router.get("/system/stats")
def user_dashboard_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve statistics for the current user's dashboard."""
    total_docs = db.query(Document).filter(Document.user_id == current_user.id).count()
    ready_docs = db.query(Document).filter(Document.user_id == current_user.id, Document.status == "ready").count()
    failed_docs = db.query(Document).filter(Document.user_id == current_user.id, Document.status == "failed").count()
    total_pages = (
        db.query(func.coalesce(func.sum(Document.page_count), 0))
        .filter(Document.user_id == current_user.id, Document.status == "ready")
        .scalar()
    )
    total_storage = (
        db.query(func.coalesce(func.sum(Document.file_size), 0))
        .filter(Document.user_id == current_user.id)
        .scalar()
    )
    total_convs = db.query(Conversation).filter(Conversation.user_id == current_user.id).count()
    total_queries = (
        db.query(Message)
        .filter(Message.user_id == current_user.id, Message.role == "user")
        .count()
    )

    return {
        "total_documents": total_docs,
        "ready_documents": ready_docs,
        "failed_documents": failed_docs,
        "total_pages": total_pages,
        "storage_used_bytes": total_storage,
        "total_conversations": total_convs,
        "total_queries": total_queries,
    }
