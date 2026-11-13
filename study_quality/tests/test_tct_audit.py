"""Synthetic tests only. Real study notes and exam questions stay off GitHub."""
import copy
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tct_audit import audit  # noqa: E402

FIXTURE = Path(__file__).resolve().parents[1] / "examples" / "fictional_weather.json"


def fixture():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def codes(data):
    return {finding["code"] for finding in audit(data)["findings"]}


class TctAuditTests(unittest.TestCase):
    def test_synthetic_example_passes(self):
        report = audit(fixture())
        self.assertTrue(report["ok"], report["findings"])
        self.assertEqual(report["summary"]["covered_options"], 3)

    def test_missing_option_mapping_fails(self):
        data = fixture()
        data["questions"][0]["options"][1]["taught_by"] = []
        self.assertIn("UNTaught_OPTION", codes(data))

    def test_missing_explicit_conclusion_fails(self):
        data = fixture()
        data["lesson"]["claims"][0]["decision"] = "yes"
        self.assertIn("CLAIM_DECISION", codes(data))

    def test_missing_mechanism_fails(self):
        data = fixture()
        data["lesson"]["claims"][1]["why"] = "because"
        self.assertIn("CLAIM_WHY", codes(data))

    def test_wrong_anchor_fails(self):
        data = fixture()
        data["lesson"]["claims"][0]["anchor"] = "this sentence does not occur in the learner lesson"
        self.assertIn("CLAIM_ANCHOR", codes(data))

    def test_unknown_claim_fails(self):
        data = fixture()
        data["questions"][0]["options"][2]["taught_by"] = ["not-there"]
        self.assertIn("UNKNOWN_CLAIM", codes(data))

    def test_teaching_cannot_mention_option_letters(self):
        data = fixture()
        data["lesson"]["blocks"][0]["text"] += " The answer is A."
        self.assertIn("QUESTION_LEAK", codes(data))

    def test_teaching_cannot_mention_question_numbers(self):
        data = fixture()
        data["lesson"]["blocks"][0]["text"] += " Question 1 will ask this."
        self.assertIn("QUESTION_LEAK", codes(data))

    def test_pretest_does_not_reveal_answers(self):
        data = fixture()
        data["phases"]["pretest_answer_text"] = "A"
        self.assertIn("PRETEST_ANSWER_LEAK", codes(data))

    def test_exam_phase_covers_entire_original_bank(self):
        data = fixture()
        data["phases"]["exam_question_ids"] = []
        self.assertIn("EXAM_INCOMPLETE", codes(data))

    def test_duplicate_option_label_fails(self):
        data = fixture()
        data["questions"][0]["options"][1]["label"] = "A"
        self.assertIn("OPTION_LABEL", codes(data))

    def test_wrong_answer_key_fails(self):
        data = fixture()
        data["questions"][0]["answer_labels"] = ["D"]
        self.assertIn("ANSWER_KEY", codes(data))

    def test_orphan_claim_fails(self):
        data = fixture()
        data["questions"][0]["options"][2]["taught_by"] = ["c-pressure"]
        self.assertIn("ORPHAN_CLAIM", codes(data))

    def test_no_private_text_in_report(self):
        data = fixture()
        data["questions"][0]["stem"] = "private-question-content-should-not-appear"
        data["lesson"]["claims"][0]["why"] = "x"
        report = json.dumps(audit(data))
        self.assertNotIn("private-question-content-should-not-appear", report)
        self.assertNotIn("Atmospheric pressure is measured", report)

    def test_invalid_root_returns_finding(self):
        report = audit(None)
        self.assertFalse(report["ok"])
        self.assertEqual(report["findings"][0]["code"], "INVALID_ROOT")

    def test_no_mutation(self):
        data = fixture()
        before = copy.deepcopy(data)
        audit(data)
        self.assertEqual(data, before)


if __name__ == "__main__":
    unittest.main()