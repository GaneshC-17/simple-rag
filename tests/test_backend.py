from fastapi.testclient import TestClient

from backend.app import app
from simple_rag.prompts.context import Context
from simple_rag.vectorstore.pg_store import SearchResult


def test_health_reports_status_and_chunk_count(monkeypatch):
    monkeypatch.setattr("backend.app.get_chunk_count", lambda: 7)
    response = TestClient(app).get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "chunks": 7}


def test_ask_returns_answer_and_sources(monkeypatch):
    from simple_rag.vectorstore.pg_store import SearchResult
    from simple_rag.prompts.context import Context

    result = SearchResult("The rules of heredity...", "notes.pdf", 3, 0.56)
    monkeypatch.setattr("backend.app.retrieve", lambda q, top_k: [result])
    monkeypatch.setattr(
        "backend.app.build_context",
        lambda r, max_tokens: Context("The rules of heredity...", 1, 10),
    )
    monkeypatch.setattr(
        "backend.app.generate_answer",
        lambda q, c: "The rules of heredity determine inheritance.",
    )

    response = TestClient(app).post("/api/ask", json={"question": "What is heredity?"})
    assert response.status_code == 200
    body = response.json()
    assert body["answer"] == "The rules of heredity determine inheritance."
    assert body["sources"][0] == {
        "content": "The rules of heredity...",
        "source": "notes.pdf",
        "chunk_index": 3,
        "similarity": 0.56,
    }


def test_ask_rejects_empty_question():
    assert TestClient(app).post("/api/ask", json={"question": "   "}).status_code == 400


def test_ask_returns_502_when_llm_fails(monkeypatch):
    def boom(q, c):
        raise RuntimeError("Cannot reach freellmapi")

    monkeypatch.setattr("backend.app.retrieve", lambda q, top_k: [])
    monkeypatch.setattr(
        "backend.app.build_context", lambda r, max_tokens: Context("", 0, 0)
    )
    monkeypatch.setattr("backend.app.generate_answer", boom)

    response = TestClient(app).post("/api/ask", json={"question": "anything"})
    assert response.status_code == 502
    assert "freellmapi" in response.json()["detail"]


def test_ask_with_no_documents_returns_grounded_answer(monkeypatch):
    monkeypatch.setattr("backend.app.retrieve", lambda q, top_k: [])
    monkeypatch.setattr(
        "backend.app.build_context", lambda r, max_tokens: Context("", 0, 0)
    )
    monkeypatch.setattr(
        "backend.app.generate_answer",
        lambda q, c: "I don't know based on the provided documents.",
    )

    body = TestClient(app).post("/api/ask", json={"question": "anything"}).json()
    assert body["sources"] == []
    assert "I don't know" in body["answer"]


def test_index_accepts_pdf_and_saves_sanitized_name(monkeypatch, tmp_path):
    from simple_rag.pipeline import IndexStats

    saved = {}
    monkeypatch.setattr("backend.app.RAW_DIR", tmp_path)

    def fake_index(path):
        saved["path"] = path
        return IndexStats("my doc.pdf", 2, 3, 100)

    monkeypatch.setattr("backend.app.index_pdf", fake_index)

    response = TestClient(app).post(
        "/api/index",
        files={"file": ("../../my doc.pdf", b"%PDF-1.4 fake", "application/pdf")},
    )
    assert response.status_code == 200
    assert response.json() == {
        "source": "my doc.pdf",
        "pages": 2,
        "chunks": 3,
        "tokens": 100,
    }
    assert saved["path"].endswith("my doc.pdf")
    assert (tmp_path / "my doc.pdf").exists()


def test_index_rejects_non_pdf():
    response = TestClient(app).post(
        "/api/index", files={"file": ("notes.txt", b"hello", "text/plain")}
    )
    assert response.status_code == 400
    assert "pdf" in response.json()["detail"].lower()


def test_index_rejects_file_without_pdf_magic_bytes():
    response = TestClient(app).post(
        "/api/index", files={"file": ("fake.pdf", b"hello", "application/pdf")}
    )
    assert response.status_code == 400
    assert "look like a PDF" in response.json()["detail"]
