from hashlib import sha256

from fastapi import FastAPI, HTTPException, UploadFile
from pydantic import BaseModel

from app.chunking import chunk_text

app = FastAPI(title="AI Knowledge Assistant", version="0.1.0")

MAX_FILE_SIZE = 1024 * 1024


class DocumentChunk(BaseModel):
    index: int
    text: str


class DocumentResponse(BaseModel):
    document_id: str
    filename: str
    chunk_count: int
    chunks: list[DocumentChunk]


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/documents", response_model=DocumentResponse)
async def ingest_document(file: UploadFile) -> DocumentResponse:
    try:
        filename = file.filename or ""

        if not filename.lower().endswith(".txt"):
            raise HTTPException(
                status_code=415,
                detail="Only .txt files are supported",
            )

        content = await file.read(MAX_FILE_SIZE + 1)

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

        chunks = [
            DocumentChunk(index=index, text=chunk)
            for index, chunk in enumerate(chunk_text(text))
        ]

        return DocumentResponse(
            document_id=sha256(content).hexdigest(),
            filename=filename,
            chunk_count=len(chunks),
            chunks=chunks,
        )
    finally:
        await file.close()