from dataclasses import dataclass
from math import fsum, isfinite

from app.embeddings import embed_passages, embed_query, split_passages
from app.storage import DocumentStore


@dataclass(frozen=True)
class SearchResult:
    document_id: str
    filename: str
    chunk_index: int
    text: str
    score: float


def search_documents(
    store: DocumentStore,
    query: str,
    top_k: int = 3,
    document_id: str | None = None,
) -> list[SearchResult]:
    query = query.strip()
    if not query:
        raise ValueError("Query must not be empty")
    if type(top_k) is not int or not 1 <= top_k <= 20:
        raise ValueError("top_k must be an integer between 1 and 20")

    chunks = store.list_chunks(document_id)
    if not chunks:
        return []

    query_vector = embed_query(query)
    passages = []
    sources = []

    for chunk in chunks:
        parts = split_passages([chunk.text])
        passages.extend(parts)
        sources.extend([chunk] * len(parts))

    passage_vectors = embed_passages(passages)
    best_results: dict[tuple[str, int], SearchResult] = {}

    for chunk, text, vector in zip(
        sources, passages, passage_vectors, strict=True
    ):
        score = fsum(
            left * right
            for left, right in zip(query_vector, vector, strict=True)
        )
        if not isfinite(score):
            raise ValueError("Embedding score must be finite")

        score = max(-1.0, min(1.0, score))
        key = (chunk.document_id, chunk.index)
        previous = best_results.get(key)

        if previous is None or score > previous.score:
            best_results[key] = SearchResult(
                document_id=chunk.document_id,
                filename=chunk.filename,
                chunk_index=chunk.index,
                text=text,
                score=score,
            )

    results = sorted(
        best_results.values(),
        key=lambda result: (
            -result.score, result.document_id, result.chunk_index
        ),
    )
    return results[:top_k]

