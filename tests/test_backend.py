from fastapi.testclient import TestClient

from backend.app import app


def test_health_reports_status_and_chunk_count(monkeypatch):
    monkeypatch.setattr("backend.app.get_chunk_count", lambda: 7)
    response = TestClient(app).get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "chunks": 7}
