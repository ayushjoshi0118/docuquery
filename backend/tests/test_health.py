from fastapi import status


def test_liveness_probe(client):
    resp = client.get("/api/v1/health/live")
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json()["status"] == "ok"


def test_readiness_probe(client):
    resp = client.get("/api/v1/health/ready")
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert data["status"] == "ready"
    assert data["checks"]["database"] == "healthy"


def test_system_stats(client, auth_headers_user_a, create_pdf_bytes):
    # Upload 1 doc
    pdf = create_pdf_bytes(["Sample stats text."])
    client.post("/api/v1/documents/upload", files={"file": ("stats.pdf", pdf, "application/pdf")}, headers=auth_headers_user_a)

    resp = client.get("/api/v1/system/stats", headers=auth_headers_user_a)
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert data["total_documents"] >= 1
    assert data["total_pages"] >= 1
    assert "storage_used_bytes" in data
