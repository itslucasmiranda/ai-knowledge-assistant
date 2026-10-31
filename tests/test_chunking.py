import pytest

from app.chunking import chunk_text


def test_short_text_returns_one_chunk():
    assert chunk_text("Um documento curto.") == ["Um documento curto."]


def test_chunks_preserve_overlap_and_cover_text():
    result = chunk_text(
        "um dois tres quatro cinco seis sete",
        chunk_size=4,
        overlap=1,
    )

    assert result == [
        "um dois tres quatro",
        "quatro cinco seis sete",
    ]


def test_blank_text_is_rejected():
    with pytest.raises(ValueError, match="text must not be empty"):
        chunk_text(" \n\t ")


@pytest.mark.parametrize(
    ("chunk_size", "overlap"),
    [(0, 0), (4, -1), (4, 4)],
)
def test_invalid_chunk_settings_are_rejected(chunk_size, overlap):
    with pytest.raises(ValueError):
        chunk_text(
            "um dois tres quatro cinco",
            chunk_size=chunk_size,
            overlap=overlap,
        )