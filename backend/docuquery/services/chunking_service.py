import re
from dataclasses import dataclass
from typing import List, Optional
from docuquery.services.pdf_service import PageText
from docuquery.config import settings


@dataclass
class ChunkItem:
    page_number: int
    chunk_index: int
    content: str
    token_count: int
    section_title: Optional[str] = None
    extraction_version: str = "v2"


def _split_into_sentences(text: str) -> List[str]:
    """Split text into sentences while respecting abbreviations and numbers."""
    if not text:
        return []
    # Split on sentence terminals followed by whitespace, avoiding splitting on common titles & abbreviations
    raw_sentences = re.split(
        r"(?<!\bDr)(?<!\bMr)(?<!\bMs)(?<!\bProf)(?<!\bCorp)(?<!\bInc)(?<!\bvs)(?<!\be\.g)(?<!\bi\.e)(?<=[.!?])\s+",
        text,
    )
    sentences = [s.strip() for s in raw_sentences if s.strip()]
    return sentences if sentences else [text]


def create_chunks_from_pages(
    pages: List[PageText],
    chunk_size: int = settings.CHUNK_SIZE,
    chunk_overlap: int = settings.CHUNK_OVERLAP,
    version: str = settings.CHUNK_EXTRACTION_VERSION,
) -> List[ChunkItem]:
    """
    Structure-aware chunking:
    1. Preserves original page boundaries (chunks never cross page borders).
    2. Respects paragraphs and sentence boundaries.
    3. Detects section headings and propagates section context.
    4. Applies configurable chunk size and overlap smoothly.
    """
    chunks: List[ChunkItem] = []
    global_chunk_idx = 0
    current_section: Optional[str] = None

    for page in pages:
        text = page.text.strip()
        if not text:
            continue

        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        if not paragraphs:
            paragraphs = [text]

        # Break paragraphs into units with section detection
        units = []
        for p in paragraphs:
            # Check if paragraph looks like a section header (short line, no period)
            lines = p.split("\n")
            first_line = lines[0].strip()
            if len(first_line) < 80 and not first_line.endswith((".", ":", ";")) and len(lines) <= 2:
                current_section = first_line.lstrip("#* \t")

            # If paragraph fits within chunk_size, treat as a single unit
            if len(p) <= chunk_size:
                units.append((p, current_section))
            else:
                # Break large paragraph into sentences
                sentences = _split_into_sentences(p)
                for s in sentences:
                    units.append((s, current_section))

        # Accumulate units into chunks
        current_chunk_parts: List[str] = []
        current_chunk_len = 0
        current_unit_idx = 0

        while current_unit_idx < len(units):
            unit_text, unit_section = units[current_unit_idx]
            candidate_len = current_chunk_len + (len(unit_text) + 1 if current_chunk_parts else len(unit_text))

            if candidate_len <= chunk_size or not current_chunk_parts:
                current_chunk_parts.append(unit_text)
                current_chunk_len = candidate_len
                current_unit_idx += 1
            else:
                # Finalize current chunk
                content = " ".join(current_chunk_parts).strip()
                if content:
                    chunks.append(
                        ChunkItem(
                            page_number=page.page_number,
                            chunk_index=global_chunk_idx,
                            content=content,
                            token_count=len(content.split()),
                            section_title=unit_section,
                            extraction_version=version,
                        )
                    )
                    global_chunk_idx += 1

                # Calculate overlap: rewind to carry forward trailing sentence/unit
                overlap_accum = 0
                rewind_count = 0
                for prev_part in reversed(current_chunk_parts):
                    if overlap_accum + len(prev_part) <= chunk_overlap:
                        overlap_accum += len(prev_part)
                        rewind_count += 1
                    else:
                        break

                if rewind_count > 0:
                    current_chunk_parts = current_chunk_parts[-rewind_count:]
                    current_chunk_len = sum(len(p) for p in current_chunk_parts) + (len(current_chunk_parts) - 1)
                else:
                    current_chunk_parts = []
                    current_chunk_len = 0

        # Finalize trailing chunk on page
        if current_chunk_parts:
            content = " ".join(current_chunk_parts).strip()
            if content:
                chunks.append(
                    ChunkItem(
                        page_number=page.page_number,
                        chunk_index=global_chunk_idx,
                        content=content,
                        token_count=len(content.split()),
                        section_title=current_section,
                        extraction_version=version,
                    )
                )
                global_chunk_idx += 1

    return chunks
