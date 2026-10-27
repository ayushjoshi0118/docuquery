# DocuQuery — Production-Grade AI Document Intelligence Platform

[![CI Pipeline](https://github.com/docuquery/docuquery/actions/workflows/ci.yml/badge.svg)](https://github.com/docuquery/docuquery/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-emerald.svg)](LICENSE)
[![Python: 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-teal.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18.3-61dafb.svg)](https://react.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.7-blue.svg)](https://www.typescriptlang.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16%20%7C%20pgvector-336791.svg)](https://github.com/pgvector/pgvector)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS-3.4-38bdf8.svg)](https://tailwindcss.com/)

**DocuQuery** is a private, multi-tenant AI document intelligence and Retrieval-Augmented Generation (RAG) platform. Users upload PDF documents, await asynchronous vector indexing via Celery and Redis, and ask complex natural-language questions. The system retrieves relevant passages via hybrid BM25 + dense vector search, reranks candidates, and synthesizes answers strictly grounded in the uploaded documents—returning interactive citations that deep-link directly to the exact PDF page and excerpt.

---

## 🚀 Key Features

- **Multi-Tenant Isolation**: Zero cross-user data exposure. Enforced at the SQL query layer (`WHERE user_id = :current_user_id`) across documents, chunks, conversations, and object storage.
- **Hybrid Dense & Lexical Retrieval**: Linear reciprocal fusion combining dense vector embeddings (cosine distance) with BM25 Inverse Document Frequency (IDF) scoring to capture both semantic concepts and exact keywords/dates/numbers.
- **Multi-Feature Candidate Reranker**: Cross-evaluates top-15 retrieved passages with exact numeric/chronological matching, negation alignment, and stem-aware keyword scoring.
- **Strict Evidence Grounding & Abstention**: Context passages are isolated in `<document_evidence>` XML tags. If substantive query coverage is below threshold (< 40%), the assistant abstains explicitly (*"I couldn't find enough information in your selected documents to answer that question."*) rather than hallucinating.
- **Claim-Level Verifiable Citations**: Cites only the specific chunks whose facts were utilized in the synthesized answer. Clicking a citation opens the PDF viewer directly at `#page={page}`.
- **Structure-Aware PDF Ingestion**: PyMuPDF extraction unwraps soft line breaks, removes running headers/footers, preserves section titles, avoids premature sentence splits on abbreviations (`Dr.`, `Inc.`), and detects scanned/image-only PDFs.
- **Asynchronous Task Architecture**: Celery with Redis broker handles background document extraction, chunking, and batched embeddings with idempotent insertion and retry mechanisms.
- **Security-First Architecture**: Bcrypt password hashing, access and refresh token rotation, in-memory/Redis token revocation on logout, client IP rate limiting, and 25MB streaming upload protection.

---

## 📊 Empirical RAG Benchmark Results

Benchmarked against a version-controlled evaluation dataset ([`backend/tests/eval_dataset.py`](backend/tests/eval_dataset.py)) containing multi-passage questions, conflicting chronological policies, fine-grained negations, unanswerable queries, and adversarial prompt injections:

| Metric | Baseline System | Upgraded RAG System | Status |
| :--- | :--- | :--- | :--- |
| **Recall@1** | 33.3% | **66.7%** | 🟢 +33.4% |
| **Recall@3** | 66.7% | **100.0%** | 🟢 +33.3% |
| **Recall@5** | 83.3% | **100.0%** | 🟢 +16.7% |
| **Page Retrieval Accuracy** | 83.3% | **100.0%** | 🟢 +16.7% |
| **Fact Correctness** | 16.7% | **100.0%** | 🟢 +83.3% |
| **Citation Validity** | 100.0% | **100.0%** | 🟢 Verified Claim-Level |
| **Abstention Accuracy** | 100.0% | **100.0%** | 🟢 0 Hallucinations |
| **Average Query Latency** | 12.10 ms | **16.75 ms** | 🟢 Sub-20ms Interactive |

---

## 🏗️ System Architecture

```
                          ┌───────────────────────────┐
                          │   React + Vite Frontend   │
                          │   (Tailwind CSS, Lucide)  │
                          └─────────────┬─────────────┘
                                        │ HTTP / REST
                                        ▼
                          ┌───────────────────────────┐
                          │    FastAPI API Server     │
                          │  (Auth, Pydantic, Routes) │
                          └──────┬──────┬──────┬──────┘
                                 │      │      │
            ┌────────────────────┘      │      └────────────────────┐
            │                           │                           │
            ▼                           ▼                           ▼
┌───────────────────────┐   ┌───────────────────────┐   ┌───────────────────────┐
│ PostgreSQL + pgvector │   │     Redis Queue       │   │  MinIO Object Storage │
│ (Users, Docs, Chunks) │   │   (Celery Broker)     │   │     (Raw PDF Files)   │
└───────────────────────┘   └───────────┬───────────┘   └───────────────────────┘
                                        │
                                        ▼
                            ┌───────────────────────┐
                            │     Celery Worker     │
                            │  (PyMuPDF, Chunking,  │
                            │   LLM Embedding Batch)│
                            └───────────────────────┘
```

---

## 🛠️ Technology Stack

| Layer | Technologies |
| :--- | :--- |
| **Backend API** | Python 3.11+, FastAPI, Pydantic v2, SQLAlchemy 2.x, Uvicorn |
| **Database & Vector Index** | PostgreSQL 16+ with `pgvector` (HNSW cosine distance index) |
| **Migrations** | Alembic |
| **PDF Processing** | PyMuPDF (`pymupdf`), preserving exact 1-based page numbers |
| **Worker & Queue** | Celery 5.4, Redis 7 |
| **Object Storage** | MinIO (S3-compatible) or Local Filesystem abstraction |
| **Security & Auth** | Bcrypt password hashing, JWT access/refresh token rotation, IP rate-limiting |
| **Frontend** | React 18, TypeScript 5.7, Vite 6, Tailwind CSS, Lucide React |
| **Testing** | `pytest`, `httpx` (backend), `vitest`, `@testing-library/react` (frontend) |
| **Deployment** | Docker Compose (7 container services with healthchecks) |

---

## 📂 Repository Structure

```
AIDoc/
├── docker-compose.yml             # Complete 7-service container stack
├── .env.example                   # Environment variable template
├── .gitignore                     # Production-safe gitignore
├── LICENSE                        # MIT License
├── README.md                      # Architecture and operational manual
├── .github/
│   ├── workflows/ci.yml           # Automated GitHub Actions CI workflow
│   └── ISSUE_TEMPLATE/            # Bug report & feature request templates
├── backend/
│   ├── Dockerfile                 # Python 3.11-slim container
│   ├── requirements.txt           # Pinned backend dependencies
│   ├── alembic.ini                # Alembic migration configuration
│   ├── alembic/                   # Database version migration scripts
│   ├── e2e_verification.py        # Automated live end-to-end acceptance script
│   ├── docuquery/
│   │   ├── main.py                # FastAPI entrypoint & middleware
│   │   ├── config.py              # Pydantic BaseSettings & production validator
│   │   ├── database.py            # SQLAlchemy engine & session factory
│   │   ├── models/                # User, Document, Chunk, Conversation, Message
│   │   ├── schemas/               # Typed Pydantic schemas
│   │   ├── api/v1/                # Versioned REST endpoints (auth, docs, chat)
│   │   ├── services/              # Storage, PDF, Chunking, LLM, RAG
│   │   └── worker/                # Celery app & document indexing tasks
│   └── tests/                     # 50 comprehensive unit, security & eval tests
└── frontend/
    ├── Dockerfile                 # Multi-stage Node build + Nginx Alpine
    ├── nginx.conf                 # Production reverse-proxy & SPA routing
    ├── package.json               # Dependencies and scripts
    ├── vite.config.ts             # Vite configuration
    └── src/
        ├── api/client.ts          # Typed REST API client & token refresher
        ├── context/AuthContext.tsx# Reactive authentication state
        ├── components/            # PdfViewerModal, CitationCard, ChatMessage
        ├── pages/                 # Dashboard, Documents, Chat, Settings, Auth
        └── test/                  # Vitest component and interaction tests
```

---

## ⚡ Quickstart

### Method 1: Docker Compose (Recommended)

To run the complete production stack (PostgreSQL + pgvector, Redis, MinIO, API, Celery Worker, and Frontend):

```bash
# 1. Clone repository
git clone https://github.com/your-username/docuquery.git
cd docuquery

# 2. Copy environment template
cp .env.example .env

# 3. Launch all services
docker compose up -d --build

# 4. Verify running health status
docker compose ps
```

Once running:
- **Frontend App**: [http://localhost:3000](http://localhost:3000)
- **Interactive Swagger Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **MinIO Storage Console**: [http://localhost:9001](http://localhost:9001) (`minioadmin` / `minioadmin`)

---

### Method 2: Local Development (Without Docker)

#### 1. Backend Setup
```bash
# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r backend/requirements.txt

# Run database migrations
cd backend
alembic upgrade head

# Start FastAPI server
export PYTHONPATH="backend"  # On Windows PowerShell: $env:PYTHONPATH="backend"
uvicorn docuquery.main:app --reload --host 127.0.0.1 --port 8000
```

#### 2. Celery Worker (Optional if `CELERY_TASK_ALWAYS_EAGER=False`)
```bash
export PYTHONPATH="backend"
celery -A docuquery.worker.celery_app worker -l info -c 2
```

#### 3. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```
Open [http://localhost:5173](http://localhost:5173) in your browser.

---

## 🤖 Configuring LLM Providers

DocuQuery supports multiple interchangeable LLM & Embedding providers via [`backend/docuquery/services/llm_adapter.py`](backend/docuquery/services/llm_adapter.py). Configure via `.env`:

### 1. Mock / Offline Mode (Default, Zero API Keys Required)
```env
EMBEDDING_PROVIDER=mock
LLM_PROVIDER=mock
EMBEDDING_DIM=1536
```
*(Uses deterministic semantic feature projections—ideal for local development, CI/CD, and offline verification).*

### 2. Google Gemini
```env
EMBEDDING_PROVIDER=gemini
LLM_PROVIDER=gemini
GEMINI_API_KEY=your_gemini_api_key
EMBEDDING_MODEL=models/text-embedding-004
LLM_MODEL=gemini-1.5-flash
EMBEDDING_DIM=768
```

### 3. OpenAI
```env
EMBEDDING_PROVIDER=openai
LLM_PROVIDER=openai
OPENAI_API_KEY=your_openai_api_key
EMBEDDING_MODEL=text-embedding-3-small
LLM_MODEL=gpt-4o-mini
EMBEDDING_DIM=1536
```

### 4. Local Ollama (Completely Self-Hosted & Private)
```env
EMBEDDING_PROVIDER=ollama
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
EMBEDDING_MODEL=nomic-embed-text
LLM_MODEL=llama3
```

---

## 🧪 Testing & Verification

### Run Backend Tests (50 Tests)
```bash
cd backend
python -m pytest tests -v
```

### Run RAG Benchmark Suite
```bash
export PYTHONPATH="backend"
python backend/tests/run_rag_eval.py
```

### Run Frontend Tests & Build
```bash
cd frontend
npm test
npm run build
```

### Run Live End-to-End User Journey Verification
```bash
python backend/e2e_verification.py
```

---

## 🛡️ Security & Privacy Disclosures

- **Multi-Tenant Protection**: No user can access or infer another user's documents, conversations, or embeddings.
- **Path Traversal Defenses**: S3 keys and local paths are generated as strict server-side UUIDs (`documents/{user_id}/{doc_id}.pdf`), rejecting null-byte or directory-traversal injections.
- **Prompt Injection Neutralization**: Retrieved passages are delimited as untrusted reference data within `<document_evidence>` XML boundaries with explicit system prompt guards.
- **Resource Limits**: Configurable upload size limits (25 MB default) and per-user storage quotas (100 MB default) protect against denial-of-service and disk exhaustion.

---

## 📄 License

This project is licensed under the terms of the [MIT License](LICENSE).
