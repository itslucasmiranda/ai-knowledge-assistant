from unittest.mock import Mock

import pytest

from app import embeddings


@pytest.fixture
def model_stub(monkeypatch):
    model = Mock()
    model.max_seq_length = 512
    model.tokenizer.return_value = {"input_ids": [0, 1, 2]}
    model.encode.return_value.tolist.return_value = [
        [1.0] + [0.0] * 383
    ]

    loader = Mock(return_value=model)
    monkeypatch.setattr(embeddings, "get_model", loader)
    return model, loader


@pytest.mark.parametrize("text", ["", " \n\t"])
@pytest.mark.parametrize("kind", ["query", "passage"])
def test_blank_text_is_rejected_before_loading_model(
    model_stub, text, kind
):
    _, loader = model_stub

    with pytest.raises(ValueError, match="Text must not be empty"):
        if kind == "query":
            embeddings.embed_query(text)
        else:
            embeddings.embed_passages([text])

    loader.assert_not_called()


def test_empty_passages_do_not_load_model(model_stub):
    _, loader = model_stub

    assert embeddings.embed_passages([]) == []

    loader.assert_not_called()


def test_query_uses_query_prefix_and_normalization(model_stub):
    model, _ = model_stub

    result = embeddings.embed_query(" Onde ficam os documentos? ")

    assert result == [1.0] + [0.0] * 383
    assert model.encode.call_args.args[0] == [
        "query: Onde ficam os documentos?"
    ]
    assert model.encode.call_args.kwargs["normalize_embeddings"] is True
    assert model.encode.call_args.kwargs["prompt"] == ""


def test_passages_preserve_order_and_use_passage_prefix(model_stub):
    model, _ = model_stub
    vectors = [
        [1.0] + [0.0] * 383,
        [0.0, 1.0] + [0.0] * 382,
    ]
    model.encode.return_value.tolist.return_value = vectors

    result = embeddings.embed_passages(
        [" Primeiro trecho. ", "Segundo trecho."]
    )

    assert result == vectors
    assert model.encode.call_args.args[0] == [
        "passage: Primeiro trecho.",
        "passage: Segundo trecho.",
    ]
    assert model.encode.call_args.kwargs["normalize_embeddings"] is True


@pytest.mark.parametrize(
    ("model_limit", "token_count", "should_reject"),
    [
        (512, 512, False),
        (512, 513, True),
        (256, 257, True),
    ],
)
def test_token_limit_is_respected(
    model_stub, model_limit, token_count, should_reject
):
    model, _ = model_stub
    model.max_seq_length = model_limit
    model.tokenizer.return_value = {
        "input_ids": list(range(token_count))
    }

    if should_reject:
        with pytest.raises(ValueError, match="Text exceeds"):
            embeddings.embed_query("Texto de teste")
        model.encode.assert_not_called()
    else:
        assert len(embeddings.embed_query("Texto de teste")) == 384

    assert model.tokenizer.call_args.kwargs["truncation"] is False