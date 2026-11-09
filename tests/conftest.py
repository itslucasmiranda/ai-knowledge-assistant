import pytest

from app.main import app, get_store
from app.storage import DocumentStore


@pytest.fixture(autouse=True)
def isolated_store(tmp_path):
    store = DocumentStore(tmp_path / "documents.sqlite3")
    app.dependency_overrides[get_store] = lambda: store

    try:
        yield store
    finally:
        app.dependency_overrides.pop(get_store, None)