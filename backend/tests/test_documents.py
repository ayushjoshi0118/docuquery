import io
import pytest
from fastapi import status
from docuquery.services.storage_service import get_storage_service


def test_upload_valid_pdf(client, auth_headers_user_a, create_pdf_bytes):
    pdf_bytes = create_pdf_bytes(["Test document for upload content verification."])
    files = {"file": ("test_doc.pdf", pdf_bytes, "application/pdf")}

    resp = client.post("/api/v1/documents/upload", files=files, headers=auth_headers_user_a)
    assert resp.status_code == status.HTTP_201_CREATED
    data = resp.json()
    assert data["filename"] == "test_doc.pdf"
    assert data["status"] in ["queued", "processing", "ready"]
    assert data["file_size"] == len(pdf_bytes)
    assert data["page_count"] == 1
    assert "id" in data


def test_upload_empty_file_rejected(client, auth_headers_user_a):
    files = {"file": ("empty.pdf", b"", "application/pdf")}
    resp = client.post("/api/v1/documents/upload", files=files, headers=auth_headers_user_a)
    assert resp.status_code == status.HTTP_400_BAD_REQUEST


def test_upload_invalid_content_rejected(client, auth_headers_user_a):
    files = {"file": ("fake.pdf", b"Not a real PDF header or body", "application/pdf")}
    resp = client.post("/api/v1/documents/upload", files=files, headers=auth_headers_user_a)
    assert resp.status_code == status.HTTP_400_BAD_REQUEST


def test_list_and_search_documents(client, auth_headers_user_a, create_pdf_bytes):
    pdf1 = create_pdf_bytes(["Alpha report on machine learning"])
    pdf2 = create_pdf_bytes(["Beta financial forecast"])

    client.post("/api/v1/documents/upload", files={"file": ("ml_report.pdf", pdf1, "application/pdf")}, headers=auth_headers_user_a)
    client.post("/api/v1/documents/upload", files={"file": ("finance_q3.pdf", pdf2, "application/pdf")}, headers=auth_headers_user_a)

    # List all
    resp = client.get("/api/v1/documents", headers=auth_headers_user_a)
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert data["total"] >= 2

    # Search filter
    search_resp = client.get("/api/v1/documents?search=finance", headers=auth_headers_user_a)
    search_data = search_resp.json()
    assert search_data["total"] == 1
    assert search_data["items"][0]["filename"] == "finance_q3.pdf"


def test_get_document_nonexistent_returns_404(client, auth_headers_user_a):
    resp = client.get("/api/v1/documents/nonexistent-doc-id-12345", headers=auth_headers_user_a)
    assert resp.status_code == status.HTTP_404_NOT_FOUND


def test_download_document_stream(client, auth_headers_user_a, create_pdf_bytes):
    pdf_bytes = create_pdf_bytes(["Document content to be downloaded and verified."])
    up_resp = client.post("/api/v1/documents/upload", files={"file": ("stream.pdf", pdf_bytes, "application/pdf")}, headers=auth_headers_user_a)
    doc_id = up_resp.json()["id"]

    resp = client.get(f"/api/v1/documents/{doc_id}/download", headers=auth_headers_user_a)
    assert resp.status_code == status.HTTP_200_OK
    assert resp.headers["content-type"] == "application/pdf"
    assert resp.content == pdf_bytes


def test_download_document_with_query_token(client, auth_headers_user_a, user_a_tokens, create_pdf_bytes):
    pdf_bytes = create_pdf_bytes(["Test download with query token parameter."])
    up_resp = client.post("/api/v1/documents/upload", files={"file": ("query_token.pdf", pdf_bytes, "application/pdf")}, headers=auth_headers_user_a)
    doc_id = up_resp.json()["id"]

    token = user_a_tokens["access_token"]
    resp = client.get(f"/api/v1/documents/{doc_id}/download?token={token}")
    assert resp.status_code == status.HTTP_200_OK
    assert resp.content == pdf_bytes


def test_delete_document_and_cleanup(client, auth_headers_user_a, create_pdf_bytes):
    pdf_bytes = create_pdf_bytes(["To be deleted"])
    up_resp = client.post("/api/v1/documents/upload", files={"file": ("delete_me.pdf", pdf_bytes, "application/pdf")}, headers=auth_headers_user_a)
    doc_id = up_resp.json()["id"]

    # Verify exists
    get_resp = client.get(f"/api/v1/documents/{doc_id}", headers=auth_headers_user_a)
    assert get_resp.status_code == status.HTTP_200_OK

    # Delete
    del_resp = client.delete(f"/api/v1/documents/{doc_id}", headers=auth_headers_user_a)
    assert del_resp.status_code == status.HTTP_204_NO_CONTENT

    # Verify 404 after deletion
    get_resp_after = client.get(f"/api/v1/documents/{doc_id}", headers=auth_headers_user_a)
    assert get_resp_after.status_code == status.HTTP_404_NOT_FOUND
