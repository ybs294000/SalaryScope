import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import unittest
from unittest.mock import MagicMock
sys.modules['streamlit'] = MagicMock()

from app.utils.country_utils import get_country_name, resolve_iso2
from app.utils.col_utils import get_col_index, compute_col_adjusted
from app.utils.savings_utils import compute_savings_potential
from app.utils.loan_utils import compute_loan_affordability
from app.utils.investment_utils import compute_investment_growth
from app.utils.emergency_fund_utils import compute_emergency_fund
from app.utils.budget_utils import compute_budget_allocation
from app.utils.ctc_utils import compute_ctc_breakdown


class TestCountryUtils(unittest.TestCase):

    def test_get_country_name_valid_iso(self):
        result = get_country_name("US")
        self.assertIn("United States", result)

    def test_get_country_name_unknown_returns_code(self):
        result = get_country_name("XX")
        self.assertEqual(result, "XX")

    def test_get_country_name_none_returns_unknown(self):
        result = get_country_name(None)
        self.assertEqual(result, "Unknown")

    def test_resolve_iso2_from_name(self):
        self.assertEqual(resolve_iso2("United States"), "US")
        self.assertEqual(resolve_iso2("India"), "IN")
        self.assertEqual(resolve_iso2("Germany"), "DE")

    def test_resolve_iso2_from_alias(self):
        self.assertEqual(resolve_iso2("USA"), "US")
        self.assertEqual(resolve_iso2("UK"), "GB")
        self.assertEqual(resolve_iso2("UAE"), "AE")

    def test_resolve_iso2_case_insensitive(self):
        self.assertEqual(resolve_iso2("india"), "IN")
        self.assertEqual(resolve_iso2("INDIA"), "IN")

    def test_resolve_iso2_from_direct_code(self):
        self.assertEqual(resolve_iso2("IN"), "IN")
        self.assertEqual(resolve_iso2("US"), "US")

    def test_resolve_iso2_unknown_returns_none(self):
        result = resolve_iso2("Narnia")
        self.assertIsNone(result)


class TestColUtils(unittest.TestCase):

    def test_get_col_index_known_country(self):
        index, source = get_col_index("US")
        self.assertEqual(index, 100.0)
        self.assertIn("built_in", source.lower())

    def test_get_col_index_unknown_country_returns_fallback(self):
        index, source = get_col_index("XX")
        self.assertEqual(index, 50.0)

    def test_compute_col_adjusted_same_country(self):
        result = compute_col_adjusted(100000, "US", "US")
        self.assertAlmostEqual(result["adjustment_factor"], 1.0, places=3)
        self.assertAlmostEqual(result["ppp_equivalent_usd"], 100000.0, places=0)

    def test_compute_col_adjusted_cheaper_country(self):
        # India (CoL ~23) vs USA (CoL 100): salary should appear larger in India terms
        result = compute_col_adjusted(100000, "US", "IN")
        self.assertLess(result["ppp_equivalent_usd"], 100000)
        self.assertLess(result["adjustment_factor"], 1.0)

    def test_compute_col_adjusted_expensive_country(self):
        # Switzerland (CoL 137) vs USA (CoL 100)
        result = compute_col_adjusted(100000, "US", "CH")
        self.assertGreater(result["ppp_equivalent_usd"], 100000)
        self.assertGreater(result["adjustment_factor"], 1.0)


class TestSavingsUtils(unittest.TestCase):

    def test_savings_structure(self):
        result = compute_savings_potential(5000, "US")
        self.assertIn("savings", result)
        self.assertIn("annual_savings", result)
        self.assertIn("expense_ratio_used", result)
        self.assertIn("savings_rate", result)

    def test_savings_non_negative(self):
        result = compute_savings_potential(3000, "IN")
        self.assertGreaterEqual(result["savings"], 0)

    def test_annual_savings_equals_monthly_times_12(self):
        result = compute_savings_potential(5000, "US")
        self.assertAlmostEqual(result["annual_savings"], result["savings"] * 12, places=2)

    def test_savings_rate_between_0_and_1(self):
        result = compute_savings_potential(5000, "GB")
        self.assertGreaterEqual(result["savings_rate"], 0)
        self.assertLessEqual(result["savings_rate"], 1)


