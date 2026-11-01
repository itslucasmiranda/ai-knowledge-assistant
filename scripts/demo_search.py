from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory

from app.chunking import chunk_text
from app.retrieval import search_documents
from app.storage import DocumentStore, StoredDocument


DOCUMENTS = {
    "armazenamento.txt": (
        "Os documentos enviados ficam armazenados em um banco SQLite. "
        "Os dados permanecem disponiveis depois de reiniciar a aplicacao."
    ),
    "acesso.txt": (
        "Para recuperar sua senha, clique em Esqueci minha senha. "
        "Um link de redefinicao sera enviado para seu email cadastrado."
    ),
    "receita.txt": (
        "Para preparar um bolo, misture farinha, ovos, leite e acucar. "
        "Coloque a massa em uma forma e leve ao forno."
    ),
}

QUERIES = [
    "Onde ficam salvos os documentos?",
    "Como recuperar o acesso se eu esquecer minha senha?",
]


def main() -> None:
    with TemporaryDirectory() as directory:
        store = DocumentStore(Path(directory) / "demo.sqlite3")

        for filename, text in DOCUMENTS.items():
            store.save(
                StoredDocument(
                    document_id=sha256(text.encode("utf-8")).hexdigest(),
                    filename=filename,
                    chunks=chunk_text(text),
                )
            )

        for query in QUERIES:
            print(f"\nPergunta: {query}")
            results = search_documents(store, query, top_k=3)

            for position, result in enumerate(results, start=1):
                print(
                    f"{position}. {result.filename} | "
                    f"trecho {result.chunk_index} | "
                    f"similaridade {result.score:.4f}"
                )
                print(f"   {result.text}")


if __name__ == "__main__":
    main()