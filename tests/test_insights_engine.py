import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import unittest
from unittest.mock import MagicMock
sys.modules['streamlit'] = MagicMock()

from app.core.insights_engine import (
    detect_domain_from_title,
    classify_job_group_app1,
    get_experience_category_app1,
    classify_role_app2,
)


class TestDomainDetection(unittest.TestCase):

    def test_ml_ai_detected(self):
        self.assertEqual(detect_domain_from_title("Machine Learning Engineer"), "ml_ai")
        self.assertEqual(detect_domain_from_title("NLP Researcher"), "ml_ai")
        self.assertEqual(detect_domain_from_title("MLOps Engineer"), "ml_ai")

    def test_analytics_detected(self):
        self.assertEqual(detect_domain_from_title("Data Analyst"), "analytics")
        self.assertEqual(detect_domain_from_title("Business Intelligence Analyst"), "analytics")

    def test_data_eng_detected(self):
        self.assertEqual(detect_domain_from_title("Data Engineer"), "data_eng")
        self.assertEqual(detect_domain_from_title("ETL Developer"), "data_eng")

    def test_scientist_detected(self):
        self.assertEqual(detect_domain_from_title("Data Scientist"), "scientist")

    def test_ml_ai_takes_priority_over_analyst(self):
        # An ML analyst should be ml_ai (higher priority)
        result = detect_domain_from_title("ML Research Analyst")
        self.assertEqual(result, "ml_ai")

    def test_other_for_unknown(self):
        self.assertEqual(detect_domain_from_title("Marketing Manager"), "other")
        self.assertEqual(detect_domain_from_title(""), "other")

    def test_none_returns_other(self):
        self.assertEqual(detect_domain_from_title(None), "other")


class TestJobGroupApp1(unittest.TestCase):

    def test_tech_group(self):
        self.assertEqual(classify_job_group_app1("Software Engineer"), "Tech")
        self.assertEqual(classify_job_group_app1("Data Analyst"), "Tech")

    def test_management_group(self):
        self.assertEqual(classify_job_group_app1("Project Manager"), "Management")
        self.assertEqual(classify_job_group_app1("Director of Engineering"), "Management")

    def test_marketing_group(self):
        self.assertEqual(classify_job_group_app1("Marketing Manager"), "Marketing_Sales")

    def test_hr_group(self):
        self.assertEqual(classify_job_group_app1("HR Generalist"), "HR")
        self.assertEqual(classify_job_group_app1("Recruiter"), "HR")

    def test_finance_group(self):
        self.assertEqual(classify_job_group_app1("Financial Analyst"), "Finance")

    def test_design_group(self):
        self.assertEqual(classify_job_group_app1("UX Designer"), "Design")

    def test_operations_fallback(self):
        self.assertEqual(classify_job_group_app1("Office Administrator"), "Operations")

    def test_non_string_returns_operations(self):
        self.assertEqual(classify_job_group_app1(None), "Operations")


class TestExperienceCategoryApp1(unittest.TestCase):

    def test_entry_level(self):
        self.assertEqual(get_experience_category_app1(0.0), "Entry")
        self.assertEqual(get_experience_category_app1(2.0), "Entry")

    def test_mid_level(self):
        self.assertEqual(get_experience_category_app1(2.5), "Mid")
        self.assertEqual(get_experience_category_app1(5.0), "Mid")

    def test_senior_level(self):
        self.assertEqual(get_experience_category_app1(5.5), "Senior")
        self.assertEqual(get_experience_category_app1(20.0), "Senior")


class TestClassifyRoleApp2(unittest.TestCase):

    def test_management_overrides_domain(self):
        result = classify_role_app2("ml_ai", is_mgmt=True, is_exec=False)
        self.assertEqual(result, "Management")

    def test_ml_ai_domain(self):
        result = classify_role_app2("ml_ai", is_mgmt=False, is_exec=False)
        self.assertEqual(result, "Machine Learning / AI")

    def test_analytics_domain(self):
        result = classify_role_app2("analytics", is_mgmt=False, is_exec=False)
        self.assertEqual(result, "Analytics")

    def test_other_domain(self):
        result = classify_role_app2("other", is_mgmt=False, is_exec=False)
        self.assertEqual(result, "Other")


if __name__ == '__main__':
    unittest.main()
