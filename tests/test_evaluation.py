import unittest

from scripts.evaluate_retrieval import score_ranking, summarize


class EvaluationTests(unittest.TestCase):
    def test_first_position(self):
        self.assertEqual(score_ranking(["a", "b"], ["a"]), {
            "hit_at_1": 1,
            "hit_at_3": 1,
            "reciprocal_rank_at_3": 1.0,
        })

    def test_second_position(self):
        self.assertEqual(score_ranking(["b", "a"], ["a"]), {
            "hit_at_1": 0,
            "hit_at_3": 1,
            "reciprocal_rank_at_3": 0.5,
        })

    def test_third_position(self):
        result = score_ranking(["b", "c", "a"], ["a"])
        self.assertEqual(result["hit_at_3"], 1)
        self.assertAlmostEqual(result["reciprocal_rank_at_3"], 1 / 3)

    def test_fourth_position_is_outside_cutoff(self):
        self.assertEqual(score_ranking(["b", "c", "d", "a"], ["a"]), {
            "hit_at_1": 0,
            "hit_at_3": 0,
            "reciprocal_rank_at_3": 0.0,
        })

    def test_empty_ranking(self):
        self.assertEqual(score_ranking([], ["a"])["hit_at_3"], 0)

    def test_first_relevant_document_is_used(self):
        result = score_ranking(["c", "b", "a"], ["a", "b"])
        self.assertEqual(result["reciprocal_rank_at_3"], 0.5)

    def test_empty_labels_are_rejected(self):
        with self.assertRaises(ValueError):
            score_ranking(["a"], [])

    def test_summary_includes_misses(self):
        rows = [
            score_ranking(["a"], ["a"]),
            score_ranking(["b", "a"], ["a"]),
            score_ranking(["b"], ["a"]),
        ]

        result = summarize(rows)

        self.assertAlmostEqual(result["hit_at_1"], 1 / 3)
        self.assertAlmostEqual(result["hit_at_3"], 2 / 3)
        self.assertEqual(result["mrr_at_3"], 0.5)

    def test_empty_summary_is_rejected(self):
        with self.assertRaises(ValueError):
            summarize([])