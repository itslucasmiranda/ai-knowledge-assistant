def chunk_text(
    text: str,
    chunk_size: int = 100,
    overlap: int = 20,
) -> list[str]:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than zero")

    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap must be between zero and chunk_size - 1")

    words = text.split()

    if not words:
        raise ValueError("text must not be empty")

    chunks = []
    start = 0

    while start < len(words):
        end = start + chunk_size
        chunks.append(" ".join(words[start:end]))

        if end >= len(words):
            break

        start = end - overlap

    return chunks