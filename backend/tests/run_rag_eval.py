import io
import time
import pymupdf
from typing import Dict, Any, List
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from docuquery.database import Base
from docuquery.models.user import User
from docuquery.models.document import Document
from docuquery.models.chunk import DocumentChunk
from docuquery.models.conversation import Conversation
from docuquery.services.pdf_service import extract_pages_from_pdf
from docuquery.services.chunking_service import create_chunks_from_pages
from docuquery.services.llm_adapter import get_llm_adapter
from docuquery.services.rag_service import execute_rag_pipeline, search_relevant_chunks
from docuquery.services.auth_service import hash_password
from docuquery.config import settings

from tests.eval_dataset import EVAL_DOCUMENTS, EVAL_QUERIES, EvalQuery


def create_in_memory_pdf(pages_text: List[str]) -> bytes:
    doc = pymupdf.open()
    for text in pages_text:
        page = doc.new_page()
        rect = pymupdf.Rect(50, 50, 550, 750)
        page.insert_textbox(rect, text, fontsize=11)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def setup_eval_db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    db = Session()

    # Create eval user
    user = User(
        email="evaluator@docuquery.local",
        hashed_password=hash_password("EvalSecretPass123!"),
        full_name="Eval Agent",
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Ingest evaluation documents
    llm = get_llm_adapter()
    doc_id_map: Dict[str, str] = {}

    for filename, pages_content in EVAL_DOCUMENTS.items():
        pdf_bytes = create_in_memory_pdf(pages_content)
        pages = extract_pages_from_pdf(pdf_bytes)
        chunks = create_chunks_from_pages(pages)

        import hashlib
        checksum = hashlib.sha256(pdf_bytes).hexdigest()

        doc = Document(
            user_id=user.id,
            filename=filename,
            storage_key=f"eval/{user.id}/{filename}",
            file_size=len(pdf_bytes),
            page_count=len(pages),
            checksum=checksum,
            status="ready",
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)
        doc_id_map[filename] = doc.id

        chunk_texts = [c.content for c in chunks]
        embeddings = llm.get_embeddings(chunk_texts)

        for item, emb in zip(chunks, embeddings):
            c_rec = DocumentChunk(
                document_id=doc.id,
                user_id=user.id,
                page_number=item.page_number,
                chunk_index=item.chunk_index,
                content=item.content,
                token_count=item.token_count,
                embedding=emb,
            )
            db.add(c_rec)
        db.commit()

    return db, user, doc_id_map


def run_benchmark(db, user, doc_id_map) -> Dict[str, Any]:
    llm = get_llm_adapter()
    results = []

    total_recall_at_1 = 0
    total_recall_at_3 = 0
    total_recall_at_5 = 0
    total_page_accuracy = 0
    total_abstention_correct = 0
    total_fact_correct = 0
    total_citation_valid = 0
    latencies = []

    answerable_count = sum(1 for q in EVAL_QUERIES if not q.should_abstain)
    abstain_count = sum(1 for q in EVAL_QUERIES if q.should_abstain)

    for query in EVAL_QUERIES:
        # Create dedicated conversation
        conv = Conversation(user_id=user.id, title=query.query_id)
        db.add(conv)
        db.commit()
        db.refresh(conv)

        start_t = time.perf_counter()

        # Step A: Measure Retrieval explicitly
        query_vector = llm.get_embeddings([query.question])[0]
        retrieved_chunks = search_relevant_chunks(
            db=db,
            user_id=user.id,
            query_vector=query_vector,
            query_text=query.question,
            top_k=5,
            similarity_threshold=0.10,  # wide threshold for retrieval eval
        )

        # Step B: Execute Full Pipeline
        rag_output = execute_rag_pipeline(
            db=db,
            user_id=user.id,
            conversation_id=conv.id,
            question=query.question,
        )
        elapsed_ms = (time.perf_counter() - start_t) * 1000.0
        latencies.append(elapsed_ms)

        asst_msg = rag_output["assistant_message"]
        answer_text = asst_msg["content"]
        citations = asst_msg["citations"] or []

        # Evaluate Retrieval Metrics
        retrieved_docs_pages = [(c["filename"], c["page_number"]) for c in retrieved_chunks]

        if not query.should_abstain:
            # Check target doc and page presence
            hit_k1 = False
            hit_k3 = False
            hit_k5 = False

            target_pairs = [(doc, page) for doc in query.target_docs for page in query.target_pages]

            for rank, item in enumerate(retrieved_docs_pages[:5]):
                if item in target_pairs:
                    if rank == 0:
                        hit_k1 = True
                    if rank < 3:
                        hit_k3 = True
                    hit_k5 = True

            if hit_k1:
                total_recall_at_1 += 1
            if hit_k3:
                total_recall_at_3 += 1
            if hit_k5:
                total_recall_at_5 += 1
            if hit_k5:
                total_page_accuracy += 1

            # Evaluate Answer Correctness
            facts_present = all(fact.lower() in answer_text.lower() for fact in query.expected_facts)
            if facts_present:
                total_fact_correct += 1

            # Evaluate Citation Validity
            cites_valid = False
            if citations:
                all_valid = True
                for cite in citations:
                    # Check citation belongs to real DB chunk
                    db_chunk = db.query(DocumentChunk).filter(DocumentChunk.id == cite.chunk_id).first()
                    if not db_chunk or db_chunk.page_number != cite.page_number:
                        all_valid = False
                cites_valid = all_valid
            if cites_valid:
                total_citation_valid += 1
        else:
            # Must abstain
            abstained = "I couldn't find enough information in your selected documents" in answer_text
            if abstained and len(citations) == 0:
                total_abstention_correct += 1

        results.append({
            "query_id": query.query_id,
            "type": query.query_type,
            "latency_ms": elapsed_ms,
            "answer_preview": answer_text[:80].replace("\n", " "),
            "full_answer": answer_text,
            "citation_count": len(citations),
        })

    metrics = {
        "recall_at_1": (total_recall_at_1 / answerable_count) * 100.0,
        "recall_at_3": (total_recall_at_3 / answerable_count) * 100.0,
        "recall_at_5": (total_recall_at_5 / answerable_count) * 100.0,
        "page_retrieval_acc": (total_page_accuracy / answerable_count) * 100.0,
        "abstention_accuracy": (total_abstention_correct / abstain_count) * 100.0,
        "fact_correctness": (total_fact_correct / answerable_count) * 100.0,
        "citation_validity": (total_citation_valid / answerable_count) * 100.0,
        "avg_latency_ms": sum(latencies) / len(latencies),
        "query_results": results,
    }
    return metrics


if __name__ == "__main__":
    db, user, doc_id_map = setup_eval_db()
    metrics = run_benchmark(db, user, doc_id_map)
    print("\n================== RAG BENCHMARK RESULTS ==================")
    print(f"Recall@1:             {metrics['recall_at_1']:.1f}%")
    print(f"Recall@3:             {metrics['recall_at_3']:.1f}%")
    print(f"Recall@5:             {metrics['recall_at_5']:.1f}%")
    print(f"Page Retrieval Acc:   {metrics['page_retrieval_acc']:.1f}%")
    print(f"Abstention Accuracy:  {metrics['abstention_accuracy']:.1f}%")
    print(f"Fact Correctness:     {metrics['fact_correctness']:.1f}%")
    print(f"Citation Validity:    {metrics['citation_validity']:.1f}%")
    print(f"Avg Latency:          {metrics['avg_latency_ms']:.2f} ms")
    print("===========================================================\n")
    print("Query-by-query Breakdown:")
    for qr in metrics["query_results"]:
        print(f"\n--- [{qr['query_id']}] ({qr['type']}) | Citations: {qr['citation_count']} ---")
        print(f"Answer: {qr['full_answer']}")
