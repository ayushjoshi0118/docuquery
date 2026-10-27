import pytest
from fastapi import status


def test_user_cannot_access_other_users_document(client, auth_headers_user_a, auth_headers_user_b, create_pdf_bytes):
    pdf_bytes = create_pdf_bytes(["Confidential project details for User A only."])
    up_resp = client.post(
        "/api/v1/documents/upload",
        files={"file": ("confidential_a.pdf", pdf_bytes, "application/pdf")},
        headers=auth_headers_user_a,
    )
    doc_id = up_resp.json()["id"]

    # User B attempts to get document metadata
    resp_b = client.get(f"/api/v1/documents/{doc_id}", headers=auth_headers_user_b)
    assert resp_b.status_code == status.HTTP_404_NOT_FOUND

    # User B attempts to download document
    dl_b = client.get(f"/api/v1/documents/{doc_id}/download", headers=auth_headers_user_b)
    assert dl_b.status_code == status.HTTP_404_NOT_FOUND

    # User B attempts to delete document
    del_b = client.delete(f"/api/v1/documents/{doc_id}", headers=auth_headers_user_b)
    assert del_b.status_code == status.HTTP_404_NOT_FOUND

    # Verify User A's document is still intact
    resp_a = client.get(f"/api/v1/documents/{doc_id}", headers=auth_headers_user_a)
    assert resp_a.status_code == status.HTTP_200_OK


def test_user_cannot_access_other_users_conversation(client, auth_headers_user_a, auth_headers_user_b):
    # User A creates a conversation
    c_resp = client.post(
        "/api/v1/conversations",
        json={"title": "User A Private Chat"},
        headers=auth_headers_user_a,
    )
    conv_id = c_resp.json()["id"]

    # User B tries to view it
    get_b = client.get(f"/api/v1/conversations/{conv_id}", headers=auth_headers_user_b)
    assert get_b.status_code == status.HTTP_404_NOT_FOUND

    # User B tries to post a message into it
    post_b = client.post(
        f"/api/v1/chat/conversations/{conv_id}/messages",
        json={"question": "Can I read your data?"},
        headers=auth_headers_user_b,
    )
    assert post_b.status_code == status.HTTP_400_BAD_REQUEST

    # User B tries to rename it
    patch_b = client.patch(
        f"/api/v1/conversations/{conv_id}",
        json={"title": "Hacked Title"},
        headers=auth_headers_user_b,
    )
    assert patch_b.status_code == status.HTTP_404_NOT_FOUND

    # User B tries to delete it
    del_b = client.delete(f"/api/v1/conversations/{conv_id}", headers=auth_headers_user_b)
    assert del_b.status_code == status.HTTP_404_NOT_FOUND


def test_cross_user_retrieval_isolation(client, auth_headers_user_a, auth_headers_user_b, create_pdf_bytes):
    # User A uploads a document containing specific proprietary keyword "SuperKryptonSecret"
    secret_text = "The master passkey for project Apollo is SuperKryptonSecret."
    pdf_bytes = create_pdf_bytes([secret_text])
    client.post(
        "/api/v1/documents/upload",
        files={"file": ("super_secret.pdf", pdf_bytes, "application/pdf")},
        headers=auth_headers_user_a,
    )

    # User B creates a conversation and asks about "SuperKryptonSecret"
    conv_b = client.post("/api/v1/conversations", json={"title": "User B Research"}, headers=auth_headers_user_b).json()
    chat_resp = client.post(
        f"/api/v1/chat/conversations/{conv_b['id']}/messages",
        json={"question": "What is the SuperKryptonSecret passkey?"},
        headers=auth_headers_user_b,
    )
    assert chat_resp.status_code == status.HTTP_200_OK
    data = chat_resp.json()
    asst_msg = data["assistant_message"]

    # Must NOT disclose User A's secret
    assert "SuperKryptonSecret" not in asst_msg["content"]
    assert "couldn't find enough information" in asst_msg["content"]
    assert asst_msg["citations"] is None or len(asst_msg["citations"]) == 0
