import json
import math
import re
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text
from docuquery.models.document import Document
from docuquery.models.chunk import DocumentChunk
from docuquery.models.conversation import Conversation
from docuquery.models.message import Message
from docuquery.schemas.chat import Citation
from docuquery.services.llm_adapter import get_llm_adapter
from docuquery.config import settings


def _cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    if not vec1 or not vec2 or len(vec1) != len(vec2):
        return 0.0
    dot = sum(a * b for a, b in zip(vec1, vec2))
    norm1 = math.sqrt(sum(a * a for a in vec1))
    norm2 = math.sqrt(sum(b * b for b in vec2))
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return dot / (norm1 * norm2)


STOP_WORDS = {
    "what", "is", "the", "a", "an", "in", "of", "and", "or", "for", "to",
    "how", "why", "where", "can", "you", "tell", "me", "about", "are",
    "under", "does", "do", "when", "her", "she", "he", "his", "their",
    "was", "were", "who", "which", "with", "at", "by", "from", "on", "as",
}


def _compute_bm25_score(
    query_tokens: List[str],
    chunk_text: str,
    df_counts: Optional[Dict[str, int]] = None,
    total_docs: int = 10,
    avg_len: float = 80.0,
    k1: float = 1.5,
    b: float = 0.75,
) -> float:
    """
    Computes BM25 lexical term score for a chunk with exact-token, number, and IDF weighting,
    filtering noise words to prevent false-positive matches on common function words.
    """
    substantive_query = [q for q in query_tokens if q not in STOP_WORDS]
    if not substantive_query:
        substantive_query = query_tokens

    chunk_tokens = re.findall(r"\w+", chunk_text.lower())
    if not chunk_tokens:
        return 0.0
    doc_len = len(chunk_tokens)
    token_counts: Dict[str, int] = {}
    for t in chunk_tokens:
        token_counts[t] = token_counts.get(t, 0) + 1

    score = 0.0
    for q in substantive_query:
        if q in token_counts:
            tf = token_counts[q]
            term_score = (tf * (k1 + 1)) / (tf + k1 * (1 - b + b * (doc_len / avg_len)))
            # Standard BM25 Inverse Document Frequency (IDF)
            if df_counts and q in df_counts:
                df = df_counts[q]
                idf = math.log(1.0 + (total_docs - df + 0.5) / (df + 0.5))
            else:
                idf = 1.0

            weighted_term = term_score * max(0.2, idf)
            # Boost specific numbers, dates (e.g. 2024, 2026), or specialized terms
            if any(char.isdigit() for char in q):
                weighted_term *= 2.0
            score += weighted_term
    return score


def _stem_match(q_words: set, s_words: set) -> set:
    matched = set()
    for qw in q_words:
        for sw in s_words:
            if qw == sw:
                matched.add(qw)
                break
            min_len = min(len(qw), len(sw))
            if min_len >= 4:
                prefix = min(min_len, 5)
                if qw[:prefix] == sw[:prefix]:
                    matched.add(qw)
                    break
    return matched


def _rerank_candidates(query: str, candidates: List[Dict[str, Any]], top_k: int) -> List[Dict[str, Any]]:
    """
    Semantic reranker: assesses query-passage interaction, exact entity/number matching,
    stem-aware keyword alignment, and negation consistency across top retrieval candidates.
    """
    query_lower = query.lower()
    query_words = set(re.findall(r"\w+", query_lower))
    stop_words = STOP_WORDS
    meaningful_words = query_words - stop_words
    query_numbers = set(re.findall(r"\b\d+\b", query))
    is_negation_query = any(w in query_words for w in ("not", "never", "no", "neither", "without"))

    reranked = []
    for cand in candidates:
        content = cand["content"]
        content_lower = content.lower()
        score = cand["score"]

        # 1. Exact year / number alignment (e.g., distinguishing 2024 vs 2026)
        if query_numbers:
            content_numbers = set(re.findall(r"\b\d+\b", content))
            matching_numbers = query_numbers.intersection(content_numbers)
            if matching_numbers:
                score += 0.45 * len(matching_numbers)
            else:
                score -= 0.25

        # 2. Meaningful keyword overlap ratio with stem matching
        content_words = set(re.findall(r"\w+", content_lower))
        overlap = _stem_match(meaningful_words, content_words)
        if meaningful_words:
            overlap_ratio = len(overlap) / len(meaningful_words)
            score += 0.60 * overlap_ratio

        # 3. Negation phrase alignment
        if is_negation_query and any(n in content_lower for n in ("not", "no", "never", "without")):
            score += 0.30

        cand_copy = dict(cand)
        cand_copy["score"] = score
        reranked.append(cand_copy)

    reranked.sort(key=lambda x: x["score"], reverse=True)
    return reranked[:top_k]


