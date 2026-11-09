import unittest

from app.token_chunking import split_to_token_limit


class TokenChunkingTests(unittest.TestCase):
    def test_short_text_is_unchanged(self):
        self.assertEqual(
            split_to_token_limit(" Olá mundo. ", len, 30),
            ["Olá mundo."],
        )

    def test_exact_limit_is_accepted(self):
        self.assertEqual(
            split_to_token_limit("abc", len, 12),
            ["abc"],
        )

    def test_prefix_counts_toward_limit(self):
        chunks = split_to_token_limit("abcdef", len, 12)

        self.assertGreater(len(chunks), 1)
        self.assertEqual("".join(chunks), "abcdef")
        self.assertTrue(
            all(len("passage: " + part) <= 12 for part in chunks)
        )

    def test_special_tokens_count_toward_limit(self):
        def count_tokens(text):
            return len(text) + 2

        chunks = split_to_token_limit(
            "abcdefgh",
            count_tokens,
            14,
        )

        self.assertEqual("".join(chunks), "abcdefgh")
        self.assertTrue(
            all(
                count_tokens("passage: " + part) <= 14
                for part in chunks
            )
        )

    def test_word_boundaries_and_order_are_preserved(self):
        text = "um dois três quatro cinco seis"
        chunks = split_to_token_limit(text, len, 22)

        self.assertEqual(" ".join(chunks), text)
        self.assertTrue(
            all(len("passage: " + part) <= 22 for part in chunks)
        )

    def test_long_unicode_word_is_not_lost(self):
        text = "á漢🙂" * 1000
        chunks = split_to_token_limit(text, len, 40)

        self.assertEqual("".join(chunks), text)
        self.assertTrue(
            all(
                part and len("passage: " + part) <= 40
                for part in chunks
            )
        )

    def test_invalid_inputs_are_rejected(self):
        for limit in (0, -1, True, 1.5):
            with self.subTest(limit=limit):
                with self.assertRaises(ValueError):
                    split_to_token_limit("abc", len, limit)

        with self.assertRaises(ValueError):
            split_to_token_limit(" \n\t", len, 20)

    def test_impossible_budget_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "single character"):
            split_to_token_limit("a", len, 9)
