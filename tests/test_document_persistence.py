from fastapi.testclient import TestClient

from app.main import app
from app.storage import DocumentStore

client = TestClient(app)


def test_uploaded_document_can_be_retrieved(isolated_store):
    upload = client.post(
        "/documents",
        files={
            "file": (
                "persistencia.txt",
                "Texto que deve continuar salvo.".encode("utf-8"),
                "text/plain",
            )
        },
    )

    assert upload.status_code == 200

    document = upload.json()
    document_id = document["document_id"]
    response = client.get(f"/documents/{document_id}")

    assert response.status_code == 200
    assert response.json() == document

    reopened_store = DocumentStore(isolated_store.db_path)
    stored_document = reopened_store.get(document_id)

    assert stored_document is not None
    assert stored_document.filename == "persistencia.txt"
    assert stored_document.chunks == ["Texto que deve continuar salvo."]


def test_duplicate_upload_returns_original_document():
    content = b"Mesmo conteudo enviado duas vezes."

    first = client.post(
        "/documents",
        files={"file": ("original.txt", content, "text/plain")},
    )
    second = client.post(
        "/documents",
        files={"file": ("renomeado.txt", content, "text/plain")},
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json() == first.json()
    assert second.json()["filename"] == "original.txt"


def test_unknown_document_returns_404():
    response = client.get("/documents/inexistente")

    assert response.status_code == 404
    assert response.json() == {"detail": "Document not found"}