import json

from scripts.evaluate_answers import Dataset, ROOT, evaluate
from app.llm import load_api_key


def main() -> int:
    try:
        load_api_key()
        dataset = Dataset.model_validate_json((ROOT / "evals/answers.json").read_bytes())
        dataset.queries = [dataset.queries[0], dataset.queries[8]]
        rows, _ = evaluate(dataset)
    except Exception as error:
        print(f"Demo could not finish: {type(error).__name__}")
        return 1
    for row in rows:
        print(json.dumps({key: row[key] for key in ("query", "status", "answer", "sources", "error")}, ensure_ascii=False, indent=2))
    return int(any(row["status"] != row["expected_status"] for row in rows))


if __name__ == "__main__":
    raise SystemExit(main())
