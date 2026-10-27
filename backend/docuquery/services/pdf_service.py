import re
from typing import List
from dataclasses import dataclass
import pymupdf
from docuquery.config import settings


@dataclass
class PageText:
    page_number: int  # 1-indexed
    text: str


def validate_pdf_bytes(data: bytes) -> pymupdf.Document:
    """
    Validate that raw bytes constitute a valid, readable, unencrypted PDF.
    Raises ValueError on validation failure.
    """
    if not data:
        raise ValueError("File content is empty")

    if len(data) > settings.MAX_UPLOAD_SIZE_BYTES:
        raise ValueError(
            f"File size exceeds maximum allowed size of {settings.MAX_UPLOAD_SIZE_BYTES // (1024 * 1024)} MB"
        )

    # Magic byte check
    if not data.startswith(b"%PDF-"):
        raise ValueError("File is not a valid PDF document (missing PDF magic header)")

    try:
        doc = pymupdf.open(stream=data, filetype="pdf")
    except Exception as e:
        raise ValueError(f"Malformed or corrupted PDF file: {str(e)}")

    if doc.is_encrypted:
        doc.close()
        raise ValueError("Encrypted or password-protected PDFs are not supported")

    if doc.page_count == 0:
        doc.close()
        raise ValueError("PDF document has no pages")

    if doc.page_count > settings.MAX_DOCUMENT_PAGES:
        pages = doc.page_count
        doc.close()
        raise ValueError(f"PDF exceeds maximum page limit of {settings.MAX_DOCUMENT_PAGES} pages (found {pages})")

    return doc


def normalize_page_text(raw_text: str) -> str:
    """
    Normalize text without destroying meaningful sentence/paragraph boundaries.
    Handles hyphenated line breaks, running footers, and redundant whitespace.
    """
    if not raw_text:
        return ""
    # Strip null bytes and non-printable control characters except standard whitespace
    cleaned = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", raw_text)
    # Standardize line breaks
    cleaned = cleaned.replace("\r\n", "\n").replace("\r", "\n")
    # Rejoin words hyphenated at line boundaries (e.g. "com- \n pliance" -> "compliance")
    cleaned = re.sub(r"(\b[A-Za-z]+)-\s*\n\s*([A-Za-z]+\b)", r"\1\2", cleaned)
    # Filter common running header/footer lines like "Page 1 of 10" or "--- Page 2 ---"
    lines = cleaned.split("\n")
    filtered_lines = []
    for line in lines:
        stripped_line = line.strip()
        # Skip pure page number footers
        if re.match(r"^(?:page\s+\d+(?:\s+of\s+\d+)?|-+\s*\d+\s*-+|\d+\s*/\s*\d+)$", stripped_line, re.IGNORECASE):
            continue
        filtered_lines.append(line)
    cleaned = "\n".join(filtered_lines)
    # Collapse lines with only spaces
    cleaned = re.sub(r"[ \t]+$", "", cleaned, flags=re.MULTILINE)
    # Collapse more than two consecutive newlines to two
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    # Merge single soft line-breaks inside paragraphs into spaces, preserving paragraph breaks (\n\n)
    paragraphs = cleaned.split("\n\n")
    normalized_paragraphs = []
    for p in paragraphs:
        # Replace internal single newlines with space
        joined = re.sub(r"(?<!\n)\n(?!\n)", " ", p)
        joined = re.sub(r"[ \t]+", " ", joined).strip()
        if joined:
            normalized_paragraphs.append(joined)
    cleaned = "\n\n".join(normalized_paragraphs)
    return cleaned.strip()


def extract_pages_from_pdf(data: bytes) -> List[PageText]:
    """
    Extract text page-by-page preserving original page numbers.
    Explicitly checks for scanned/image-only PDFs lacking an embedded text layer.
    """
    doc = validate_pdf_bytes(data)
    pages: List[PageText] = []
    total_text_len = 0
    total_images_count = 0

    try:
        for p_idx in range(doc.page_count):
            page = doc[p_idx]
            text = page.get_text("text") or ""
            normalized = normalize_page_text(text)
            pages.append(PageText(page_number=p_idx + 1, text=normalized))
            total_text_len += len(normalized)
            total_images_count += len(page.get_images())

        # If document has pages with images but almost no extractable text, flag as scanned
        if doc.page_count > 0 and total_images_count > 0 and total_text_len < 20:
            raise ValueError(
                "Scanned or image-only PDF detected without an embedded text layer. "
                "DocuQuery requires digital text-based PDFs or an OCR pipeline."
            )
    finally:
        doc.close()
    return pages
