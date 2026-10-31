import pytest

from app.storage import DocumentStore, StoredDocument


def test_document_persists_after_reopening_store(tmp_path):
    db_path = tmp_path / "data" / "documents.sqlite3"
    document = StoredDocument(
        document_id="doc-1",
        filename="anotações.txt",
        chunks=[f"Trecho {index}" for index in range(12)],
    )

    store = DocumentStore(db_path)

    assert store.save(document) is True

    reopened_store = DocumentStore(db_path)

    assert reopened_store.get("doc-1") == document


def test_duplicate_id_preserves_original_document(tmp_path):
    store = DocumentStore(tmp_path / "documents.sqlite3")
    original = StoredDocument(
        document_id="doc-1",
        filename="original.txt",
        chunks=["Primeiro trecho.", "Segundo trecho."],
    )
    duplicate = StoredDocument(
        document_id="doc-1",
        filename="outro-nome.txt",
        chunks=["Outro conteúdo."],
    )

    assert store.save(original) is True
    assert store.save(duplicate) is False
    assert store.get("doc-1") == original


def test_missing_document_returns_none(tmp_path):
    store = DocumentStore(tmp_path / "documents.sqlite3")

    assert store.get("inexistente") is None


@pytest.mark.parametrize(
    ("document_id", "filename", "chunks"),
    [
        ("", "arquivo.txt", ["Texto válido."]),
        ("doc-1", " ", ["Texto válido."]),
        ("doc-1", "arquivo.txt", []),
        ("doc-1", "arquivo.txt", [" \n\t "]),
    ],
)
def test_invalid_document_is_not_saved(
    tmp_path,
    document_id,
    filename,
    chunks,
):
    store = DocumentStore(tmp_path / "documents.sqlite3")
    document = StoredDocument(document_id, filename, chunks)

    with pytest.raises(ValueError):
        store.save(document)

    assert store.get(document_id) is None