class TestLoanUtils(unittest.TestCase):

    def test_loan_structure(self):
        result = compute_loan_affordability(5000, country="US")
        self.assertIn("max_loan", result)
        self.assertIn("affordable_emi", result)
        self.assertIn("interest_rate_pct", result)
        self.assertIn("loan_years", result)

    def test_max_loan_positive(self):
        result = compute_loan_affordability(5000, country="US")
        self.assertGreater(result["max_loan"], 0)

    def test_affordable_emi_within_cap(self):
        net_monthly = 5000
        result = compute_loan_affordability(net_monthly, country="US")
        emi_cap = result.get("emi_cap_fraction_used", 0.4)
        self.assertLessEqual(result["affordable_emi"], net_monthly * emi_cap + 1)  # +1 for rounding


class TestInvestmentUtils(unittest.TestCase):
    def test_investment_structure(self):
        result = compute_investment_growth(500, "US")
        self.assertIn("horizons", result)
        self.assertEqual(len(result["horizons"]), 4)

        for h in result["horizons"]:
            self.assertIn("years", h)
            self.assertIn("value_nominal", h)
            self.assertIn("value_real", h)

    def test_investment_grows_over_time(self):
        result = compute_investment_growth(500, "US")
        h = result["horizons"]

        values = [x["value_nominal"] for x in h]

        self.assertLess(values[0], values[1])
        self.assertLess(values[1], values[2])
        self.assertLess(values[2], values[3])

    def test_zero_savings_gives_zero_growth(self):
        result = compute_investment_growth(0, "US")

        for h in result["horizons"]:
            self.assertEqual(h["value_nominal"], 0.0)
            self.assertEqual(h["total_contributed"], 0.0)


class TestEmergencyFundUtils(unittest.TestCase):

    def test_emergency_fund_structure(self):
        result = compute_emergency_fund(5000, "US")
        self.assertIn("target_3mo", result)
        self.assertIn("target_6mo", result)
        self.assertIn("monthly_expenses_est", result)

    def test_6_month_double_3_month(self):
        result = compute_emergency_fund(5000, "US")
        self.assertAlmostEqual(result["target_6mo"], result["target_3mo"] * 2, places=0)


class TestBudgetUtils(unittest.TestCase):

    def test_budget_structure(self):
        result = compute_budget_allocation(5000, "US")
        self.assertIn("categories", result)
        self.assertIsInstance(result["categories"], list)
        self.assertGreater(len(result["categories"]), 0)

    def test_category_structure(self):
        result = compute_budget_allocation(5000, "US")
        for cat in result["categories"]:
            self.assertIn("label", cat)
            self.assertIn("amount_usd", cat)
            self.assertIn("fraction", cat)

    def test_allocations_sum_to_net(self):
        net = 5000
        result = compute_budget_allocation(net, "US")
        total = sum(c["amount_usd"] for c in result["categories"])
        self.assertAlmostEqual(total, net, delta=10)


class TestCtcUtils(unittest.TestCase):

    def test_ctc_structure(self):
        result = compute_ctc_breakdown(80000, "IN")
        self.assertIn("basic", result)
        self.assertIn("hra", result)
        self.assertIn("bonus", result)
        self.assertIn("pf_employee", result)

    def test_india_hra_is_50_of_basic(self):
        result = compute_ctc_breakdown(80000, "IN")
        self.assertAlmostEqual(result["hra"], result["basic"] * 0.50, delta=100)

    def test_us_hra_is_zero(self):
        result = compute_ctc_breakdown(80000, "US")
        self.assertEqual(result["hra"], 0.0)


if __name__ == '__main__':
    unittest.main()