def search_relevant_chunks(
    db: Session,
    user_id: str,
    query_vector: List[float],
    query_text: Optional[str] = None,
    selected_document_ids: Optional[List[str]] = None,
    top_k: int = settings.RAG_TOP_K,
    similarity_threshold: float = settings.RAG_SIMILARITY_THRESHOLD,
) -> List[Dict[str, Any]]:
    """
    Search relevant document chunks combining dense vector search and BM25 lexical search,
    followed by semantic reranking. Strictly enforces user ownership and ready document status.
    """
    bind = db.get_bind()
    is_postgres = bind.dialect.name == "postgresql"

    has_pgvector = False
    if is_postgres:
        try:
            res = db.execute(text("SELECT 1 FROM pg_extension WHERE extname = 'vector'")).scalar()
            has_pgvector = bool(res)
        except Exception:
            has_pgvector = False

    query_tokens = re.findall(r"\w+", query_text.lower()) if query_text else []

    if is_postgres and has_pgvector:
        score_expr = 1 - DocumentChunk.embedding.cosine_distance(query_vector)
        stmt = (
            db.query(DocumentChunk, Document.filename, score_expr.label("score"))
            .join(Document, DocumentChunk.document_id == Document.id)
            .filter(
                Document.user_id == user_id,
                DocumentChunk.user_id == user_id,
                Document.status == "ready",
            )
        )
        if selected_document_ids:
            stmt = stmt.filter(Document.id.in_(selected_document_ids))
        stmt = stmt.order_by(score_expr.desc()).limit(settings.RAG_RERANK_CANDIDATES_K)
        rows = stmt.all()

        df_counts = {}
        if settings.RAG_HYBRID_RETRIEVAL and query_tokens:
            for chunk, filename, _ in rows:
                cw = set(re.findall(r"\w+", chunk.content.lower()))
                for q in query_tokens:
                    if q in cw:
                        df_counts[q] = df_counts.get(q, 0) + 1

        candidates = []
        for chunk, filename, vec_score in rows:
            v_score = max(0.0, float(vec_score))
            if settings.RAG_HYBRID_RETRIEVAL and query_tokens:
                bm25 = _compute_bm25_score(query_tokens, chunk.content, df_counts=df_counts, total_docs=len(rows))
                norm_bm25 = min(1.0, bm25 / 10.0)
                combined = (1 - settings.RAG_HYBRID_ALPHA) * v_score + settings.RAG_HYBRID_ALPHA * norm_bm25
            else:
                combined = v_score

            candidates.append({
                "chunk_id": chunk.id,
                "document_id": chunk.document_id,
                "filename": filename,
                "page_number": chunk.page_number,
                "content": chunk.content,
                "score": combined,
            })
    else:
        stmt = (
            db.query(DocumentChunk, Document.filename)
            .join(Document, DocumentChunk.document_id == Document.id)
            .filter(
                Document.user_id == user_id,
                DocumentChunk.user_id == user_id,
                Document.status == "ready",
            )
        )
        if selected_document_ids:
            stmt = stmt.filter(Document.id.in_(selected_document_ids))
        rows = stmt.all()

        scored = []
        max_bm25 = 1.0
        bm25_map = {}
        if settings.RAG_HYBRID_RETRIEVAL and query_tokens:
            df_counts = {}
            for chunk, filename in rows:
                cw = set(re.findall(r"\w+", chunk.content.lower()))
                for q in query_tokens:
                    if q in cw:
                        df_counts[q] = df_counts.get(q, 0) + 1

            for chunk, filename in rows:
                bm = _compute_bm25_score(query_tokens, chunk.content, df_counts=df_counts, total_docs=len(rows))
                bm25_map[chunk.id] = bm
                if bm > max_bm25:
                    max_bm25 = bm

        for chunk, filename in rows:
            emb = chunk.embedding
            if isinstance(emb, str):
                try:
                    emb = json.loads(emb)
                except Exception:
                    emb = []
            elif hasattr(emb, "tolist"):
                emb = emb.tolist()

            sim = max(0.0, _cosine_similarity(query_vector, emb))
            if settings.RAG_HYBRID_RETRIEVAL and query_tokens:
                norm_bm25 = bm25_map.get(chunk.id, 0.0) / max_bm25
                combined_score = (1 - settings.RAG_HYBRID_ALPHA) * sim + settings.RAG_HYBRID_ALPHA * norm_bm25
            else:
                combined_score = sim

            scored.append((combined_score, chunk, filename))

        scored.sort(key=lambda x: x[0], reverse=True)
        candidates = []
        for combined, chunk, filename in scored[: settings.RAG_RERANK_CANDIDATES_K]:
            candidates.append({
                "chunk_id": chunk.id,
                "document_id": chunk.document_id,
                "filename": filename,
                "page_number": chunk.page_number,
                "content": chunk.content,
                "score": float(combined),
            })

    # Apply semantic reranker
    if settings.RAG_RERANKING_ENABLED and query_text and candidates:
        ranked = _rerank_candidates(query_text, candidates, top_k)
    else:
        ranked = candidates[:top_k]

    # Filter by similarity threshold
    filtered_passages = [p for p in ranked if p["score"] >= similarity_threshold]
    return filtered_passages


