from unittest.mock import Mock

import pytest

from app import embeddings
from app.main import app, get_store
from app.storage import DocumentStore


@pytest.fixture(autouse=True)
def offline_model(monkeypatch):
    model = Mock()
    model.max_seq_length = 512

    def tokenize(text, *, add_special_tokens, truncation):
        assert add_special_tokens is True
        assert truncation is False
        return {"input_ids": [0] * (len(text.split()) + 2)}

    model.tokenizer.side_effect = tokenize
    model.encode.side_effect = AssertionError(
        "Use an explicit embedding stub in this test"
    )

    monkeypatch.setattr(
        embeddings,
        "get_model",
        Mock(return_value=model),
    )

    return model


@pytest.fixture(autouse=True)
def isolated_store(tmp_path):
    store = DocumentStore(tmp_path / "documents.sqlite3")
    app.dependency_overrides[get_store] = lambda: store

    try:
        yield store
    finally:
        app.dependency_overrides.pop(get_store, None)