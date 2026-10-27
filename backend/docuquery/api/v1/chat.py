from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from docuquery.database import get_db
from docuquery.models.user import User
from docuquery.schemas.chat import MessageCreate, ChatResponse
from docuquery.services.rag_service import execute_rag_pipeline
from docuquery.api.deps import get_current_user

router = APIRouter(prefix="/chat", tags=["Chat & RAG"])


@router.post("/conversations/{conversation_id}/messages", response_model=ChatResponse)
def send_message(
    conversation_id: str,
    message_in: MessageCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Submit a question to a conversation.
    Retrieves grounded document passages, generates evidence-based answer, and returns citations.
    """
    try:
        response_dict = execute_rag_pipeline(
            db=db,
            user_id=current_user.id,
            conversation_id=conversation_id,
            question=message_in.question,
            selected_document_ids=message_in.selected_document_ids,
        )
        return response_dict
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(ve),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate grounded answer",
        )
