"""
Tests for src/formatter.py

Covers:
- Normal response formatting (sentence cap, source URL, date footer)
- Prohibited language detection triggers fallback (EC-4.5)
- Fallback response has no source URL (EC-5.11)
- Out-of-corpus fallback has no source URL and lists covered funds
- Refusal response structure
- Source URL validation — only approved corpus URLs shown (EC-5.11)
- Sentence cap enforcement (EC-4.6)
- LLM-injected Source/Last updated lines are stripped
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from src.formatter import (
    format_response,
    format_refusal,
    _scan_prohibited,
    _validate_url,
    _split_sentences,
    APPROVED_URL_PREFIX,
    FALLBACK_ANSWER,
)

VALID_URL = "https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth"
INVALID_URL = "https://hdfcfund.com/some-page"
AMFI_URL = "https://www.amfiindia.com/some-page"


# ---------------------------------------------------------------------------
# format_response — normal path
# ---------------------------------------------------------------------------
class TestFormatResponseNormal:
    def test_returns_answer(self):
        r = format_response("The expense ratio is 0.77%.", VALID_URL, "2026-05-08")
        assert r["answer"] == "The expense ratio is 0.77%."

    def test_returns_valid_source_url(self):
        r = format_response("The expense ratio is 0.77%.", VALID_URL, "2026-05-08")
        assert r["source_url"] == VALID_URL

    def test_returns_last_updated(self):
        r = format_response("The expense ratio is 0.77%.", VALID_URL, "2026-05-08")
        assert r["last_updated"] == "2026-05-08"

    def test_refused_is_false(self):
        r = format_response("The expense ratio is 0.77%.", VALID_URL, "2026-05-08")
        assert r["refused"] is False

    def test_fallback_is_false(self):
        r = format_response("The expense ratio is 0.77%.", VALID_URL, "2026-05-08")
        assert r["fallback"] is False

    def test_adds_period_if_missing(self):
        r = format_response("The expense ratio is 0.77%", VALID_URL, "2026-05-08")
        assert r["answer"].endswith(".")

    def test_does_not_double_period(self):
        r = format_response("The expense ratio is 0.77%.", VALID_URL, "2026-05-08")
        assert not r["answer"].endswith("..")

    def test_strips_llm_source_line(self):
        raw = "The expense ratio is 0.77%. Source: https://groww.in/..."
        r = format_response(raw, VALID_URL, "2026-05-08")
        assert "Source:" not in r["answer"]

    def test_strips_llm_last_updated_line(self):
        raw = "The expense ratio is 0.77%. Last updated from sources: 2026-05-08"
        r = format_response(raw, VALID_URL, "2026-05-08")
        assert "Last updated" not in r["answer"]

    def test_invalid_url_returns_none(self):
        r = format_response("The expense ratio is 0.77%.", INVALID_URL, "2026-05-08")
        assert r["source_url"] is None

    def test_amfi_url_not_shown(self):
        r = format_response("The expense ratio is 0.77%.", AMFI_URL, "2026-05-08")
        assert r["source_url"] is None

    def test_empty_url_returns_none(self):
        r = format_response("The expense ratio is 0.77%.", "", "2026-05-08")
        assert r["source_url"] is None

    def test_missing_date_returns_na(self):
        r = format_response("The expense ratio is 0.77%.", VALID_URL, "")
        assert r["last_updated"] == "N/A"


# ---------------------------------------------------------------------------
# format_response — sentence cap (EC-4.6)
# ---------------------------------------------------------------------------
class TestSentenceCap:
    def test_three_sentences_kept(self):
        raw = "Sentence one. Sentence two. Sentence three."
        r = format_response(raw, VALID_URL, "2026-05-08")
        sentences = [s for s in r["answer"].split(". ") if s]
        assert len(sentences) <= 3

    def test_four_sentences_truncated(self):
        raw = "One. Two. Three. Four."
        r = format_response(raw, VALID_URL, "2026-05-08")
        # Should contain at most 3 sentences
        parts = _split_sentences(r["answer"])
        assert len(parts) <= 3

    def test_single_sentence_kept(self):
        raw = "The exit load is Nil."
        r = format_response(raw, VALID_URL, "2026-05-08")
        assert "The exit load is Nil" in r["answer"]


# ---------------------------------------------------------------------------
# format_response — fallback path
# ---------------------------------------------------------------------------
class TestFormatResponseFallback:
    def test_is_fallback_true_triggers_fallback(self):
        r = format_response(None, VALID_URL, "2026-05-08", is_fallback=True)
        assert r["fallback"] is True

    def test_none_raw_text_triggers_fallback(self):
        r = format_response(None, VALID_URL, "2026-05-08")
        assert r["fallback"] is True

    def test_fallback_has_no_source_url(self):
        r = format_response(None, VALID_URL, "2026-05-08", is_fallback=True)
        assert r["source_url"] is None

    def test_fallback_has_no_last_updated(self):
        r = format_response(None, VALID_URL, "2026-05-08", is_fallback=True)
        assert r["last_updated"] is None

    def test_fallback_answer_contains_expected_text(self):
        r = format_response(None, VALID_URL, "2026-05-08", is_fallback=True)
        assert "could not be found" in r["answer"].lower()

    def test_out_of_corpus_fallback_lists_covered_funds(self):
        r = format_response(None, VALID_URL, "2026-05-08", out_of_corpus=True)
        assert "HDFC Mid Cap" in r["answer"]
        assert r["source_url"] is None

    def test_out_of_corpus_fallback_is_fallback_true(self):
        r = format_response(None, VALID_URL, "2026-05-08", out_of_corpus=True)
        assert r["fallback"] is True


# ---------------------------------------------------------------------------
# Prohibited language scan (EC-4.5)
# ---------------------------------------------------------------------------
class TestProhibitedLanguageScan:
    def test_you_should_triggers_fallback(self):
        r = format_response("You should invest in this fund.", VALID_URL, "2026-05-08")
        assert r["fallback"] is True
        assert r["source_url"] is None

    def test_recommended_triggers_fallback(self):
        r = format_response("This fund is recommended for long term.", VALID_URL, "2026-05-08")
        assert r["fallback"] is True

    def test_best_fund_triggers_fallback(self):
        r = format_response("This is the best fund in its category.", VALID_URL, "2026-05-08")
        assert r["fallback"] is True

    def test_safe_investment_triggers_fallback(self):
        r = format_response("This is a safe investment option.", VALID_URL, "2026-05-08")
        assert r["fallback"] is True

    def test_good_option_triggers_fallback(self):
        r = format_response("This is a good option for investors.", VALID_URL, "2026-05-08")
        assert r["fallback"] is True

    def test_performs_well_triggers_fallback(self):
        r = format_response("This fund performs well in bull markets.", VALID_URL, "2026-05-08")
        assert r["fallback"] is True

    def test_suits_your_goals_triggers_fallback(self):
        r = format_response("This fund suits your goals perfectly.", VALID_URL, "2026-05-08")
        assert r["fallback"] is True

    def test_clean_text_not_flagged(self):
        r = format_response(
            "The expense ratio of HDFC Mid Cap Fund is 0.77% as of May 2026.",
            VALID_URL, "2026-05-08"
        )
        assert r["fallback"] is False
        assert r["prohibited_detected"] is False

    def test_scan_prohibited_returns_match(self):
        assert _scan_prohibited("You should invest in this fund.") is not None

    def test_scan_prohibited_returns_none_for_clean(self):
        assert _scan_prohibited("The expense ratio is 0.77%.") is None

    def test_case_insensitive_detection(self):
        assert _scan_prohibited("YOU SHOULD invest in this fund.") is not None


# ---------------------------------------------------------------------------
# format_refusal
# ---------------------------------------------------------------------------
class TestFormatRefusal:
    def test_refused_is_true(self):
        r = format_refusal()
        assert r["refused"] is True

    def test_fallback_is_false(self):
        r = format_refusal()
        assert r["fallback"] is False

    def test_no_source_url(self):
        r = format_refusal()
        assert r["source_url"] is None

    def test_no_last_updated(self):
        r = format_refusal()
        assert r["last_updated"] is None

    def test_answer_mentions_scope(self):
        r = format_refusal()
        assert "factual" in r["answer"].lower()

    def test_answer_contains_amfi_link(self):
        r = format_refusal()
        assert "amfiindia.com" in r["answer"]

    def test_answer_does_not_contain_advisory_language(self):
        r = format_refusal()
        answer_lower = r["answer"].lower()
        assert "you should" not in answer_lower
        assert "recommended" not in answer_lower


# ---------------------------------------------------------------------------
# _validate_url
# ---------------------------------------------------------------------------
class TestValidateUrl:
    def test_valid_groww_url_passes(self):
        assert _validate_url(VALID_URL) == VALID_URL

    def test_non_corpus_url_returns_none(self):
        assert _validate_url(INVALID_URL) is None

    def test_amfi_url_returns_none(self):
        assert _validate_url(AMFI_URL) is None

    def test_empty_string_returns_none(self):
        assert _validate_url("") is None

    def test_none_like_empty_returns_none(self):
        assert _validate_url("") is None

    def test_http_not_https_returns_none(self):
        assert _validate_url("http://groww.in/mutual-funds/hdfc-mid-cap") is None

    def test_all_five_corpus_urls_pass(self):
        urls = [
            "https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth",
            "https://groww.in/mutual-funds/hdfc-equity-fund-direct-growth",
            "https://groww.in/mutual-funds/hdfc-focused-fund-direct-growth",
            "https://groww.in/mutual-funds/hdfc-elss-tax-saver-fund-direct-plan-growth",
            "https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth",
        ]
        for url in urls:
            assert _validate_url(url) == url, f"Expected {url} to pass validation"


# ---------------------------------------------------------------------------
# _split_sentences
# ---------------------------------------------------------------------------
class TestSplitSentences:
    def test_single_sentence(self):
        assert len(_split_sentences("Hello world.")) == 1

    def test_two_sentences(self):
        assert len(_split_sentences("Hello world. Goodbye world.")) == 2

    def test_three_sentences(self):
        parts = _split_sentences("One. Two. Three.")
        assert len(parts) == 3

    def test_question_mark_splits(self):
        parts = _split_sentences("What is NAV? It is the net asset value.")
        assert len(parts) == 2

    def test_exclamation_splits(self):
        parts = _split_sentences("Important! Read this carefully.")
        assert len(parts) == 2

    def test_empty_string(self):
        assert _split_sentences("") == []
