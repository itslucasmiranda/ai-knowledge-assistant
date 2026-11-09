from unittest.mock import Mock

import pytest

from app import embeddings


@pytest.fixture
def model_stub(monkeypatch):
    model = Mock()
    model.max_seq_length = 24

    def tokenize(text, *, add_special_tokens, truncation):
        assert add_special_tokens is True
        assert truncation is False
        return {"input_ids": list(range(len(text) + 2))}

    model.tokenizer.side_effect = tokenize
    loader = Mock(return_value=model)
    monkeypatch.setattr(embeddings, "get_model", loader)

    return model, loader


def test_empty_list_does_not_load_model(model_stub):
    _, loader = model_stub

    assert embeddings.split_passages([]) == []

    loader.assert_not_called()


@pytest.mark.parametrize("text", ["", " \n\t"])
def test_blank_passage_is_rejected_before_loading(model_stub, text):
    _, loader = model_stub

    with pytest.raises(embeddings.EmbeddingInputError):
        embeddings.split_passages(["Texto válido.", text])

    loader.assert_not_called()


def test_short_passages_preserve_order(model_stub):
    model, _ = model_stub

    result = embeddings.split_passages([" Primeiro. ", "Segundo."])

    assert result == ["Primeiro.", "Segundo."]
    model.encode.assert_not_called()


@pytest.mark.parametrize("model_limit", [24, 1024])
def test_long_passage_respects_effective_limit(model_stub, model_limit):
    model, _ = model_stub
    model.max_seq_length = model_limit
    text = "á漢🙂" * 400

    result = embeddings.split_passages([text])

    assert len(result) > 1
    assert "".join(result) == text

    limit = min(512, model_limit)

    for chunk in result:
        tokens = model.tokenizer(
            "passage: " + chunk,
            add_special_tokens=True,
            truncation=False,
        )["input_ids"]
        assert len(tokens) <= limit

    model.encode.assert_not_called()