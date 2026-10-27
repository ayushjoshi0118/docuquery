import logging
from docuquery.worker.celery_app import celery_app
from docuquery.database import SessionLocal
from docuquery.models.document import Document
from docuquery.models.chunk import DocumentChunk
from docuquery.services.storage_service import get_storage_service
from docuquery.services.pdf_service import extract_pages_from_pdf
from docuquery.services.chunking_service import create_chunks_from_pages
from docuquery.services.llm_adapter import get_llm_adapter

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=10)
def process_document_indexing(self, document_id: str, user_id: str):
    """
    Background worker task to extract, chunk, embed, and index a PDF document.
    Ensures idempotency by clearing prior chunks and updating status atomically.
    """
    logger.info(f"Starting indexing for document_id={document_id}, user_id={user_id}")
    db = SessionLocal()
    try:
        # 1. Fetch document and verify ownership
        doc = (
            db.query(Document)
            .filter(Document.id == document_id, Document.user_id == user_id)
            .first()
        )
        if not doc:
            logger.warning(f"Document {document_id} not found for user {user_id}. Aborting.")
            return

        doc.status = "processing"
        doc.error_message = None
        db.commit()

        # 2. Retrieve PDF bytes from storage
        storage = get_storage_service()
        pdf_bytes = storage.get_object(doc.storage_key)

        # 3. Extract text page by page
        pages = extract_pages_from_pdf(pdf_bytes)
        doc.page_count = len(pages)
        db.commit()

        if not pages or all(len(p.text.strip()) == 0 for p in pages):
            doc.status = "failed"
            doc.error_message = "Document contains no readable text"
            db.commit()
            return

        # 4. Create chunks
        chunks = create_chunks_from_pages(pages)
        if not chunks:
            doc.status = "failed"
            doc.error_message = "Could not generate text chunks from document"
            db.commit()
            return

        # 5. Generate embeddings in batches of 32
        llm = get_llm_adapter()
        chunk_texts = [c.content for c in chunks]
        embeddings = []
        batch_size = 32

        for i in range(0, len(chunk_texts), batch_size):
            batch = chunk_texts[i : i + batch_size]
            batch_emb = llm.get_embeddings(batch)
            embeddings.extend(batch_emb)

        # 6. Idempotent insertion: remove existing chunks
        db.query(DocumentChunk).filter(DocumentChunk.document_id == document_id).delete()

        # 7. Insert new chunks
        import json
        for item, emb in zip(chunks, embeddings):
            meta = {
                "section_title": item.section_title,
                "version": item.extraction_version,
            }
            chunk_record = DocumentChunk(
                document_id=document_id,
                user_id=user_id,
                page_number=item.page_number,
                chunk_index=item.chunk_index,
                content=item.content,
                token_count=item.token_count,
                embedding=emb,
                metadata_json=json.dumps(meta),
            )
            db.add(chunk_record)

        # 8. Mark ready
        doc.status = "ready"
        doc.error_message = None
        db.commit()
        logger.info(f"Indexing successfully completed for document {document_id} ({len(chunks)} chunks).")

    except ValueError as ve:
        # Validation or formatting errors should not be retried indefinitely
        logger.error(f"Permanent validation error indexing document {document_id}: {ve}")
        if 'doc' in locals() and doc:
            doc.status = "failed"
            doc.error_message = str(ve)
            db.commit()
    except Exception as exc:
        logger.exception(f"Unexpected error indexing document {document_id}: {exc}")
        if 'doc' in locals() and doc:
            doc.status = "failed"
            doc.error_message = "Indexing failed due to an internal error"
            db.commit()
        # Retry transient exceptions if retries remain
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc, countdown=10 * (2 ** self.request.retries))
    finally:
        db.close()
