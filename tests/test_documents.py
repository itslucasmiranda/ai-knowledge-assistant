from hashlib import sha256

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


@pytest.mark.parametrize("encoding", ["utf-8", "utf-8-sig"])
def test_upload_returns_document_and_chunks(encoding):
    text = "Documento com acentuação para testar a ingestão."
    content = text.encode(encoding)

    response = client.post(
        "/documents",
        files={"file": ("exemplo.txt", content, "text/plain")},
    )

    assert response.status_code == 200
    assert response.json() == {
        "document_id": sha256(content).hexdigest(),
        "filename": "exemplo.txt",
        "chunk_count": 1,
        "chunks": [{"index": 0, "text": text}],
    }


def test_long_document_returns_overlapping_chunks():
    words = [f"palavra{number}" for number in range(101)]
    content = " ".join(words).encode("utf-8")

    response = client.post(
        "/documents",
        files={"file": ("longo.txt", content, "text/plain")},
    )

    assert response.status_code == 200

    data = response.json()

    assert data["chunk_count"] == 2
    assert data["chunks"] == [
        {"index": 0, "text": " ".join(words[:100])},
        {"index": 1, "text": " ".join(words[80:])},
    ]


@pytest.mark.parametrize(
    ("filename", "content", "status_code", "detail"),
    [
        (
            "vazio.txt",
            b"",
            400,
            "File must not be empty",
        ),
        (
            "espacos.txt",
            b" \n\t ",
            400,
            "File must not be empty",
        ),
        (
            "invalido.txt",
            b"\xff\xfe",
            400,
            "File must use UTF-8 encoding",
        ),
        (
            "nulo.txt",
            b"texto\x00invalido",
            400,
            "File must not contain null characters",
        ),
        (
            "documento.pdf",
            b"conteudo",
            415,
            "Only .txt files are supported",
        ),
    ],
)
def test_invalid_documents_are_rejected(
    filename,
    content,
    status_code,
    detail,
):
    response = client.post(
        "/documents",
        files={"file": (filename, content, "application/octet-stream")},
    )

    assert response.status_code == status_code
    assert response.json() == {"detail": detail}


@pytest.mark.parametrize(
    ("size", "status_code"),
    [
        (1_048_576, 200),
        (1_048_577, 413),
    ],
)
def test_document_size_boundary(size, status_code):
    response = client.post(
        "/documents",
        files={"file": ("limite.txt", b"a" * size, "text/plain")},
    )

    assert response.status_code == status_code

    if status_code == 413:
        assert response.json() == {
            "detail": "File must not exceed 1 MiB"
        }


def test_upload_requires_file():
    response = client.post("/documents")

    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", "file"]