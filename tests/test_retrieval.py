from unittest.mock import Mock

import pytest

from app import retrieval
from app.storage import StoredDocument


@pytest.fixture
def encoders(monkeypatch):
    vectors = {
        "Receita de bolo.": [0.0, 1.0],
        "Documentos ficam no SQLite.": [1.0, 0.0],
        "O arquivo persiste apos reiniciar.": [0.8, 0.6],
    }
    query_encoder = Mock(return_value=[1.0, 0.0])
    passage_encoder = Mock(
        side_effect=lambda texts: [vectors[text] for text in texts]
    )
    monkeypatch.setattr(retrieval, "embed_query", query_encoder)
    monkeypatch.setattr(retrieval, "embed_passages", passage_encoder)
    return query_encoder, passage_encoder


@pytest.fixture
def searchable_store(isolated_store):
    isolated_store.save(
        StoredDocument("doc-a", "receita.txt", ["Receita de bolo."])
    )
    isolated_store.save(
        StoredDocument(
            "doc-b",
            "armazenamento.txt",
            [
                "Documentos ficam no SQLite.",
                "O arquivo persiste apos reiniciar.",
            ],
        )
    )
    return isolated_store


def test_results_are_ranked_and_preserve_sources(searchable_store, encoders):
    results = retrieval.search_documents(searchable_store, "Onde salvar?")

    assert [result.score for result in results] == pytest.approx([1.0, 0.8, 0.0])
    assert [
        (result.document_id, result.filename, result.chunk_index, result.text)
        for result in results
    ] == [
        ("doc-b", "armazenamento.txt", 0, "Documentos ficam no SQLite."),
        ("doc-b", "armazenamento.txt", 1, "O arquivo persiste apos reiniciar."),
        ("doc-a", "receita.txt", 0, "Receita de bolo."),
    ]


def test_top_k_limits_results(searchable_store, encoders):
    results = retrieval.search_documents(
        searchable_store, "Onde salvar?", top_k=1
    )

    assert len(results) == 1
    assert results[0].document_id == "doc-b"
    assert results[0].chunk_index == 0


def test_document_filter_is_applied_before_encoding(searchable_store, encoders):
    _, passage_encoder = encoders

    results = retrieval.search_documents(
        searchable_store, "Onde salvar?", document_id="doc-a"
    )

    assert len(results) == 1
    assert results[0].document_id == "doc-a"
    passage_encoder.assert_called_once_with(["Receita de bolo."])


def test_empty_store_does_not_call_encoders(isolated_store, encoders):
    query_encoder, passage_encoder = encoders

    assert retrieval.search_documents(isolated_store, "Onde salvar?") == []
    query_encoder.assert_not_called()
    passage_encoder.assert_not_called()


@pytest.mark.parametrize("query", ["", " \n\t"])
def test_blank_query_is_rejected(isolated_store, encoders, query):
    with pytest.raises(ValueError, match="Query must not be empty"):
        retrieval.search_documents(isolated_store, query)

    encoders[0].assert_not_called()
    encoders[1].assert_not_called()


@pytest.mark.parametrize("top_k", [0, -1, 21])
def test_invalid_top_k_is_rejected(isolated_store, encoders, top_k):
    with pytest.raises(ValueError, match="top_k"):
        retrieval.search_documents(isolated_store, "Onde salvar?", top_k=top_k)


def test_encoding_error_is_not_hidden(searchable_store, encoders):
    _, passage_encoder = encoders
    passage_encoder.side_effect = ValueError("Text exceeds the model limit")

    with pytest.raises(ValueError, match="Text exceeds"):
        retrieval.search_documents(searchable_store, "Onde salvar?")