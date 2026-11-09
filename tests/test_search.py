from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from app import retrieval
from app.embeddings import EmbeddingInputError
from app.main import app


@pytest.fixture
def client():
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client


@pytest.fixture
def encoders(monkeypatch):
    vectors = {
        "Texto sobre SQLite.": [1.0, 0.0],
        "Receita de bolo.": [0.0, 1.0],
    }
    query_encoder = Mock(return_value=[1.0, 0.0])
    passage_encoder = Mock(
        side_effect=lambda texts: [vectors[text] for text in texts]
    )
    monkeypatch.setattr(retrieval, "embed_query", query_encoder)
    monkeypatch.setattr(retrieval, "embed_passages", passage_encoder)
    return query_encoder, passage_encoder


@pytest.fixture
def documents(client):
    ids = {}
    for filename, text in [
        ("armazenamento.txt", "Texto sobre SQLite."),
        ("receita.txt", "Receita de bolo."),
    ]:
        response = client.post(
            "/documents",
            files={"file": (filename, text.encode("utf-8"), "text/plain")},
        )
        assert response.status_code == 200
        ids[filename] = response.json()["document_id"]
    return ids


def test_search_returns_ranked_sources(client, documents, encoders):
    response = client.post(
        "/search", json={"query": " Onde salvar? ", "top_k": 1}
    )

    assert response.status_code == 200
    assert response.json() == {
        "query": "Onde salvar?",
        "result_count": 1,
        "results": [
            {
                "document_id": documents["armazenamento.txt"],
                "filename": "armazenamento.txt",
                "chunk_index": 0,
                "text": "Texto sobre SQLite.",
                "score": 1.0,
            }
        ],
    }


def test_search_filters_document(client, documents, encoders):
    response = client.post(
        "/search",
        json={
            "query": "Onde salvar?",
            "document_id": documents["receita.txt"],
        },
    )

    assert response.status_code == 200
    assert response.json()["result_count"] == 1
    assert response.json()["results"][0]["filename"] == "receita.txt"
    encoders[1].assert_called_once_with(["Receita de bolo."])


def test_search_empty_store_returns_empty_results(client, encoders):
    response = client.post("/search", json={"query": "Onde salvar?"})

    assert response.status_code == 200
    assert response.json()["results"] == []
    assert response.json()["result_count"] == 0
    encoders[0].assert_not_called()
    encoders[1].assert_not_called()


def test_search_unknown_document_returns_empty_results(client, documents, encoders):
    response = client.post(
        "/search", json={"query": "Onde salvar?", "document_id": "0" * 64}
    )

    assert response.status_code == 200
    assert response.json()["results"] == []
    encoders[0].assert_not_called()
    encoders[1].assert_not_called()


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"query": ""},
        {"query": " \n\t"},
        {"query": "x" * 2001},
        {"query": "Teste", "top_k": 0},
        {"query": "Teste", "top_k": 21},
        {"query": "Teste", "top_k": True},
        {"query": "Teste", "top_k": 1.5},
        {"query": "Teste", "top_k": "3"},
        {"query": "Teste", "document_id": "invalid"},
        {"query": 123},
        {"query": "Teste", "unknown_field": True},
    ],
)
def test_invalid_search_is_rejected(client, encoders, payload):
    response = client.post("/search", json=payload)

    assert response.status_code == 422
    encoders[0].assert_not_called()
    encoders[1].assert_not_called()


def test_embedding_input_error_returns_422(client, documents, encoders):
    encoders[1].side_effect = EmbeddingInputError("Text exceeds the model limit")

    response = client.post("/search", json={"query": "Onde salvar?"})

    assert response.status_code == 422
    assert response.json()["detail"] == "Text exceeds the model limit"


def test_internal_error_is_not_reported_as_invalid_input(client, documents, encoders):
    encoders[1].side_effect = ValueError("Internal embedding failure")

    response = client.post("/search", json={"query": "Onde salvar?"})

    assert response.status_code == 500
    assert "Internal embedding failure" not in response.text