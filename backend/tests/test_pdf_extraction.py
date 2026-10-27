import pytest
from docuquery.services.pdf_service import (
    validate_pdf_bytes,
    extract_pages_from_pdf,
    normalize_page_text,
)
from docuquery.services.chunking_service import create_chunks_from_pages


def test_pdf_extraction_page_number_preservation(create_pdf_bytes):
    # Create 3-page PDF with distinct text on each page
    page1_text = "Page 1: DocuQuery architecture consists of FastAPI, PostgreSQL, and PyMuPDF."
    page2_text = "Page 2: Vector embeddings are generated with configurable dimensions."
    page3_text = "Page 3: Answers must be grounded strictly in retrieved context."

    pdf_bytes = create_pdf_bytes([page1_text, page2_text, page3_text])

    pages = extract_pages_from_pdf(pdf_bytes)
    assert len(pages) == 3

    assert pages[0].page_number == 1
    assert "FastAPI" in pages[0].text

    assert pages[1].page_number == 2
    assert "Vector embeddings" in pages[1].text

    assert pages[2].page_number == 3
    assert "grounded strictly" in pages[2].text


def test_chunking_preserves_page_numbers(create_pdf_bytes):
    page1_text = "Intro to system. " * 30  # longer text that will get chunked
    page2_text = "Deep dive into RAG. " * 30

    pdf_bytes = create_pdf_bytes([page1_text, page2_text])
    pages = extract_pages_from_pdf(pdf_bytes)

    chunks = create_chunks_from_pages(pages, chunk_size=300, chunk_overlap=50)
    assert len(chunks) > 2

    page1_chunks = [c for c in chunks if c.page_number == 1]
    page2_chunks = [c for c in chunks if c.page_number == 2]

    assert len(page1_chunks) >= 1
    assert len(page2_chunks) >= 1

    # Check global chunk index increments monotonically
    for i in range(len(chunks)):
        assert chunks[i].chunk_index == i


def test_validate_empty_bytes():
    with pytest.raises(ValueError, match="empty"):
        validate_pdf_bytes(b"")


def test_validate_invalid_magic_bytes():
    with pytest.raises(ValueError, match="missing PDF magic header"):
        validate_pdf_bytes(b"This is plain text not a PDF document")


def test_validate_corrupted_pdf():
    corrupted = b"%PDF-1.4\ncorrupted bytes trailing garbage data"
    with pytest.raises(ValueError, match="Malformed or corrupted PDF"):
        validate_pdf_bytes(corrupted)


def test_validate_encrypted_pdf(create_pdf_bytes):
    pdf_bytes = create_pdf_bytes(["Secret financial report"], encrypt_password="SecretPassword123")
    with pytest.raises(ValueError, match="Encrypted or password-protected"):
        validate_pdf_bytes(pdf_bytes)
