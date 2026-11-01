from dataclasses import dataclass
from math import fsum, isfinite

from app.embeddings import embed_passages, embed_query
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
    passage_vectors = embed_passages([chunk.text for chunk in chunks])
    results = []

    for chunk, vector in zip(chunks, passage_vectors, strict=True):
        score = fsum(
            left * right
            for left, right in zip(query_vector, vector, strict=True)
        )
        if not isfinite(score):
            raise ValueError("Embedding score must be finite")

        results.append(
            SearchResult(
                document_id=chunk.document_id,
                filename=chunk.filename,
                chunk_index=chunk.index,
                text=chunk.text,
                score=max(-1.0, min(1.0, score)),
            )
        )

    results.sort(
        key=lambda result: (
            -result.score, result.document_id, result.chunk_index
        )
    )
    return results[:top_k]