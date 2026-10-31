from hashlib import sha256
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, UploadFile
from pydantic import BaseModel

from app.chunking import chunk_text
from app.storage import DocumentStore, StoredDocument

app = FastAPI(title="AI Knowledge Assistant", version="0.1.0")

MAX_FILE_SIZE = 1024 * 1024
DB_PATH = Path(__file__).resolve().parent.parent / "data" / "documents.sqlite3"


class DocumentChunk(BaseModel):
    index: int
    text: str


class DocumentResponse(BaseModel):
    document_id: str
    filename: str
    chunk_count: int
    chunks: list[DocumentChunk]


def get_store() -> DocumentStore:
    return DocumentStore(DB_PATH)


def document_response(document: StoredDocument) -> DocumentResponse:
    return DocumentResponse(
        document_id=document.document_id,
        filename=document.filename,
        chunk_count=len(document.chunks),
        chunks=[
            DocumentChunk(index=index, text=text)
            for index, text in enumerate(document.chunks)
        ],
    )


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/documents", response_model=DocumentResponse)
def ingest_document(
    file: UploadFile,
    store: Annotated[DocumentStore, Depends(get_store)],
) -> DocumentResponse:
    try:
        filename = file.filename or ""

        if not filename.lower().endswith(".txt"):
            raise HTTPException(
                status_code=415,
                detail="Only .txt files are supported",
            )

        content = file.file.read(MAX_FILE_SIZE + 1)

        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=413,
                detail="File must not exceed 1 MiB",
            )

        try:
            text = content.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise HTTPException(
                status_code=400,
                detail="File must use UTF-8 encoding",
            ) from exc

        if not text.strip():
            raise HTTPException(
                status_code=400,
                detail="File must not be empty",
            )

        if "\x00" in text:
            raise HTTPException(
                status_code=400,
                detail="File must not contain null characters",
            )

        document = StoredDocument(
            document_id=sha256(content).hexdigest(),
            filename=filename,
            chunks=chunk_text(text),
        )
        store.save(document)
        stored_document = store.get(document.document_id)

        if stored_document is None:
            raise HTTPException(
                status_code=500,
                detail="Document could not be loaded after saving",
            )

        return document_response(stored_document)
    finally:
        file.file.close()


@app.get("/documents/{document_id}", response_model=DocumentResponse)
def read_document(
    document_id: str,
    store: Annotated[DocumentStore, Depends(get_store)],
) -> DocumentResponse:
    document = store.get(document_id)

    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")

    return document_response(document)