import argparse
import json
import math
import platform
import subprocess
import time
from datetime import datetime, timezone
from hashlib import sha256
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.answers import answer_question
from app.chunking import chunk_text
from app.embeddings import MODEL_NAME as EMBEDDING_MODEL, split_passages
from app.llm import MODEL_NAME, SYSTEM_PROMPT, load_api_key
from app.storage import DocumentStore, StoredDocument

ROOT = Path(__file__).resolve().parents[1]


class DatasetDocument(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    id: str = Field(min_length=1)
    filename: str = Field(min_length=1)
    text: str = Field(min_length=1)


class Case(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    id: str = Field(min_length=1)
    query: str = Field(min_length=1, max_length=2000)
    expected_status: Literal["answered", "insufficient_context"]
    relevant_document_ids: list[str]
    reference_answer: str = Field(min_length=1)
    document_id: str | None = None


class Dataset(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    description: str
    documents: list[DatasetDocument] = Field(min_length=1)
    queries: list[Case] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_references(self):
        ids = {doc.id for doc in self.documents}
        if len(ids) != len(self.documents):
            raise ValueError("Duplicate document IDs")
        hashes = {sha256(doc.text.encode()).hexdigest() for doc in self.documents}
        if len(hashes) != len(self.documents):
            raise ValueError("Duplicate document contents")
        if len({case.id for case in self.queries}) != len(self.queries):
            raise ValueError("Duplicate query IDs")
        for case in self.queries:
            relevant = set(case.relevant_document_ids)
            if not relevant <= ids or (case.document_id is not None and case.document_id not in ids):
                raise ValueError("Unknown document reference")
            if bool(relevant) != (case.expected_status == "answered"):
                raise ValueError("Answerable cases require relevant documents; abstentions require none")
            if case.document_id is not None and not relevant <= {case.document_id}:
                raise ValueError("Relevant documents excluded by the filter")
        return self


def summarize(rows: list[dict]) -> dict:
    def average(values):
        return sum(values) / len(values) if values else None

    answerable = [row for row in rows if row["expected_status"] == "answered"]
    unanswerable = [row for row in rows if row["expected_status"] == "insufficient_context"]
    recall = []
    precision = []
    for row in answerable:
        expected = set(row["relevant_document_ids"])
        actual = set(row["cited_document_ids"])
        recall.append(len(expected & actual) / len(expected))
        precision.append(len(expected & actual) / len(actual) if actual else 0.0)
    latencies = sorted(row["latency_ms"] for row in rows)
    return {
        "case_count": len(rows),
        "error_count": sum(row["status"] == "error" for row in rows),
        "status_accuracy": average([row["status"] == row["expected_status"] for row in rows]),
        "answerable_answer_rate": average([row["status"] == "answered" for row in answerable]),
        "unanswerable_abstention_rate": average([row["status"] == "insufficient_context" for row in unanswerable]),
        "source_document_recall": average(recall),
        "source_document_precision": average(precision),
        "latency_p50_ms": latencies[math.ceil(len(latencies) * .50) - 1] if latencies else None,
        "latency_p95_ms": latencies[math.ceil(len(latencies) * .95) - 1] if latencies else None,
    }


def evaluate(dataset: Dataset, *, delay: float = 10.0) -> tuple[list[dict], float]:
    rows = []
    started = time.perf_counter()
    with TemporaryDirectory(prefix="rag-eval-") as directory:
        store = DocumentStore(Path(directory) / "documents.sqlite3")
        aliases = {}
        for doc in dataset.documents:
            document_id = sha256(doc.text.encode("utf-8")).hexdigest()
            aliases[document_id] = doc.id
            store.save(StoredDocument(document_id, doc.filename, split_passages(chunk_text(doc.text))))
        ids = {alias: document_id for document_id, alias in aliases.items()}
        setup_ms = round((time.perf_counter() - started) * 1000, 2)
        for index, case in enumerate(dataset.queries):
            if index and delay:
                time.sleep(delay)
            print(f"Evaluating {case.id} ({index + 1}/{len(dataset.queries)})...", flush=True)
            row = case.model_dump()
            row.update(status="error", answer=None, sources=[], cited_document_ids=[], error=None,
                       human_review={"correct": None, "supported_by_sources": None, "complete": None, "notes": ""})
            started = time.perf_counter()
            try:
                response = answer_question(store, case.query, top_k=5,
                                           document_id=ids.get(case.document_id))
                row.update(response.model_dump())
                row["cited_document_ids"] = sorted({aliases.get(source.document_id, "unknown") for source in response.sources})
            except Exception as error:
                row["error"] = type(error).__name__
            row["latency_ms"] = round((time.perf_counter() - started) * 1000, 2)
            rows.append(row)
    return rows, setup_ms


def provenance(dataset_bytes: bytes) -> dict:
    packages = {}
    for name in ("sentence-transformers", "torch", "transformers", "httpx", "fastapi", "pydantic"):
        try:
            packages[name] = version(name)
        except PackageNotFoundError:
            packages[name] = None
    try:
        revision = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT,
                                  capture_output=True, text=True, check=True).stdout.strip()
        dirty = bool(subprocess.run(["git", "status", "--porcelain"], cwd=ROOT,
                                    capture_output=True, text=True, check=True).stdout.strip())
    except (OSError, subprocess.CalledProcessError):
        revision, dirty = None, None
    return {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "generation_model": MODEL_NAME, "embedding_model": EMBEDDING_MODEL,
        "dataset_sha256": sha256(dataset_bytes).hexdigest(),
        "prompt_sha256": sha256(SYSTEM_PROMPT.encode()).hexdigest(),
        "git_revision": revision, "working_tree_dirty": dirty,
        "python": platform.python_version(), "platform": platform.platform(), "packages": packages,
        "top_k": 5, "model_revisions_pinned": False,
    }


def save_report(path: Path, report: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2, allow_nan=False)
        handle.write("\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate real RAG answers in an isolated temporary database.")
    parser.add_argument("--dataset", type=Path, default=ROOT / "evals/answers.json")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--delay", type=float, default=10.0, help="Seconds between requests (default: 10)")
    args = parser.parse_args()
    if not math.isfinite(args.delay) or args.delay < 0:
        parser.error("--delay must be finite and nonnegative")
    output = args.output or ROOT / "evals/results" / f"answers_{datetime.now(timezone.utc):%Y%m%dT%H%M%S%fZ}.json"
    if output.exists():
        parser.error("Output already exists; choose a new filename")
    try:
        data = args.dataset.read_bytes()
        dataset = Dataset.model_validate_json(data)
        load_api_key()
        rows, setup_ms = evaluate(dataset, delay=args.delay)
        report = {"dataset": dataset.name, "execution": "real_models", "metadata": provenance(data),
                  "setup_ms": setup_ms, "delay_seconds": args.delay, "metrics": summarize(rows), "cases": rows}
        save_report(output, report)
    except Exception as error:
        print(f"Evaluation could not finish: {type(error).__name__}. No credentials are printed.")
        return 1
    print(json.dumps(report["metrics"], indent=2))
    print(f"Report: {output.resolve()}")
    print("Review the answers and cited passages before filling in human_review.")
    return int(report["metrics"]["error_count"] > 0)


if __name__ == "__main__":
    raise SystemExit(main())
