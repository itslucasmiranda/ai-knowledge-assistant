import json
import platform
from datetime import datetime, timezone
from hashlib import sha256
from importlib.metadata import version
from pathlib import Path
from tempfile import TemporaryDirectory


ROOT = Path(__file__).resolve().parents[1]


def score_ranking(ranked_ids: list[str], relevant_ids: list[str]) -> dict:
    if not relevant_ids:
        raise ValueError("Relevant document IDs must not be empty")

    relevant = set(relevant_ids)
    rank = next(
        (i for i, doc_id in enumerate(ranked_ids[:3], 1) if doc_id in relevant),
        None,
    )

    return {
        "hit_at_1": int(rank == 1),
        "hit_at_3": int(rank is not None),
        "reciprocal_rank_at_3": 1.0 / rank if rank is not None else 0.0,
    }


def summarize(rows: list[dict]) -> dict:
    if not rows:
        raise ValueError("Evaluation must contain queries")

    return {
        "hit_at_1": sum(row["hit_at_1"] for row in rows) / len(rows),
        "hit_at_3": sum(row["hit_at_3"] for row in rows) / len(rows),
        "mrr_at_3": sum(row["reciprocal_rank_at_3"] for row in rows) / len(rows),
    }


def main() -> None:
    from app.chunking import chunk_text
    from app.embeddings import MODEL_NAME
    from app.retrieval import search_documents
    from app.storage import DocumentStore, StoredDocument

    dataset_path = ROOT / "evals" / "retrieval.json"
    raw = dataset_path.read_bytes()
    dataset = json.loads(raw.decode("utf-8-sig"))
    documents = dataset["documents"]
    queries = dataset["queries"]

    if not documents or not queries:
        raise ValueError("Documents and queries must not be empty")

    for items in (documents, queries):
        if len({item["id"] for item in items}) != len(items):
            raise ValueError("Duplicate dataset IDs")

    known_ids = {doc["id"] for doc in documents}

    for query in queries:
        relevant = query["relevant_document_ids"]
        if not relevant or not set(relevant) <= known_ids:
            raise ValueError(f"Invalid relevance labels: {query['id']}")
        if not query["query"].strip():
            raise ValueError(f"Empty query: {query['id']}")

    rows = []

    with TemporaryDirectory() as directory:
        store = DocumentStore(Path(directory) / "evaluation.sqlite3")
        aliases = {}

        for doc in documents:
            chunks = chunk_text(doc["text"])

            if len(chunks) != 1:
                raise ValueError("This evaluation requires one chunk per document")

            document_id = sha256(doc["text"].encode("utf-8")).hexdigest()

            if document_id in aliases:
                raise ValueError("Duplicate document contents")

            aliases[document_id] = doc["id"]
            store.save(StoredDocument(document_id, doc["filename"], chunks))

        for query in queries:
            print(f"Evaluating {query['id']}...", flush=True)

            results = search_documents(store, query["query"], top_k=3)
            ranked_ids = [aliases[result.document_id] for result in results]
            metrics = score_ranking(ranked_ids, query["relevant_document_ids"])

            rows.append({
                "id": query["id"],
                "query": query["query"],
                "relevant_document_ids": query["relevant_document_ids"],
                "results": [
                    {
                        "id": aliases[result.document_id],
                        "filename": result.filename,
                        "chunk_index": result.chunk_index,
                        "score": result.score,
                    }
                    for result in results
                ],
                **metrics,
            })

    metrics = summarize(rows)

    report = {
        "dataset": dataset["name"],
        "dataset_sha256": sha256(raw).hexdigest(),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "model": MODEL_NAME,
        "device": "cpu",
        "python": platform.python_version(),
        "packages": {
            name: version(name)
            for name in ("sentence-transformers", "transformers", "torch")
        },
        "document_count": len(documents),
        "query_count": len(rows),
        "top_k": 3,
        "metrics": metrics,
        "queries": rows,
    }

    output = ROOT / "evals" / "results" / "retrieval_baseline.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(json.dumps(metrics, indent=2))
    print(f"Report: {output}")


if __name__ == "__main__":
    main()