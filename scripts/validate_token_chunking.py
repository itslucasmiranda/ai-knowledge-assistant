from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory

from fastapi.testclient import TestClient

from app.embeddings import MODEL_NAME, get_model
from app.main import app, get_store
from app.storage import DocumentStore, StoredDocument


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def main() -> None:
    print(f"Carregando o modelo real: {MODEL_NAME}", flush=True)
    model = get_model()
    limit = min(512, model.max_seq_length)

    def token_count(text: str) -> int:
        return len(
            model.tokenizer(
                "passage: " + text,
                add_special_tokens=True,
                truncation=False,
            )["input_ids"]
        )

    text = (
        "Os documentos enviados ficam armazenados no SQLite. "
        + "armazenamento" * 600
    )
    original_tokens = token_count(text)
    require(original_tokens > limit, "O texto precisa exceder o limite.")

    with TemporaryDirectory(prefix="token-chunking-") as directory:
        store = DocumentStore(Path(directory) / "documents.sqlite3")
        missing = object()
        previous = app.dependency_overrides.get(get_store, missing)
        app.dependency_overrides[get_store] = lambda: store

        try:
            with TestClient(app) as client:
                print("Validando upload e persistencia...", flush=True)
                content = text.encode("utf-8")
                upload = client.post(
                    "/documents",
                    files={"file": ("tokens.txt", content, "text/plain")},
                )
                upload.raise_for_status()
                document = upload.json()
                chunks = [item["text"] for item in document["chunks"]]

                require(len(chunks) > 1, "O upload nao dividiu o texto.")
                require(
                    document["document_id"] == sha256(content).hexdigest(),
                    "O identificador do upload mudou.",
                )
                require(
                    "".join("".join(chunks).split()) == "".join(text.split()),
                    "O conteudo perdeu caracteres durante a divisao.",
                )
                largest_chunk = max(token_count(chunk) for chunk in chunks)
                require(largest_chunk <= limit, "Um trecho excedeu o limite.")

                saved = DocumentStore(store.db_path).get(document["document_id"])
                require(saved is not None, "O documento nao foi persistido.")
                require(saved.chunks == chunks, "Os trechos salvos diferem do upload.")

                legacy_text = "Documento antigo. " + text
                legacy_id = sha256(legacy_text.encode("utf-8")).hexdigest()
                store.save(
                    StoredDocument(legacy_id, "legado.txt", [legacy_text])
                )
                require(
                    token_count(legacy_text) > limit,
                    "O documento antigo precisa exceder o limite.",
                )

                for label, document_id in [
                    ("novo", document["document_id"]),
                    ("antigo", legacy_id),
                ]:
                    print(f"Validando busca no documento {label}...", flush=True)
                    response = client.post(
                        "/search",
                        json={
                            "query": "Onde ficam armazenados os documentos?",
                            "top_k": 3,
                            "document_id": document_id,
                        },
                    )
                    response.raise_for_status()
                    body = response.json()
                    results = body["results"]
                    require(bool(results), f"Busca vazia no documento {label}.")
                    require(body["result_count"] == len(results), "Contagem incorreta.")

                    for result in results:
                        require(result["document_id"] == document_id, "Fonte incorreta.")
                        require(token_count(result["text"]) <= limit, "Resultado longo.")

                    if label == "antigo":
                        require(len(results) == 1, "O trecho antigo gerou duplicatas.")
                        require(results[0]["chunk_index"] == 0, "Indice de origem alterado.")
                        require(results[0]["filename"] == "legado.txt", "Nome alterado.")
                        require(results[0]["text"] in legacy_text, "Texto fora da fonte.")

                original = DocumentStore(store.db_path).get(legacy_id)
                require(original is not None, "O documento antigo desapareceu.")
                require(original.chunks == [legacy_text], "O banco antigo foi alterado.")

                print(f"Tokens do texto original: {original_tokens}")
                print(f"Limite efetivo: {limit}")
                print(f"Trechos gerados no upload: {len(chunks)}")
                print(f"Maior trecho, incluindo prefixo e tokens especiais: {largest_chunk}")
                print("OK: upload, persistencia e busca com modelo real.")
                print("OK: documento antigo preservado; banco temporario utilizado.")
        finally:
            if previous is missing:
                app.dependency_overrides.pop(get_store, None)
            else:
                app.dependency_overrides[get_store] = previous


if __name__ == "__main__":
    main()
