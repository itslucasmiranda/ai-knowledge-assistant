from hashlib import sha256
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, UploadFile
from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.chunking import chunk_text
from app.storage import DocumentStore, StoredDocument

from app.embeddings import EmbeddingInputError, split_passages
from app.retrieval import SearchResult, search_documents
from app.answers import AnswerResponse, answer_question
from app.observability import record_request
from app.llm import (
    LLMConfigurationError,
    LLMResponseError,
    LLMTimeoutError,
    LLMUnavailableError,
)

app = FastAPI(title="AI Knowledge Assistant", version="1.0.0")
app.middleware("http")(record_request)

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

        document_id = sha256(content).hexdigest()
        existing_document = store.get(document_id)

        if existing_document is not None:
            return document_response(existing_document)

        document = StoredDocument(
            document_id=document_id,
            filename=filename,
            chunks=split_passages(chunk_text(text)),
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

class SearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: Annotated[
        str,
        StringConstraints(strip_whitespace=True, min_length=1, max_length=2000),
    ]
    top_k: Annotated[int, Field(strict=True, ge=1, le=20)] = 3
    document_id: Annotated[
        str, Field(pattern=r"^[0-9a-f]{64}$")
    ] | None = None


class SearchResponse(BaseModel):
    query: str
    result_count: int
    results: list[SearchResult]


@app.post("/search", response_model=SearchResponse)
def search(
    request: SearchRequest,
    store: Annotated[DocumentStore, Depends(get_store)],
) -> SearchResponse:
    try:
        results = search_documents(
            store=store,
            query=request.query,
            top_k=request.top_k,
            document_id=request.document_id,
        )
    except EmbeddingInputError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return SearchResponse(
        query=request.query,
        result_count=len(results),
        results=results,
    )


class AskRequest(SearchRequest):
    top_k: Annotated[int, Field(strict=True, ge=1, le=5)] = 3


@app.post("/ask", response_model=AnswerResponse)
def ask(
    request: AskRequest,
    store: Annotated[DocumentStore, Depends(get_store)],
) -> AnswerResponse:
    try:
        return answer_question(
            store, request.query, top_k=request.top_k, document_id=request.document_id
        )
    except EmbeddingInputError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except LLMConfigurationError:
        raise HTTPException(status_code=503, detail="Answer generation is not configured") from None
    except LLMUnavailableError:
        raise HTTPException(status_code=503, detail="Answer generation is temporarily unavailable") from None
    except LLMTimeoutError:
        raise HTTPException(status_code=504, detail="Answer generation timed out") from None
    except LLMResponseError:
        raise HTTPException(status_code=502, detail="Answer provider returned an invalid response") from None
