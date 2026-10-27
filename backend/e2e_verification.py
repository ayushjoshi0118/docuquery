import os
import sys
import json
import pymupdf
import httpx
import psycopg2

BASE_URL = "http://127.0.0.1:8000/api/v1"
DB_CONN = "postgresql://docuquery:docuquery_secret@localhost:5432/docuquery"

def create_sample_pdf() -> bytes:
    doc = pymupdf.open()
    
    # Page 1
    p1 = doc.new_page()
    rect1 = pymupdf.Rect(50, 50, 550, 750)
    p1.insert_textbox(rect1, "DocuQuery Production Architecture.\nDocuQuery employs FastAPI, PostgreSQL, and PyMuPDF.\nThe project lead is Senior Engineer Cassandra Thorne.\nAll API endpoints are versioned under v1.", fontsize=11)
    
    # Page 2
    p2 = doc.new_page()
    rect2 = pymupdf.Rect(50, 50, 550, 750)
    p2.insert_textbox(rect2, "Security Policies and Operations.\nAll customer data must be encrypted with AES-256-GCM.\nThe annual compliance audit is scheduled for November 2026.\nAccess control is strictly enforced at database layer.", fontsize=11)
    
    data = doc.write()
    doc.close()
    return data

def main():
    print("=== Step 1: Connecting to Live FastAPI and PostgreSQL ===")
    conn = psycopg2.connect(DB_CONN)
    cur = conn.cursor()
    cur.execute("SELECT version();")
    print(f"PostgreSQL Version: {cur.fetchone()[0]}")

    with httpx.Client(base_url=BASE_URL, timeout=30.0) as client:
        # 1. Health check
        h = client.get("/health/live").json()
        r = client.get("/health/ready").json()
        print(f"Liveness: {h}, Readiness: {r}")
        assert h["status"] == "ok"
        assert r["status"] == "ready"

        # 2. Register & Login User A
        email_a = "alice_qa@docuquery.com"
        pwd = "ProductionPassword123!"
        print(f"\n=== Step 2: Register & Login ({email_a}) ===")
        # Register (or login if exists)
        reg_resp = client.post("/auth/register", json={"email": email_a, "password": pwd, "full_name": "Alice QA"})
        if reg_resp.status_code == 201:
            print("Alice registered successfully.")
        else:
            print("Alice already registered.")

        login_resp = client.post("/auth/login", json={"email": email_a, "password": pwd})
        assert login_resp.status_code == 200
        tokens_a = login_resp.json()
        headers_a = {"Authorization": f"Bearer {tokens_a['access_token']}"}
        print("Alice authenticated with JWT bearer token.")

        # Clean up any existing documents from previous test runs
        existing_docs = client.get("/documents", headers=headers_a).json()["items"]
        for ed in existing_docs:
            client.delete(f"/documents/{ed['id']}", headers=headers_a)
        print("Cleaned up existing documents for test isolation.")

        # 3. Upload PDF
        print("\n=== Step 3: Upload Real Multi-Page PDF Document ===")
        pdf_bytes = create_sample_pdf()
        files = {"file": ("docuquery_architecture.pdf", pdf_bytes, "application/pdf")}
        upload_resp = client.post("/documents/upload", files=files, headers=headers_a)
        assert upload_resp.status_code == 201
        doc_data = upload_resp.json()
        doc_id = doc_data["id"]
        print(f"Document uploaded: id={doc_id}, status={doc_data['status']}")

        # 4. Verify storage and database records
        print("\n=== Step 4: Verify Object Storage & PostgreSQL Records ===")
        # Query PostgreSQL for internal storage key
        cur.execute("SELECT id, filename, status, page_count, storage_key FROM documents WHERE id = %s", (doc_id,))
        db_doc = cur.fetchone()
        assert db_doc is not None
        storage_key = db_doc[4]
        print(f"PostgreSQL Document Row: id={db_doc[0]}, filename={db_doc[1]}, status={db_doc[2]}, page_count={db_doc[3]}, storage_key={storage_key}")
        assert db_doc[2] == "ready"
        assert db_doc[3] == 2

        # Check storage file on disk
        local_path = os.path.abspath(os.path.join("data", "storage", storage_key.replace("/", os.sep)))
        print(f"Checking disk storage path: {local_path}")
        assert os.path.exists(local_path), f"File missing on disk: {local_path}"
        assert os.path.getsize(local_path) == len(pdf_bytes)
        print("Private storage file verified on disk.")

        # Check chunks in PostgreSQL
        cur.execute("SELECT id, page_number, chunk_index, length(content) FROM document_chunks WHERE document_id = %s ORDER BY chunk_index", (doc_id,))
        chunks = cur.fetchall()
        print(f"PostgreSQL Chunks Count: {len(chunks)}")
        for ch in chunks:
            print(f"  Chunk {ch[2]}: page={ch[1]}, content_len={ch[3]}")
        assert len(chunks) >= 2

        # 5. Create Conversation and Query Answer
        print("\n=== Step 5: Ask Grounded Questions with Citations ===")
        conv = client.post("/conversations", json={"title": "Architecture Q&A"}, headers=headers_a).json()
        conv_id = conv["id"]

        # Question 1: Who is the project lead?
        q1 = "Who is the project lead for DocuQuery?"
        print(f"User Query: '{q1}'")
        chat_resp1 = client.post(f"/chat/conversations/{conv_id}/messages", json={"question": q1}, headers=headers_a)
        assert chat_resp1.status_code == 200
        msg1 = chat_resp1.json()["assistant_message"]
        print(f"Assistant Response:\n{msg1['content']}\n")
        assert "Cassandra Thorne" in msg1["content"], "Expected Cassandra Thorne in grounded answer"
        assert msg1["citations"] is not None and len(msg1["citations"]) >= 1
        cit1 = msg1["citations"][0]
        print(f"Citation 1: doc={cit1['filename']}, page={cit1['page_number']}, excerpt='{cit1['excerpt']}'")
        assert cit1["page_number"] == 1
        assert cit1["document_id"] == doc_id

        # Question 2: When is the compliance audit?
        q2 = "When is the annual compliance audit scheduled?"
        print(f"\nUser Query: '{q2}'")
        chat_resp2 = client.post(f"/chat/conversations/{conv_id}/messages", json={"question": q2}, headers=headers_a)
        assert chat_resp2.status_code == 200
        msg2 = chat_resp2.json()["assistant_message"]
        print(f"Assistant Response:\n{msg2['content']}\n")
        assert "November 2026" in msg2["content"]
        cit2 = msg2["citations"][0]
        print(f"Citation 2: doc={cit2['filename']}, page={cit2['page_number']}, excerpt='{cit2['excerpt']}'")
        assert cit2["page_number"] == 2

        # Question 3: Abstention check on unsupported question
        q3 = "What is the recipe for chocolate lava cake?"
        print(f"\nUser Query (Out of scope): '{q3}'")
        chat_resp3 = client.post(f"/chat/conversations/{conv_id}/messages", json={"question": q3}, headers=headers_a)
        assert chat_resp3.status_code == 200
        msg3 = chat_resp3.json()["assistant_message"]
        print(f"Assistant Response:\n{msg3['content']}\n")
        assert "couldn't find enough information in your selected documents" in msg3["content"]
        assert msg3["citations"] is None or len(msg3["citations"]) == 0
        print("Abstention policy verified successfully.")

        # 6. Persistence check
        print("\n=== Step 6: Verify Conversation & Message Persistence ===")
        hist = client.get(f"/conversations/{conv_id}", headers=headers_a).json()
        print(f"Fetched conversation history from server: {len(hist['messages'])} messages stored.")
        assert len(hist["messages"]) == 6  # 3 user + 3 assistant

        # 7. Cross-user isolation check
        print("\n=== Step 7: Cross-User Access Isolation ===")
        email_b = "bob_qa@docuquery.com"
        client.post("/auth/register", json={"email": email_b, "password": pwd, "full_name": "Bob QA"})
        login_b = client.post("/auth/login", json={"email": email_b, "password": pwd}).json()
        headers_b = {"Authorization": f"Bearer {login_b['access_token']}"}

        # Bob attempts to get Alice's document
        bad_doc = client.get(f"/documents/{doc_id}", headers=headers_b)
        assert bad_doc.status_code == 404
        print("Bob cannot access Alice's document metadata (404 Not Found).")

        # Bob attempts to query Alice's conversation
        bad_conv = client.get(f"/conversations/{conv_id}", headers=headers_b)
        assert bad_conv.status_code == 404
        print("Bob cannot access Alice's conversation history (404 Not Found).")

        # 8. Document Deletion & Cascade Verification
        print("\n=== Step 8: Document Deletion & Cascading Cleanup ===")
        del_resp = client.delete(f"/documents/{doc_id}", headers=headers_a)
        assert del_resp.status_code == 204
        print("DELETE /documents endpoint returned 204 No Content.")

        # Verify storage file deleted
        assert not os.path.exists(local_path), "File still exists on disk after deletion!"
        print("Storage file deleted from disk.")

        # Verify document row deleted from PostgreSQL
        cur.execute("SELECT count(*) FROM documents WHERE id = %s", (doc_id,))
        assert cur.fetchone()[0] == 0
        print("PostgreSQL document record deleted.")

        # Verify chunks cascaded in PostgreSQL
        cur.execute("SELECT count(*) FROM document_chunks WHERE document_id = %s", (doc_id,))
        assert cur.fetchone()[0] == 0
        print("PostgreSQL document chunks deleted via cascade.")

    cur.close()
    conn.close()
    print("\n>>> ALL CRITICAL REAL-SYSTEM USER JOURNEYS PASSED SUCCESSFULLY! <<<")

if __name__ == "__main__":
    main()
