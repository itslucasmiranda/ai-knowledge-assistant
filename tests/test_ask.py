from unittest.mock import Mock
import json

import httpx
import pytest
from fastapi.testclient import TestClient

from app import answers, retrieval
from app import llm
from app.embeddings import EmbeddingInputError
from app.llm import (
    Generation, LLMConfigurationError, LLMResponseError, LLMTimeoutError, LLMUnavailableError,
)
from app.main import app
from app.retrieval import SearchResult
from app.storage import StoredDocument


@pytest.fixture
def client():
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client


@pytest.fixture(autouse=True)
def generator(monkeypatch):
    generator = Mock(return_value=Generation(
        can_answer=True, answer="Os documentos ficam no SQLite.", source_ids=["S1"]
    ))
    monkeypatch.setattr(answers, "generate_answer", generator)
    return generator


@pytest.fixture
def documents(isolated_store, monkeypatch):
    isolated_store.save(StoredDocument("a" * 64, "armazenamento.txt", ["Salvos no SQLite."]))
    isolated_store.save(StoredDocument("b" * 64, "receita.txt", ["Misture ovos e farinha."]))
    monkeypatch.setattr(retrieval, "embed_query", lambda query: [1., 0.])
    monkeypatch.setattr(retrieval, "embed_passages", lambda texts: [
        [1., 0.] if "SQLite" in text else [0., 1.] for text in texts
    ])


def test_answer_has_only_cited_sources_with_original_metadata(client, documents, generator):
    response = client.post("/ask", json={"query": " Onde ficam? "})
    assert response.status_code == 200
    assert response.json() == {
        "query": "Onde ficam?", "status": "answered",
        "answer": "Os documentos ficam no SQLite.",
        "sources": [{"source_id": "S1", "document_id": "a" * 64,
                     "filename": "armazenamento.txt", "chunk_index": 0,
                     "text": "Salvos no SQLite.", "score": 1.0}],
    }
    assert len(generator.call_args.args[1]) == 2


def test_filter_applies_before_generation(client, documents, generator):
    response = client.post("/ask", json={"query": "Como preparar?", "document_id": "b" * 64})
    assert response.status_code == 200
    assert response.json()["sources"][0]["document_id"] == "b" * 64
    assert generator.call_args.args[1] == [{"source_id": "S1", "text": "Misture ovos e farinha."}]


def test_top_k_limits_context(client, documents, generator):
    assert client.post("/ask", json={"query": "Onde?", "top_k": 1}).status_code == 200
    assert len(generator.call_args.args[1]) == 1


def test_empty_store_does_not_call_provider(client, generator):
    response = client.post("/ask", json={"query": "Onde?"})
    assert response.json()["status"] == "insufficient_context"
    assert response.json()["sources"] == []
    generator.assert_not_called()


def test_unknown_document_does_not_call_provider(client, documents, generator):
    response = client.post("/ask", json={"query": "Onde?", "document_id": "c" * 64})
    assert response.status_code == 200
    assert response.json()["status"] == "insufficient_context"
    generator.assert_not_called()


def test_model_abstention_discards_unsupported_answer(client, documents, generator):
    generator.return_value = Generation(can_answer=False, answer="Unsupported claim", source_ids=["S99"])
    response = client.post("/ask", json={"query": "Quem ganhou a corrida?"})
    assert response.json()["status"] == "insufficient_context"
    assert response.json()["answer"] == answers.INSUFFICIENT_CONTEXT
    assert response.json()["sources"] == []


@pytest.mark.parametrize("answer,ids", [
    ("", ["S1"]), (" \n", ["S1"]), ("Texto", []), ("Texto", ["S99"]),
    ("Texto [S2]", ["S1"]), ("x" * 8001, ["S1"]),
])
def test_invalid_answer_is_502_not_a_fabricated_success(client, documents, generator, answer, ids):
    generator.return_value = Generation(can_answer=True, answer=answer, source_ids=ids)
    response = client.post("/ask", json={"query": "Onde?"})
    assert response.status_code == 502
    assert "sources" not in response.json()


def test_duplicate_citations_are_deduplicated(client, documents, generator):
    generator.return_value.source_ids = ["S1", "S1"]
    assert len(client.post("/ask", json={"query": "Onde?"}).json()["sources"]) == 1


def test_context_budget_preserves_whole_fragments(client, monkeypatch, generator):
    monkeypatch.setattr(answers, "search_documents", lambda *args, **kwargs: [
        SearchResult("a" * 64, "a.txt", 0, "a" * 7000, .9),
        SearchResult("b" * 64, "b.txt", 0, "b" * 6000, .8),
        SearchResult("c" * 64, "c.txt", 0, "c" * 5000, .7),
    ])
    response = client.post("/ask", json={"query": "Onde?"})
    assert response.status_code == 200
    context = generator.call_args.args[1]
    assert [item["text"] for item in context] == ["a" * 7000, "c" * 5000]


@pytest.mark.parametrize("payload", [
    {}, {"query": " "}, {"query": "x" * 2001}, {"query": 12},
    {"query": "Onde?", "top_k": 6}, {"query": "Onde?", "top_k": 0},
    {"query": "Onde?", "top_k": True}, {"query": "Onde?", "top_k": "3"},
    {"query": "Onde?", "document_id": "invalid"},
    {"query": "Onde?", "api_key": "not-accepted"},
])
def test_request_validation_prevents_generation(client, generator, payload):
    assert client.post("/ask", json=payload).status_code == 422
    generator.assert_not_called()


@pytest.mark.parametrize("error,status", [
    (LLMConfigurationError("PRIVATE"), 503), (LLMUnavailableError("PRIVATE"), 503),
    (LLMTimeoutError("PRIVATE"), 504), (LLMResponseError("PRIVATE"), 502),
    (RuntimeError("PRIVATE"), 500),
])
def test_provider_errors_are_sanitized(client, documents, generator, error, status):
    generator.side_effect = error
    response = client.post("/ask", json={"query": "Onde?"})
    assert response.status_code == status
    assert "PRIVATE" not in response.text


def test_embedding_validation_stops_before_generation(client, monkeypatch, generator):
    monkeypatch.setattr(answers, "search_documents", Mock(side_effect=EmbeddingInputError("Too many tokens")))
    assert client.post("/ask", json={"query": "Onde?"}).status_code == 422
    generator.assert_not_called()


def test_full_ask_flow_with_mock_http_provider(client, documents, monkeypatch, tmp_path):
    monkeypatch.setattr(answers, "generate_answer", llm.generate_answer)
    monkeypatch.setattr(llm, "KEY_PATH", tmp_path / "absent-key")
    monkeypatch.setenv("GROQ_API_KEY", "gsk_test_only")
    original_client = httpx.Client
    calls = []

    def handler(request):
        payload = json.loads(request.content)
        context = json.loads(payload["messages"][1]["content"])
        calls.append(context)
        assert context["sources"] == [{"source_id": "S1", "text": "Salvos no SQLite."}]
        return httpx.Response(200, json={"choices": [{
            "finish_reason": "stop", "message": {"content": json.dumps({
                "can_answer": True, "answer": "No SQLite.", "source_ids": ["S1"]
            })}
        }]})

    monkeypatch.setattr(llm.httpx, "Client", lambda **kwargs: original_client(
        transport=httpx.MockTransport(handler), **kwargs
    ))
    response = client.post("/ask", json={"query": "Onde?", "document_id": "a" * 64})
    assert response.status_code == 200
    assert response.json()["answer"] == "No SQLite."
    assert response.json()["sources"][0]["document_id"] == "a" * 64
    assert len(calls) == 1
