import re
from dataclasses import asdict
from typing import Literal

from pydantic import BaseModel

from app.llm import LLMResponseError, generate_answer
from app.retrieval import search_documents
from app.storage import DocumentStore

MAX_CONTEXT_CHARACTERS = 12000
INSUFFICIENT_CONTEXT = "Não encontrei informações suficientes nos documentos para responder."


class AnswerSource(BaseModel):
    source_id: str
    document_id: str
    filename: str
    chunk_index: int
    text: str
    score: float


class AnswerResponse(BaseModel):
    query: str
    status: Literal["answered", "insufficient_context"]
    answer: str
    sources: list[AnswerSource]


def insufficient_context(query: str) -> AnswerResponse:
    return AnswerResponse(
        query=query, status="insufficient_context", answer=INSUFFICIENT_CONTEXT, sources=[]
    )


def answer_question(
    store: DocumentStore, query: str, top_k: int = 3, document_id: str | None = None
) -> AnswerResponse:
    results = search_documents(store, query, top_k=top_k, document_id=document_id)
    sources = []
    characters = 0
    for result in results:
        if characters + len(result.text) > MAX_CONTEXT_CHARACTERS:
            continue
        sources.append(AnswerSource(source_id=f"S{len(sources) + 1}", **asdict(result)))
        characters += len(result.text)

    if not sources:
        return insufficient_context(query)

    generation = generate_answer(
        query, [{"source_id": source.source_id, "text": source.text} for source in sources]
    )
    if not generation.can_answer:
        return insufficient_context(query)

    available = {source.source_id: source for source in sources}
    selected_ids = list(dict.fromkeys(generation.source_ids))
    inline_ids = set(re.findall(r"\[(S\d+)\]", generation.answer))
    if (
        not generation.answer.strip()
        or len(generation.answer) > 8000
        or not selected_ids
        or any(source_id not in available for source_id in selected_ids)
        or not inline_ids.issubset(selected_ids)
    ):
        raise LLMResponseError("LLM returned an answer with invalid references or content")

    return AnswerResponse(
        query=query,
        status="answered",
        answer=generation.answer.strip(),
        sources=[available[source_id] for source_id in selected_ids],
    )
