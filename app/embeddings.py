from functools import lru_cache
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer

MODEL_NAME = "intfloat/multilingual-e5-small"


@lru_cache(maxsize=1)
def get_model() -> "SentenceTransformer":
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(MODEL_NAME, device="cpu")


def _encode(texts: list[str], prefix: str) -> list[list[float]]:
    if not texts:
        return []
    if any(not text.strip() for text in texts):
        raise ValueError("Text must not be empty")

    model = get_model()
    inputs = [f"{prefix}: {text.strip()}" for text in texts]
    limit = min(512, model.max_seq_length)

    for text in inputs:
        tokens = model.tokenizer(
            text, add_special_tokens=True, truncation=False
        )["input_ids"]
        if len(tokens) > limit:
            raise ValueError(f"Text exceeds the model limit of {limit} tokens")

    vectors = model.encode(
        inputs,
        prompt="",
        normalize_embeddings=True,
        convert_to_numpy=True,
        show_progress_bar=False,
        batch_size=16,
    )
    return vectors.tolist()


def embed_query(query: str) -> list[float]:
    return _encode([query], "query")[0]


def embed_passages(passages: list[str]) -> list[list[float]]:
    return _encode(passages, "passage")