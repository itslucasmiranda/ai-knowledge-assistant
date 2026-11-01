import pytest

from app.storage import StoredChunk, StoredDocument


@pytest.fixture
def populated_store(isolated_store):
    isolated_store.save(
        StoredDocument("doc-b", "b.txt", ["Texto B"])
    )
    isolated_store.save(
        StoredDocument(
            "doc-a",
            "a.txt",
            [f"Trecho {index}" for index in range(12)],
        )
    )
    return isolated_store


def test_empty_store_returns_no_chunks(isolated_store):
    assert isolated_store.list_chunks() == []


def test_chunks_preserve_source_and_numeric_order(populated_store):
    expected = [
        StoredChunk("doc-a", "a.txt", index, f"Trecho {index}")
        for index in range(12)
    ]
    expected.append(StoredChunk("doc-b", "b.txt", 0, "Texto B"))

    assert populated_store.list_chunks() == expected


def test_filter_returns_only_requested_document(populated_store):
    assert populated_store.list_chunks("doc-b") == [
        StoredChunk("doc-b", "b.txt", 0, "Texto B")
    ]


def test_unknown_ids_do_not_return_other_documents(populated_store):
    assert populated_store.list_chunks("missing") == []
    assert populated_store.list_chunks("doc-a' OR 1=1 --") == []