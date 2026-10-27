import pytest
from docuquery.worker.tasks import process_document_indexing
from docuquery.models.document import Document
from docuquery.models.chunk import DocumentChunk


def test_indexing_idempotency(client, auth_headers_user_a, create_pdf_bytes, db):
    pdf_bytes = create_pdf_bytes(["Sample text for idempotency check." * 5])
    up_resp = client.post(
        "/api/v1/documents/upload",
        files={"file": ("idempotency.pdf", pdf_bytes, "application/pdf")},
        headers=auth_headers_user_a,
    )
    doc_id = up_resp.json()["id"]

    # Initial chunk count
    count1 = db.query(DocumentChunk).filter(DocumentChunk.document_id == doc_id).count()
    assert count1 > 0

    # Execute task a second time
    user_a = up_resp.json()
    doc_record = db.query(Document).filter(Document.id == doc_id).first()
    process_document_indexing(doc_id, doc_record.user_id)

    # Count must remain exactly the same (no duplicates)
    count2 = db.query(DocumentChunk).filter(DocumentChunk.document_id == doc_id).count()
    assert count1 == count2


def test_indexing_retry_workflow(client, auth_headers_user_a, create_pdf_bytes, db):
    pdf_bytes = create_pdf_bytes(["Valid content for retry."])
    up_resp = client.post(
        "/api/v1/documents/upload",
        files={"file": ("retry_test.pdf", pdf_bytes, "application/pdf")},
        headers=auth_headers_user_a,
    )
    doc_id = up_resp.json()["id"]

    # Manually simulate failure
    doc = db.query(Document).filter(Document.id == doc_id).first()
    doc.status = "failed"
    doc.error_message = "Simulated worker failure"
    db.commit()

    # Call retry endpoint
    retry_resp = client.post(f"/api/v1/documents/{doc_id}/retry", headers=auth_headers_user_a)
    assert retry_resp.status_code == 200

    # Status should be queued or ready
    status_resp = client.get(f"/api/v1/documents/{doc_id}/status", headers=auth_headers_user_a)
    assert status_resp.json()["status"] in ["queued", "processing", "ready"]
