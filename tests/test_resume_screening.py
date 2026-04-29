import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.core.resume_screening import (
    calculate_resume_screening_app1,
    calculate_resume_screening_app2,
)


class TestResumeScreeningApp1(unittest.TestCase):

    def test_strong_app1_profile_returns_expected_structure(self):
        raw_text = """
        Alex Morgan
        alex.morgan@email.com
        +1 415 555 0111
        linkedin.com/in/alexmorgan

        Summary
        Data Scientist with 7 years of experience building ML systems.

        Experience
        Led machine learning projects and data analysis work across product teams.

        Education
        Master's Degree in Computer Science

        Skills
        Python, SQL, machine learning, pandas, numpy, scikit-learn, tensorflow, statistics

        Projects
        Production forecasting and recommendation systems.
        """
        features = {
            "years_of_experience": 7.0,
            "education_level": 2,
            "skills": [
                "python", "sql", "machine learning", "pandas",
                "numpy", "scikit-learn", "tensorflow", "statistics",
            ],
            "job_title": "Data Scientist",
            "sources": {
                "job_title": "skills:title_match",
                "country": "ner:united states",
                "education": "phrase:masters",
            },
        }
        score_data = {"total_score": 84}

        result = calculate_resume_screening_app1(raw_text, features, score_data)

        self.assertIn("overall_score", result)
        self.assertIn("overall_band", result)
        self.assertIn("ats_readiness_score", result)
        self.assertIn("role_match_score", result)
        self.assertIn("parse_confidence_score", result)
        self.assertIn("strengths", result)
        self.assertIn("gaps", result)
        self.assertIn("improvements", result)
        self.assertGreaterEqual(result["overall_score"], 80)
        self.assertEqual(result["overall_band"], "Strong")

    def test_layout_risk_surfaces_gap(self):
        raw_text = "\n".join(
            ["A | B | C | D | E | F | G"] +
            ["x" for _ in range(20)] +
            ["Skills", "Python", "SQL"]
        )
        features = {
            "years_of_experience": 0.0,
            "education_level": 1,
            "skills": ["python", "sql"],
            "job_title": "Software Engineer",
            "sources": {
                "job_title": "default",
                "country": "default",
                "education": "default_bachelor",
            },
        }
        score_data = {"total_score": 25}

        result = calculate_resume_screening_app1(raw_text, features, score_data)

        self.assertTrue(any("formatting signals" in item.lower() for item in result["gaps"]))
        self.assertTrue(any("one-column layout" in item.lower() for item in result["improvements"]))


class TestResumeScreeningApp2(unittest.TestCase):

    def test_direct_data_role_scores_well(self):
        raw_text = """
        Priya Shah
        priya.shah@email.com
        github.com/priyads

        Summary
        Machine Learning Engineer with 5 years of experience.

        Experience
        Built NLP and model deployment pipelines using Python, SQL, Docker, AWS, and Airflow.

        Skills
        Python, SQL, machine learning, NLP, Docker, AWS, Airflow, scikit-learn, PyTorch
        """
        features = {
            "years_of_experience_a2": 5.0,
            "skills_a2": [
                "python", "sql", "machine learning", "nlp", "docker",
                "aws", "airflow", "scikit-learn", "pytorch",
            ],
            "job_title_a2": "Machine Learning Engineer",
            "sources_a2": {
                "job_title": "title_match",
                "country": "alias:india",
            },
        }
        score_data = {
            "total_score_a2": 79,
            "ds_skill_count_a2": 7,
        }

        result = calculate_resume_screening_app2(raw_text, features, score_data)

        self.assertGreaterEqual(result["role_match_score"], 70)
        self.assertGreaterEqual(result["overall_score"], 75)
        self.assertIn(result["overall_band"], {"Strong", "Good"})
        self.assertTrue(any("data and machine-learning keyword coverage" in item.lower() for item in result["strengths"]))


if __name__ == "__main__":
    unittest.main()
