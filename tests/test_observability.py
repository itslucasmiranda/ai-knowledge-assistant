import json
import logging

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.observability import record_request


def test_request_logs_use_route_template_without_private_data(caplog):
    app = FastAPI()
    app.middleware("http")(record_request)

    @app.post("/documents/{document_id}")
    def document(document_id: str):
        return {"ok": True}

    with caplog.at_level(logging.INFO, logger="uvicorn.error"):
        with TestClient(app) as client:
            response = client.post("/documents/private-id?secret=private-query", json={"text": "private-body"},
                                   headers={"Authorization": "Bearer private-key"})
            other = client.post("/documents/another-id")
    records = [json.loads(record.message) for record in caplog.records if record.name == "uvicorn.error"]
    assert len(records) == 2
    assert records[0]["route"] == "/documents/{document_id}"
    assert records[0]["status"] == 200
    assert records[0]["request_id"] == response.headers["X-Request-ID"]
    assert response.headers["X-Request-ID"] != other.headers["X-Request-ID"]
    assert float(response.headers["X-Process-Time-Ms"]) >= 0
    assert "private-" not in json.dumps(records)


def test_unhandled_failure_is_recorded_without_exception_message(caplog):
    app = FastAPI()
    app.middleware("http")(record_request)

    @app.get("/failure")
    def failure():
        raise RuntimeError("private-message")

    with caplog.at_level(logging.INFO, logger="uvicorn.error"):
        with TestClient(app, raise_server_exceptions=False) as client:
            assert client.get("/failure").status_code == 500
    records = [json.loads(record.message) for record in caplog.records if record.name == "uvicorn.error"]
    assert records[0]["status"] == 500
    assert "private-message" not in json.dumps(records)
