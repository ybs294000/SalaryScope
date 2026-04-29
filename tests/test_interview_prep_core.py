import json
import os
import shutil
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def _cache_data(*args, **kwargs):
    def decorator(func):
        return func
    return decorator


fake_streamlit = types.SimpleNamespace(
    cache_data=_cache_data,
    session_state={},
    fragment=lambda *args, **kwargs: (lambda func: func),
)
sys.modules["streamlit"] = fake_streamlit

from app.interview_aptitude_prep import loader
from app.interview_aptitude_prep.scoring import score_question_set
from app.interview_aptitude_prep.timer import build_attempt, finalize_attempt, format_duration
from app.interview_aptitude_prep.validator import (
    validate_question_set_payload,
    validate_registry_payload,
)


def _workspace_temp_dir(name: str) -> Path:
    root = Path(__file__).resolve().parent / "_tmp"
    root.mkdir(exist_ok=True)
    target = root / name
    if target.exists():
        shutil.rmtree(target, ignore_errors=True)
    target.mkdir(parents=True, exist_ok=True)
    return target


class TestInterviewPrepValidator(unittest.TestCase):

    def test_registry_duplicate_set_ids_are_rejected(self):
        payload = {
            "sets": [
                {"set_id": "dup", "title": "Set A", "file": "sample_sets/a.json"},
                {"set_id": "dup", "title": "Set B", "file": "sample_sets/b.json"},
            ]
        }
        base_dir = _workspace_temp_dir("validator_duplicate_ids")
        try:
            (base_dir / "sample_sets").mkdir()
            (base_dir / "sample_sets" / "a.json").write_text("{}", encoding="utf-8")
            (base_dir / "sample_sets" / "b.json").write_text("{}", encoding="utf-8")
            errors, warnings, entries = validate_registry_payload(payload, base_dir)
        finally:
            shutil.rmtree(base_dir, ignore_errors=True)

        self.assertTrue(any("duplicate set_id" in err.lower() for err in errors))
        self.assertEqual(warnings, [])
        self.assertEqual(len(entries), 1)

    def test_question_set_normalizes_true_false_options(self):
        payload = {
            "set_id": "tf_set",
            "title": "True False Set",
            "sections": [
                {
                    "title": "Basics",
                    "questions": [
                        {
                            "id": "q1",
                            "type": "true_false",
                            "prompt": "Python is a programming language.",
                            "correct_answer": "true",
                        }
                    ],
                }
            ],
        }

        errors, warnings, normalized = validate_question_set_payload(payload)

        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])
        options = normalized["sections"][0]["questions"][0]["options"]
        self.assertEqual(options, [{"id": "true", "label": "True"}, {"id": "false", "label": "False"}])
        self.assertEqual(normalized["question_count"], 1)


class TestInterviewPrepScoring(unittest.TestCase):

    def test_score_question_set_tracks_correct_incorrect_and_skipped(self):
        question_set = {
            "set_id": "score_set",
            "title": "Scoring Set",
            "scoring": {"pass_percent": 60},
            "sections": [
                {
                    "id": "sec1",
                    "title": "Section 1",
                    "questions": [
                        {
                            "id": "q1",
                            "type": "single_choice",
                            "prompt": "Pick A",
                            "options": [{"id": "a", "label": "A"}, {"id": "b", "label": "B"}],
                            "correct_answer": "a",
                            "marks": 2,
                            "negative_marks": 0.5,
                            "section_id": "sec1",
                            "section_title": "Section 1",
                        },
                        {
                            "id": "q2",
                            "type": "numeric_input",
                            "prompt": "2 + 2",
                            "accepted_answers": [4],
                            "tolerance": 0.0,
                            "marks": 1,
                            "negative_marks": 0.25,
                            "section_id": "sec1",
                            "section_title": "Section 1",
                        },
                        {
                            "id": "q3",
                            "type": "text_input",
                            "prompt": "Leave blank",
                            "accepted_answers": ["anything"],
                            "marks": 1,
                            "negative_marks": 0.0,
                            "section_id": "sec1",
                            "section_title": "Section 1",
                        },
                    ],
                }
            ],
        }
        answers = {"q1": "a", "q2": "5", "q3": ""}
        attempt = finalize_attempt(build_attempt(question_set, timed_mode=False))

        result = score_question_set(question_set, answers, attempt)

        self.assertEqual(result["correct_count"], 1)
        self.assertEqual(result["incorrect_count"], 1)
        self.assertEqual(result["skipped_count"], 1)
        self.assertAlmostEqual(result["total_marks"], 4.0)
        self.assertAlmostEqual(result["total_obtained"], 1.75)
        self.assertAlmostEqual(result["percentage"], 43.75)
        self.assertEqual(result["timer_snapshot"]["timer_enabled"], False)

    def test_format_duration_outputs_readable_values(self):
        self.assertEqual(format_duration(None), "Untimed")
        self.assertEqual(format_duration(65), "01:05")
        self.assertEqual(format_duration(3661), "01:01:01")


class TestInterviewPrepLoader(unittest.TestCase):

    def test_loader_surfaces_question_count_mismatch_warning(self):
        registry_payload = {
            "sets": [
                {
                    "set_id": "sample_set",
                    "title": "Sample Set",
                    "file": "sample_sets/sample.json",
                    "question_count": 99,
                }
            ]
        }
        question_set_payload = {
            "set_id": "sample_set",
            "title": "Sample Set",
            "sections": [
                {
                    "title": "Section A",
                    "questions": [
                        {
                            "id": "q1",
                            "type": "single_choice",
                            "prompt": "Pick A",
                            "options": [{"id": "a", "label": "A"}, {"id": "b", "label": "B"}],
                            "correct_answer": "a",
                        }
                    ],
                }
            ],
        }

        base_dir = _workspace_temp_dir("loader_question_count_mismatch")
        try:
            sample_dir = base_dir / "sample_sets"
            sample_dir.mkdir()
            registry_path = base_dir / "registry_ia.json"
            question_path = sample_dir / "sample.json"
            registry_path.write_text(json.dumps(registry_payload), encoding="utf-8")
            question_path.write_text(json.dumps(question_set_payload), encoding="utf-8")

            with patch.object(loader, "BASE_DIR", base_dir), patch.object(loader, "REGISTRY_PATH", registry_path):
                bundle = loader.load_registry_bundle()
                self.assertEqual(bundle["errors"], [])
                self.assertEqual(len(bundle["entries"]), 1)
                set_bundle = loader.load_question_set(bundle["entries"][0])
        finally:
            shutil.rmtree(base_dir, ignore_errors=True)

        self.assertEqual(set_bundle["errors"], [])
        self.assertTrue(any("does not match the file contents" in warning for warning in set_bundle["warnings"]))


if __name__ == "__main__":
    unittest.main()
