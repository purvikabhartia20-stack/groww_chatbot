"""
Tests for src/classifier.py

Covers:
- Allowed factual queries pass through
- Advisory queries are refused
- Comparison queries are refused
- Prediction queries are refused
- Ranking queries are refused
- Suitability queries are refused
- Safe override patterns prevent false positives (EC-4.1)
- Scheme detection from query text
- Out-of-corpus detection (EC-4.13)
- Case insensitivity
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from src.classifier import classify, ClassifierResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def allowed(query: str) -> ClassifierResult:
    result = classify(query)
    assert result.allowed, f"Expected ALLOWED but got REFUSED for: '{query}'\nPattern: {result.matched_pattern}"
    return result


def refused(query: str) -> ClassifierResult:
    result = classify(query)
    assert not result.allowed, f"Expected REFUSED but got ALLOWED for: '{query}'"
    return result


# ---------------------------------------------------------------------------
# Allowed — factual queries
# ---------------------------------------------------------------------------
class TestAllowedQueries:
    def test_expense_ratio(self):
        allowed("What is the expense ratio of HDFC Mid Cap Fund?")

    def test_exit_load(self):
        allowed("What is the exit load for HDFC ELSS Tax Saver Fund?")

    def test_minimum_sip(self):
        allowed("What is the minimum SIP amount for HDFC Large Cap Fund?")

    def test_lock_in_period(self):
        allowed("What is the lock-in period of HDFC ELSS Tax Saver Fund?")

    def test_benchmark_index(self):
        allowed("What is the benchmark index of HDFC Equity Fund?")

    def test_nav(self):
        allowed("What is the NAV of HDFC Focused Fund?")

    def test_fund_category(self):
        allowed("What is the fund category of HDFC Mid Cap Fund?")

    def test_aum(self):
        allowed("What is the AUM of HDFC Large Cap Fund?")

    def test_riskometer(self):
        allowed("What is the riskometer rating of HDFC ELSS Tax Saver Fund?")

    def test_investment_objective(self):
        allowed("What is the investment objective of HDFC Equity Fund?")

    def test_fund_manager(self):
        allowed("Who is the fund manager of HDFC Mid Cap Fund?")

    def test_stamp_duty(self):
        allowed("What is the stamp duty on HDFC Mid Cap Fund?")

    def test_tax_implication(self):
        allowed("What are the tax implications of redeeming HDFC ELSS?")


# ---------------------------------------------------------------------------
# Refused — investment advice
# ---------------------------------------------------------------------------
class TestRefusedAdvice:
    def test_should_i_invest(self):
        refused("Should I invest in HDFC Mid Cap Fund?")

    def test_should_i_buy(self):
        refused("Should I buy HDFC ELSS Tax Saver Fund?")

    def test_is_it_worth(self):
        refused("Is it worth investing in HDFC Large Cap Fund?")

    def test_good_time(self):
        refused("Is this a good time to invest in mutual funds?")

    def test_right_time(self):
        refused("Is this the right time to invest in HDFC funds?")

    def test_worth_investing(self):
        refused("Is HDFC Mid Cap Fund worth investing in?")

    def test_should_i_generic(self):
        refused("Should I start a SIP now?")


# ---------------------------------------------------------------------------
# Refused — comparisons
# ---------------------------------------------------------------------------
class TestRefusedComparisons:
    def test_compare_funds(self):
        refused("Compare HDFC Mid Cap and HDFC Large Cap")

    def test_fund_vs_fund(self):
        refused("HDFC Mid Cap Fund vs HDFC Large Cap Fund")

    def test_better_than(self):
        refused("Is HDFC Mid Cap Fund better than HDFC Large Cap Fund?")

    def test_which_is_better(self):
        refused("Which is better, HDFC ELSS or HDFC Large Cap?")

    def test_which_fund_is_best(self):
        refused("Which fund is best for long term?")

    def test_which_sip(self):
        refused("Which SIP should I choose?")


# ---------------------------------------------------------------------------
# Refused — predictions / forecasts
# ---------------------------------------------------------------------------
class TestRefusedPredictions:
    def test_will_it_grow(self):
        refused("Will HDFC Mid Cap Fund grow in the next year?")

    def test_will_fund_grow(self):
        refused("Will HDFC Mid Cap Fund grow in the next year?")

    def test_expected_returns(self):
        refused("What are the expected returns of HDFC ELSS?")

    def test_future_returns(self):
        refused("What will be the future returns of HDFC Large Cap?")

    def test_beat_inflation(self):
        refused("Can HDFC Mid Cap Fund beat inflation?")

    def test_will_outperform(self):
        refused("Will HDFC Equity Fund outperform the market?")

    def test_will_fund_outperform(self):
        refused("Will HDFC Equity Fund outperform the market?")

    def test_give_good_returns(self):
        refused("Will HDFC ELSS give good returns?")

    def test_what_returns(self):
        refused("What returns can I expect from HDFC Mid Cap?")


# ---------------------------------------------------------------------------
# Refused — rankings
# ---------------------------------------------------------------------------
class TestRefusedRankings:
    def test_best_fund(self):
        refused("What is the best fund for tax saving?")

    def test_best_performing(self):
        refused("Which is the best performing HDFC fund?")

    def test_top_fund(self):
        refused("What is the top fund in mid cap category?")

    def test_safest_fund(self):
        refused("Which is the safest fund to invest in?")

    def test_highest_return(self):
        refused("Which fund gives the highest return?")

    def test_best_sip(self):
        refused("What is the best SIP to start?")

    def test_best_mutual_fund(self):
        refused("What is the best mutual fund in India?")


# ---------------------------------------------------------------------------
# Refused — suitability / evaluative
# ---------------------------------------------------------------------------
class TestRefusedSuitability:
    def test_suits_my_goals(self):
        refused("Does HDFC ELSS suit my goals?")

    def test_right_for_me(self):
        refused("Is HDFC Mid Cap Fund right for me?")

    def test_suitable_for_me(self):
        refused("Is HDFC Large Cap Fund suitable for me?")

    def test_recommend(self):
        refused("Can you recommend a good HDFC fund?")

    def test_is_it_safe(self):
        refused("Is HDFC Mid Cap Fund safe?")

    def test_is_it_good(self):
        refused("Is HDFC ELSS a good investment?")

    def test_good_investment(self):
        refused("Is HDFC Large Cap Fund a good investment?")

    def test_safe_investment(self):
        refused("Is HDFC Mid Cap Fund a safe investment?")


# ---------------------------------------------------------------------------
# Safe overrides — EC-4.1 (should NOT be refused)
# ---------------------------------------------------------------------------
class TestSafeOverrides:
    def test_best_way_to_check(self):
        allowed("What is the best way to check the expense ratio?")

    def test_best_way_to_download(self):
        allowed("What is the best way to download my statement?")

    def test_best_way_to_access(self):
        allowed("What is the best way to access my account?")

    def test_best_time_to_check(self):
        allowed("What is the best time to check NAV?")


# ---------------------------------------------------------------------------
# Scheme detection
# ---------------------------------------------------------------------------
class TestSchemeDetection:
    def test_detects_mid_cap(self):
        r = allowed("What is the expense ratio of HDFC Mid Cap Fund?")
        assert r.detected_scheme == "HDFC Mid Cap Fund Direct Growth"

    def test_detects_elss(self):
        r = allowed("What is the lock-in period of HDFC ELSS Tax Saver Fund?")
        assert r.detected_scheme == "HDFC ELSS Tax Saver Fund Direct Plan Growth"

    def test_detects_elss_short(self):
        r = allowed("What is the exit load for HDFC ELSS?")
        assert r.detected_scheme == "HDFC ELSS Tax Saver Fund Direct Plan Growth"

    def test_detects_large_cap(self):
        r = allowed("What is the NAV of HDFC Large Cap Fund?")
        assert r.detected_scheme == "HDFC Large Cap Fund Direct Growth"

    def test_detects_equity(self):
        r = allowed("What is the benchmark of HDFC Equity Fund?")
        assert r.detected_scheme == "HDFC Equity Fund Direct Growth"

    def test_detects_focused(self):
        r = allowed("What is the AUM of HDFC Focused Fund?")
        assert r.detected_scheme == "HDFC Focused Fund Direct Growth"

    def test_no_scheme_detected(self):
        r = allowed("What is a mutual fund?")
        assert r.detected_scheme is None


# ---------------------------------------------------------------------------
# Out-of-corpus detection — EC-4.13
# ---------------------------------------------------------------------------
class TestOutOfCorpus:
    def test_flexi_cap_out_of_corpus(self):
        r = allowed("What is the expense ratio of HDFC Flexi Cap Fund?")
        assert r.out_of_corpus is True

    def test_small_cap_out_of_corpus(self):
        r = allowed("What is the NAV of HDFC Small Cap Fund?")
        assert r.out_of_corpus is True

    def test_known_scheme_not_out_of_corpus(self):
        r = allowed("What is the expense ratio of HDFC Mid Cap Fund?")
        assert r.out_of_corpus is False

    def test_generic_query_not_out_of_corpus(self):
        r = allowed("What is a mutual fund?")
        assert r.out_of_corpus is False


# ---------------------------------------------------------------------------
# Case insensitivity
# ---------------------------------------------------------------------------
class TestCaseInsensitivity:
    def test_uppercase_refused(self):
        refused("SHOULD I INVEST IN HDFC MID CAP FUND?")

    def test_mixed_case_refused(self):
        refused("Which Fund Is Best For Tax Saving?")

    def test_uppercase_allowed(self):
        allowed("WHAT IS THE EXPENSE RATIO OF HDFC MID CAP FUND?")
