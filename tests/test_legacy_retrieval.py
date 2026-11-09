import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

from app import embeddings, retrieval
from app.storage import DocumentStore, StoredDocument


class LegacyRetrievalTests(unittest.TestCase):
    def setUp(self):
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.store = DocumentStore(Path(directory.name) / "documents.sqlite3")
        self.store.save(
            StoredDocument("legacy", "antigo.txt", ["abcdefghijklmnopqr"])
        )
        self.store.save(
            StoredDocument("short", "curto.txt", ["curto"])
        )

        self.model = Mock()
        self.model.max_seq_length = 20

        def tokenize(text, *, add_special_tokens, truncation):
            self.assertTrue(add_special_tokens)
            self.assertFalse(truncation)
            return {"input_ids": [0] * (len(text) + 2)}

        self.model.tokenizer.side_effect = tokenize
        self.enterContext(
            patch.object(embeddings, "get_model", return_value=self.model)
        )
        self.enterContext(
            patch.object(retrieval, "embed_query", return_value=[1.0, 0.0])
        )

        self.scores = {
            "abcdefghi": 0.2,
            "jklmnopqr": 0.9,
            "curto": 0.8,
        }

        def encode(texts):
            for text in texts:
                self.assertLessEqual(len("passage: " + text) + 2, 20)
            return [[self.scores[text], 0.0] for text in texts]

        self.encoder = self.enterContext(
            patch.object(retrieval, "embed_passages", side_effect=encode)
        )

    def test_best_part_preserves_source_and_database(self):
        results = retrieval.search_documents(self.store, "Onde?", top_k=3)

        self.assertEqual(
            [(result.document_id, result.text) for result in results],
            [("legacy", "jklmnopqr"), ("short", "curto")],
        )
        self.assertEqual(results[0].filename, "antigo.txt")
        self.assertEqual(results[0].chunk_index, 0)
        self.assertAlmostEqual(results[0].score, 0.9)

        reopened = DocumentStore(self.store.db_path)
        self.assertEqual(
            reopened.get("legacy").chunks,
            ["abcdefghijklmnopqr"],
        )

    def test_document_filter_runs_before_splitting(self):
        results = retrieval.search_documents(
            self.store, "Onde?", document_id="short"
        )

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].document_id, "short")
        self.encoder.assert_called_once_with(["curto"])
        self.model.tokenizer.assert_called_once_with(
            "passage: curto",
            add_special_tokens=True,
            truncation=False,
        )

    def test_equal_scores_keep_first_part(self):
        self.scores["abcdefghi"] = 0.9

        results = retrieval.search_documents(
            self.store, "Onde?", document_id="legacy"
        )

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].text, "abcdefghi")

    def test_tokenizer_failure_is_not_hidden(self):
        self.model.tokenizer.side_effect = RuntimeError("Tokenizer failed")

        with self.assertRaisesRegex(RuntimeError, "Tokenizer failed"):
            retrieval.search_documents(self.store, "Onde?")

        self.encoder.assert_not_called()

