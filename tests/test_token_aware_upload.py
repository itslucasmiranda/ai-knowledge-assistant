from hashlib import sha256
from unittest.mock import Mock

from fastapi.testclient import TestClient

from app import embeddings
from app.main import app
from app.storage import DocumentStore


def test_upload_persists_chunks_within_token_limit(
    isolated_store,
    offline_model,
):
    model = offline_model
    model.max_seq_length = 32

    def tokenize(text, *, add_special_tokens, truncation):
        assert add_special_tokens is True
        assert truncation is False
        return {"input_ids": [0] * (len(text) + 2)}

    model.tokenizer.side_effect = tokenize

    text = "á漢🙂" * 80
    content = text.encode("utf-8")

    with TestClient(app) as client:
        response = client.post(
            "/documents",
            files={"file": ("longo.txt", content, "text/plain")},
        )

        assert response.status_code == 200

        data = response.json()
        chunks = [chunk["text"] for chunk in data["chunks"]]

        assert data["document_id"] == sha256(content).hexdigest()
        assert data["chunk_count"] == len(chunks)
        assert len(chunks) > 1
        assert "".join(chunks) == text
        assert [chunk["index"] for chunk in data["chunks"]] == list(
            range(len(chunks))
        )

        for chunk in chunks:
            tokens = model.tokenizer(
                "passage: " + chunk,
                add_special_tokens=True,
                truncation=False,
            )["input_ids"]

            assert len(tokens) <= model.max_seq_length

        reopened_store = DocumentStore(isolated_store.db_path)
        saved = reopened_store.get(data["document_id"])

        assert saved is not None
        assert saved.chunks == chunks

        fetched = client.get(
            f"/documents/{data['document_id']}"
        )

        assert fetched.status_code == 200
        assert fetched.json() == data

    model.encode.assert_not_called()


def test_duplicate_upload_does_not_load_model_again(monkeypatch):
    content = b"Documento ja cadastrado."

    with TestClient(app) as client:
        first = client.post(
            "/documents",
            files={"file": ("original.txt", content, "text/plain")},
        )

        assert first.status_code == 200

        loader = Mock(
            side_effect=AssertionError(
                "Duplicate upload must not load the model"
            )
        )
        monkeypatch.setattr(embeddings, "get_model", loader)

        second = client.post(
            "/documents",
            files={"file": ("renomeado.txt", content, "text/plain")},
        )

        assert second.status_code == 200
        assert second.json() == first.json()
        loader.assert_not_called()