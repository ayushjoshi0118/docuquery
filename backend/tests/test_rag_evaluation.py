"""
Automated Pytest Suite for DocuQuery RAG Evaluation & Grounding Quality.
Verifies Recall, Page Accuracy, Fact Correctness, Abstention, Citation Validity,
and Scanned Document Handling.
"""

import pytest
import pymupdf
from tests.run_rag_eval import setup_eval_db, run_benchmark
from docuquery.services.pdf_service import extract_pages_from_pdf


@pytest.fixture(scope="module")
def eval_benchmark_metrics():
    db, user, doc_id_map = setup_eval_db()
    metrics = run_benchmark(db, user, doc_id_map)
    return metrics


def test_rag_retrieval_recall_and_page_accuracy(eval_benchmark_metrics):
    """Verify Recall@3, Recall@5, and Page-Level Retrieval Accuracy."""
    assert eval_benchmark_metrics["recall_at_3"] >= 90.0, f"Recall@3 failed: {eval_benchmark_metrics['recall_at_3']}%"
    assert eval_benchmark_metrics["recall_at_5"] >= 95.0, f"Recall@5 failed: {eval_benchmark_metrics['recall_at_5']}%"
    assert eval_benchmark_metrics["page_retrieval_acc"] >= 95.0, f"Page accuracy failed: {eval_benchmark_metrics['page_retrieval_acc']}%"


def test_rag_fact_correctness_and_grounding(eval_benchmark_metrics):
    """Verify fact correctness against ground-truth evaluation queries."""
    assert eval_benchmark_metrics["fact_correctness"] >= 90.0, f"Fact correctness failed: {eval_benchmark_metrics['fact_correctness']}%"


def test_rag_abstention_on_unsupported_questions(eval_benchmark_metrics):
    """Verify explicit abstention policy on absent / unanswerable questions (100% accuracy, 0 false answers)."""
    assert eval_benchmark_metrics["abstention_accuracy"] == 100.0, f"Abstention failed: {eval_benchmark_metrics['abstention_accuracy']}%"


def test_rag_verifiable_citations(eval_benchmark_metrics):
    """Verify citation validity: every cited chunk must exist in the database and match extracted page metadata."""
    assert eval_benchmark_metrics["citation_validity"] == 100.0, f"Citation validity failed: {eval_benchmark_metrics['citation_validity']}%"


def test_rag_latency_budget(eval_benchmark_metrics):
    """Verify average retrieval and answer latency remains within interactive budget (< 200ms)."""
    assert eval_benchmark_metrics["avg_latency_ms"] < 200.0, f"Latency budget exceeded: {eval_benchmark_metrics['avg_latency_ms']} ms"


def test_scanned_pdf_detection():
    """Verify system detects image-only / scanned PDFs lacking a text layer and provides honest error."""
    # Create empty PDF with an image drawing
    doc = pymupdf.open()
    page = doc.new_page()
    # Draw pixmap image on page without text
    pix = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, 100, 100), 1)
    page.insert_image(pymupdf.Rect(50, 50, 200, 200), pixmap=pix)
    pdf_bytes = doc.tobytes()
    doc.close()

    with pytest.raises(ValueError, match="Scanned or image-only PDF detected without an embedded text layer"):
        extract_pages_from_pdf(pdf_bytes)