def execute_rag_pipeline(
    db: Session,
    user_id: str,
    conversation_id: str,
    question: str,
    selected_document_ids: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Execute complete RAG flow with hybrid retrieval, reranking, and explicit abstention:
    1. Verify conversation ownership.
    2. Embed question.
    3. Retrieve relevant chunks with hybrid scoring and ownership isolation.
    4. Enforce abstention threshold.
    5. Generate grounded answer.
    6. Build citations linked strictly to retrieved chunks.
    7. Persist user and assistant messages in database.
    """
    # 1. Verify conversation ownership
    conversation = (
        db.query(Conversation)
        .filter(Conversation.id == conversation_id, Conversation.user_id == user_id)
        .first()
    )
    if not conversation:
        raise ValueError("Conversation not found or access denied")

    # If selected_document_ids provided, deduplicate and ensure they belong to user and are ready
    if selected_document_ids:
        selected_document_ids = list(dict.fromkeys(selected_document_ids))
        user_docs_count = (
            db.query(Document)
            .filter(
                Document.id.in_(selected_document_ids),
                Document.user_id == user_id,
                Document.status == "ready",
            )
            .count()
        )
        if user_docs_count != len(selected_document_ids):
            raise ValueError("One or more selected documents are invalid, not ready, or access denied")

    llm = get_llm_adapter()

    # 2. Generate embedding for query
    query_embeddings = llm.get_embeddings([question])
    query_vector = query_embeddings[0]

    # 3. Retrieve relevant chunks using hybrid retrieval + reranker
    retrieved_chunks = search_relevant_chunks(
        db=db,
        user_id=user_id,
        query_vector=query_vector,
        query_text=question,
        selected_document_ids=selected_document_ids,
        top_k=settings.RAG_TOP_K,
        similarity_threshold=settings.RAG_SIMILARITY_THRESHOLD,
    )

    # 4. Check explicit abstention policy:
    # Requires both relevance score threshold and substantive query term coverage in retrieved evidence
    query_substantive = [w for w in re.findall(r"\w+", question.lower()) if w not in STOP_WORDS]
    if query_substantive and retrieved_chunks:
        all_chunk_text = " ".join(c["content"].lower() for c in retrieved_chunks)
        chunk_words = set(re.findall(r"\w+", all_chunk_text))

        def _term_in_chunk(q_term: str) -> bool:
            if q_term in chunk_words:
                return True
            q_stem = q_term.rstrip("s").rstrip("ed").rstrip("ing")
            if len(q_stem) >= 3:
                return any(cw.startswith(q_stem) or q_stem in cw for cw in chunk_words)
            return False

        matched_substantive = [w for w in query_substantive if _term_in_chunk(w)]
        substantive_coverage = len(matched_substantive) / len(query_substantive)
    else:
        substantive_coverage = 0.0

    has_sufficient_evidence = bool(
        retrieved_chunks
        and max(c["score"] for c in retrieved_chunks) >= settings.RAG_ABSTENTION_THRESHOLD
        and substantive_coverage >= 0.40
    )

    if not has_sufficient_evidence:
        answer_text = "I couldn't find enough information in your selected documents to answer that question."
        citations: List[Citation] = []
    else:
        # 5. Generate grounded answer
        answer_text = llm.generate_answer(question, retrieved_chunks)

        is_insufficient = "I couldn't find enough information in your selected documents" in answer_text
        citations: List[Citation] = []

        if not is_insufficient and retrieved_chunks:
            # Create citation objects strictly referencing chunks whose evidence was actually used in the answer
            seen = set()
            for chunk in retrieved_chunks:
                # Verifiable claim check: verify if sentences or key facts from this chunk were used in the answer
                chunk_sentences = re.split(r"(?<=[.!?])\s+", chunk["content"])
                chunk_used = any(
                    s.strip() and s.strip() in answer_text
                    for s in chunk_sentences
                    if len(s.strip()) > 25
                )

                if chunk_used:
                    key = (chunk["document_id"], chunk["page_number"])
                    if key not in seen:
                        seen.add(key)
                        excerpt = chunk["content"].strip()
                        if len(excerpt) > 200:
                            excerpt = excerpt[:197] + "..."
                        citations.append(
                            Citation(
                                document_id=chunk["document_id"],
                                filename=chunk["filename"],
                                page_number=chunk["page_number"],
                                excerpt=excerpt,
                                chunk_id=chunk["chunk_id"],
                            )
                        )

            # Fallback for abstractive/summarized LLM answers: cite the top relevant chunk
            if not citations and retrieved_chunks:
                top_chunk = retrieved_chunks[0]
                excerpt = top_chunk["content"].strip()
                if len(excerpt) > 200:
                    excerpt = excerpt[:197] + "..."
                citations.append(
                    Citation(
                        document_id=top_chunk["document_id"],
                        filename=top_chunk["filename"],
                        page_number=top_chunk["page_number"],
                        excerpt=excerpt,
                        chunk_id=top_chunk["chunk_id"],
                    )
                )

    # 6. Persist user message and assistant message
    user_msg = Message(
        conversation_id=conversation.id,
        user_id=user_id,
        role="user",
        content=question,
    )
    db.add(user_msg)

    citations_json = json.dumps([c.model_dump() for c in citations]) if citations else None
    asst_msg = Message(
        conversation_id=conversation.id,
        user_id=user_id,
        role="assistant",
        content=answer_text,
        citations=citations_json,
    )
    db.add(asst_msg)

    if conversation.title == "New Conversation":
        short_title = question.strip()[:40]
        if len(question.strip()) > 40:
            short_title += "..."
        conversation.title = short_title

    db.commit()
    db.refresh(user_msg)
    db.refresh(asst_msg)

    return {
        "user_message": {
            "id": user_msg.id,
            "conversation_id": user_msg.conversation_id,
            "role": user_msg.role,
            "content": user_msg.content,
            "citations": None,
            "created_at": user_msg.created_at,
        },
        "assistant_message": {
            "id": asst_msg.id,
            "conversation_id": asst_msg.conversation_id,
            "role": asst_msg.role,
            "content": asst_msg.content,
            "citations": citations,
            "created_at": asst_msg.created_at,
        },
    }
