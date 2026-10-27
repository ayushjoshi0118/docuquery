import pytest
from fastapi import status
from docuquery.models.chunk import DocumentChunk


def test_rag_grounded_answer_and_citations(client, auth_headers_user_a, create_pdf_bytes, db):
    # Upload document with specific known facts
    page1 = "Project Titan uses Rust for low-level systems programming."
    page2 = "The target deployment timeline for Project Titan is Q4 2026."
    pdf_bytes = create_pdf_bytes([page1, page2])

    up_resp = client.post(
        "/api/v1/documents/upload",
        files={"file": ("titan_overview.pdf", pdf_bytes, "application/pdf")},
        headers=auth_headers_user_a,
    )
    doc_id = up_resp.json()["id"]

    # Create conversation
    conv_resp = client.post("/api/v1/conversations", json={"title": "Titan Q&A"}, headers=auth_headers_user_a)
    conv_id = conv_resp.json()["id"]

    # Ask grounded question
    chat_resp = client.post(
        f"/api/v1/chat/conversations/{conv_id}/messages",
        json={"question": "What programming language does Project Titan use?"},
        headers=auth_headers_user_a,
    )
    assert chat_resp.status_code == status.HTTP_200_OK
    data = chat_resp.json()
    asst_msg = data["assistant_message"]

    # Verify answer content
    assert "Rust" in asst_msg["content"]

    # Verify citations
    citations = asst_msg["citations"]
    assert citations is not None
    assert len(citations) >= 1

    citation = citations[0]
    assert citation["document_id"] == doc_id
    assert citation["filename"] == "titan_overview.pdf"
    assert citation["page_number"] in [1, 2]
    assert "Titan" in citation["excerpt"]
    assert "chunk_id" in citation

    # Verify cited chunk actually exists in database
    db_chunk = db.query(DocumentChunk).filter(DocumentChunk.id == citation["chunk_id"]).first()
    assert db_chunk is not None
    assert db_chunk.document_id == doc_id


def test_rag_unsupported_question_insufficient_evidence(client, auth_headers_user_a, create_pdf_bytes):
    # Document about astronomy
    text = "The solar system contains eight planets orbiting the Sun."
    pdf_bytes = create_pdf_bytes([text])
    client.post(
        "/api/v1/documents/upload",
        files={"file": ("planets.pdf", pdf_bytes, "application/pdf")},
        headers=auth_headers_user_a,
    )

    conv_resp = client.post("/api/v1/conversations", json={"title": "Planets"}, headers=auth_headers_user_a)
    conv_id = conv_resp.json()["id"]

    # Ask question unrelated to document
    chat_resp = client.post(
        f"/api/v1/chat/conversations/{conv_id}/messages",
        json={"question": "What is the capital city of France?"},
        headers=auth_headers_user_a,
    )
    assert chat_resp.status_code == status.HTTP_200_OK
    data = chat_resp.json()
    asst = data["assistant_message"]

    # Must return explicit insufficient information response
    assert "couldn't find enough information" in asst["content"]
    assert asst["citations"] is None or len(asst["citations"]) == 0


def test_rag_selected_documents_filtering(client, auth_headers_user_a, create_pdf_bytes):
    doc1_bytes = create_pdf_bytes(["Solar energy utilizes photovoltaic panels to generate electricity."])
    doc2_bytes = create_pdf_bytes(["Wind energy relies on aerodynamic turbine blades."])

    up1 = client.post("/api/v1/documents/upload", files={"file": ("solar.pdf", doc1_bytes, "application/pdf")}, headers=auth_headers_user_a).json()
    up2 = client.post("/api/v1/documents/upload", files={"file": ("wind.pdf", doc2_bytes, "application/pdf")}, headers=auth_headers_user_a).json()

    conv_id = client.post("/api/v1/conversations", json={"title": "Energy"}, headers=auth_headers_user_a).json()["id"]

    # Only select doc2 (wind) and ask about photovoltaic panels
    resp = client.post(
        f"/api/v1/chat/conversations/{conv_id}/messages",
        json={"question": "How does solar photovoltaic energy work?", "selected_document_ids": [up2["id"]]},
        headers=auth_headers_user_a,
    )
    assert resp.status_code == status.HTTP_200_OK
    asst = resp.json()["assistant_message"]

    # Since solar document was NOT selected, assistant cannot answer and cannot cite solar
    assert "couldn't find enough information" in asst["content"]
    assert asst["citations"] is None or len(asst["citations"]) == 0
