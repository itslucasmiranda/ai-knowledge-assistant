import sqlite3
from collections.abc import Iterator
from contextlib import closing, contextmanager
from dataclasses import dataclass
from pathlib import Path

@dataclass(frozen=True)
class StoredChunk:
    document_id: str
    filename: str
    index: int
    text: str

@dataclass
class StoredDocument:
    document_id: str
    filename: str
    chunks: list[str]


class DocumentStore:
    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        with self._connect() as connection:
            connection.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    document_id TEXT PRIMARY KEY NOT NULL,
                    filename TEXT NOT NULL
                )
            """)
            connection.execute("""
                CREATE TABLE IF NOT EXISTS chunks (
                    document_id TEXT NOT NULL,
                    chunk_index INTEGER NOT NULL,
                    text TEXT NOT NULL,
                    PRIMARY KEY (document_id, chunk_index),
                    FOREIGN KEY (document_id)
                        REFERENCES documents(document_id)
                )
            """)

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        with closing(sqlite3.connect(
            self.db_path,
            autocommit=sqlite3.LEGACY_TRANSACTION_CONTROL,
        )) as connection:
            connection.execute("PRAGMA foreign_keys = ON")
            with connection:
                yield connection

    def save(self, document: StoredDocument) -> bool:
        if not document.document_id.strip() or not document.filename.strip():
            raise ValueError("Document ID and filename must not be empty")

        if not document.chunks or any(not text.strip() for text in document.chunks):
            raise ValueError("Document must contain non-empty chunks")

        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO documents (document_id, filename)
                VALUES (?, ?)
                ON CONFLICT(document_id) DO NOTHING
                """,
                (document.document_id, document.filename),
            )

            if cursor.rowcount == 0:
                return False

            connection.executemany(
                """
                INSERT INTO chunks (document_id, chunk_index, text)
                VALUES (?, ?, ?)
                """,
                [
                    (document.document_id, index, text)
                    for index, text in enumerate(document.chunks)
                ],
            )

        return True

    def get(self, document_id: str) -> StoredDocument | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT filename FROM documents WHERE document_id = ?",
                (document_id,),
            ).fetchone()

            if row is None:
                return None

            chunks = connection.execute(
                """
                SELECT text FROM chunks
                WHERE document_id = ?
                ORDER BY chunk_index
                """,
                (document_id,),
            ).fetchall()

        return StoredDocument(document_id, row[0], [chunk[0] for chunk in chunks])

    def list_chunks(self, document_id: str | None = None) -> list[StoredChunk]:
        query = """
            SELECT c.document_id, d.filename, c.chunk_index, c.text
            FROM chunks AS c
            JOIN documents AS d ON d.document_id = c.document_id
        """
        parameters: tuple[str, ...] = ()

        if document_id is not None:
            query += " WHERE c.document_id = ?"
            parameters = (document_id,)

        query += " ORDER BY c.document_id, c.chunk_index"

        with self._connect() as connection:
            rows = connection.execute(query, parameters).fetchall()

        return [
            StoredChunk(
                document_id=row[0],
                filename=row[1],
                index=row[2],
                text=row[3],
            )
            for row in rows
        ]