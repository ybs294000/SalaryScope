import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import unittest
from unittest.mock import patch, MagicMock
sys.modules['streamlit'] = MagicMock()

from app.core.resume_analysis import (
    preprocess_resume_text,
    extract_experience_years,
    calculate_resume_score,
    extract_employment_type_a2,
    extract_remote_ratio_a2,
    calculate_resume_score_a2,
)


class TestPreprocessResumeText(unittest.TestCase):

    def test_returns_string(self):
        result = preprocess_resume_text("Some raw text here.")
        self.assertIsInstance(result, str)

    def test_handles_empty_string(self):
        result = preprocess_resume_text("")
        self.assertIsInstance(result, str)


class TestExtractExperienceYears(unittest.TestCase):

    def test_explicit_years(self):
        result = extract_experience_years("I have 5 years of experience in Python.")
        self.assertAlmostEqual(result, 5.0, places=0)

    def test_plus_notation(self):
        result = extract_experience_years("Over 3+ years of professional work.")
        self.assertAlmostEqual(result, 3.0, places=0)

    def test_no_experience_returns_zero(self):
        result = extract_experience_years("Recent graduate with strong academic background.")
        self.assertEqual(result, 0.0)

    def test_returns_float(self):
        result = extract_experience_years("7 years experience")
        self.assertIsInstance(result, float)


class TestCalculateResumeScoreApp1(unittest.TestCase):

    def test_score_structure(self):
        features = {
            "years_of_experience": 5.0,
            "education_level": 1,
            "skills": ["python", "sql", "pandas"]
        }
        result = calculate_resume_score(features)
        self.assertIn("total_score", result)
        self.assertIn("level", result)
        self.assertIn("experience_score", result)
        self.assertIn("education_score", result)
        self.assertIn("skills_score", result)

    def test_score_range(self):
        features = {
            "years_of_experience": 10.0,
            "education_level": 3,
            "skills": ["python"] * 15
        }
        result = calculate_resume_score(features)
        self.assertGreaterEqual(result["total_score"], 0)
        self.assertLessEqual(result["total_score"], 100)

    def test_zero_experience_zero_score_component(self):
        features = {"years_of_experience": 0.0, "education_level": 0, "skills": []}
        result = calculate_resume_score(features)
        self.assertEqual(result["experience_score"], 0)
        self.assertEqual(result["skills_score"], 0)

    def test_phd_max_education_score(self):
        features = {"years_of_experience": 0.0, "education_level": 3, "skills": []}
        result = calculate_resume_score(features)
        self.assertEqual(result["education_score"], 35)

    def test_level_labels(self):
        features_basic = {"years_of_experience": 0.0, "education_level": 0, "skills": []}
        result = calculate_resume_score(features_basic)
        self.assertIn(result["level"], ["Basic", "Moderate", "Strong"])


class TestExtractEmploymentType(unittest.TestCase):

    def test_full_time_default(self):
        result = extract_employment_type_a2("software engineer at tech company")
        self.assertEqual(result, "FT")

    def test_part_time_detected(self):
        result = extract_employment_type_a2("part-time data analyst position")
        self.assertEqual(result, "PT")

    def test_freelance_detected(self):
        result = extract_employment_type_a2("freelancer with 5 years experience")
        self.assertEqual(result, "FL")

    def test_contract_detected(self):
        result = extract_employment_type_a2("contract consultant role")
        self.assertEqual(result, "CT")

    def test_internship_detected_as_part_time(self):
        result = extract_employment_type_a2("summer internship at a startup")
        self.assertEqual(result, "PT")


class TestExtractRemoteRatio(unittest.TestCase):

    def test_onsite_default(self):
        result = extract_remote_ratio_a2("office-based position in NYC")
        self.assertEqual(result, 0)

    def test_remote_detected(self):
        result = extract_remote_ratio_a2("fully remote work from home position")
        self.assertEqual(result, 100)

    def test_hybrid_detected(self):
        result = extract_remote_ratio_a2("hybrid role with flexible working")
        self.assertEqual(result, 50)

    def test_wfh_detected_as_remote(self):
        result = extract_remote_ratio_a2("WFH allowed, 100% remote")
        self.assertEqual(result, 100)


class TestCalculateResumeScoreApp2(unittest.TestCase):

    def test_score_structure(self):
        features = {
            "years_of_experience_a2": 5.0,
            "skills_a2": ["python", "machine learning", "sql"],
            "job_title_a2": "Data Scientist"
        }
        result = calculate_resume_score_a2(features)
        self.assertIn("total_score_a2", result)
        self.assertIn("level_a2", result)
        self.assertIn("experience_score_a2", result)
        self.assertIn("skills_score_a2", result)
        self.assertIn("title_score_a2", result)
        self.assertIn("ds_skill_count_a2", result)

    def test_ds_title_gets_max_title_score(self):
        features = {
            "years_of_experience_a2": 0.0,
            "skills_a2": [],
            "job_title_a2": "Data Scientist"
        }
        result = calculate_resume_score_a2(features)
        self.assertEqual(result["title_score_a2"], 25)

    def test_ds_skills_weighted_higher(self):
        features_ds = {
            "years_of_experience_a2": 0.0,
            "skills_a2": ["python", "machine learning"],
            "job_title_a2": "Other"
        }
        features_gen = {
            "years_of_experience_a2": 0.0,
            "skills_a2": ["excel", "powerpoint"],
            "job_title_a2": "Other"
        }
        result_ds = calculate_resume_score_a2(features_ds)
        result_gen = calculate_resume_score_a2(features_gen)
        self.assertGreater(result_ds["skills_score_a2"], result_gen["skills_score_a2"])


if __name__ == '__main__':
    unittest.main()
