import json
from copy import deepcopy
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.answers import AnswerResponse, AnswerSource, insufficient_context
from scripts import evaluate_answers as evaluation


def dataset():
    return evaluation.Dataset.model_validate_json((evaluation.ROOT / "evals/answers.json").read_bytes())


def row(expected, status, relevant=(), cited=(), latency=10):
    return dict(expected_status=expected, status=status, relevant_document_ids=list(relevant),
                cited_document_ids=list(cited), latency_ms=latency)


def test_metrics_include_errors_and_missing_answers_in_denominators():
    rows = [row("answered", "answered", ["a", "b"], ["a", "c"], 10),
            row("answered", "error", ["a"], [], 20),
            row("insufficient_context", "insufficient_context", latency=30),
            row("insufficient_context", "error", latency=40)]
    metrics = evaluation.summarize(rows)
    assert metrics == dict(case_count=4, error_count=2, status_accuracy=.5,
                          answerable_answer_rate=.5, unanswerable_abstention_rate=.5,
                          source_document_recall=.25, source_document_precision=.25,
                          latency_p50_ms=20, latency_p95_ms=40)


def test_metrics_do_not_invent_scores_for_empty_groups():
    metrics = evaluation.summarize([])
    assert metrics["case_count"] == metrics["error_count"] == 0
    assert all(value is None for key, value in metrics.items() if key not in {"case_count", "error_count"})
    assert evaluation.summarize([row("insufficient_context", "insufficient_context")])["source_document_recall"] is None


@pytest.mark.parametrize("change", [
    lambda d: d["documents"].append(d["documents"][0]),
    lambda d: d["documents"][1].update(text=d["documents"][0]["text"]),
    lambda d: d["queries"].append(d["queries"][0]),
    lambda d: d["queries"][0].update(relevant_document_ids=["missing"]),
    lambda d: d["queries"][0].update(document_id="missing"),
    lambda d: d["queries"][0].update(document_id="support"),
    lambda d: d["queries"][0].update(relevant_document_ids=[]),
    lambda d: d["queries"][8].update(relevant_document_ids=["storage"]),
    lambda d: d["queries"][0].update(query="   "),
    lambda d: d.update(queries=[]),
])
def test_invalid_datasets_are_rejected_before_execution(change):
    data = deepcopy(dataset().model_dump())
    change(data)
    with pytest.raises(ValidationError):
        evaluation.Dataset.model_validate(data)


def test_evaluation_is_isolated_maps_sources_and_keeps_error_cases(monkeypatch):
    data = dataset()
    data.queries = [data.queries[0], data.queries[8], data.queries[9]]
    data.queries[0].document_id = "storage"
    paths = []

    def answer(store, query, top_k, document_id):
        paths.append(store.db_path)
        assert top_k == 5
        if query == data.queries[0].query:
            doc = store.get(document_id)
            assert doc.filename == "armazenamento.txt"
            return AnswerResponse(query=query, status="answered", answer="SQLite.", sources=[
                AnswerSource(source_id="S1", document_id=document_id, filename=doc.filename,
                             chunk_index=0, text=doc.chunks[0], score=.9)])
        if query == data.queries[1].query:
            return insufficient_context(query)
        raise RuntimeError("PRIVATE credential or provider body")

    monkeypatch.setattr(evaluation, "answer_question", answer)
    monkeypatch.setattr(evaluation.time, "sleep", lambda _: pytest.fail("No delay requested"))
    rows, setup_ms = evaluation.evaluate(data, delay=0)
    assert setup_ms >= 0
    assert len(rows) == 3
    assert rows[0]["cited_document_ids"] == ["storage"]
    assert rows[1]["status"] == "insufficient_context"
    assert rows[2]["error"] == "RuntimeError"
    assert "PRIVATE" not in json.dumps(rows)
    assert all(not path.exists() for path in paths)
    assert rows[0]["human_review"]["supported_by_sources"] is None
    assert rows[0]["reference_answer"] == data.queries[0].reference_answer


def test_report_never_overwrites_previous_evidence(tmp_path):
    output = tmp_path / "results" / "report.json"
    evaluation.save_report(output, {"answer": "Não sei."})
    with pytest.raises(FileExistsError):
        evaluation.save_report(output, {"answer": "Changed"})
    assert json.loads(output.read_text()) == {"answer": "Não sei."}
