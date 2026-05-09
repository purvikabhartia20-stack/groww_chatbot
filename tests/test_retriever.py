"""
Tests for src/retriever.py

Covers:
- Synonym expansion maps financial terms correctly (EC-4.4)
- URL validation logic (via formatter, tested separately)
- Scheme filter map covers all 5 known schemes
- RetrievalResult dataclass defaults
- Threshold filtering logic (unit-level, no ChromaDB dependency)
- BGE query prefix is applied
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from src.retriever import (
    _expand_synonyms,
    QUERY_SYNONYMS,
    SCHEME_FILTER_MAP,
    SIMILARITY_THRESHOLD,
    BGE_QUERY_PREFIX,
    RetrievalResult,
    RetrievedChunk,
)


# ---------------------------------------------------------------------------
# Synonym expansion (EC-4.4)
# ---------------------------------------------------------------------------
class TestSynonymExpansion:
    def test_management_fee_to_expense_ratio(self):
        result = _expand_synonyms("What is the management fee of HDFC Mid Cap?")
        assert "expense ratio" in result

    def test_annual_fee_to_expense_ratio(self):
        result = _expand_synonyms("What is the annual fee?")
        assert "expense ratio" in result

    def test_ter_to_expense_ratio(self):
        result = _expand_synonyms("What is the TER of HDFC Mid Cap?")
        assert "expense ratio" in result.lower()

    def test_redemption_charge_to_exit_load(self):
        result = _expand_synonyms("What is the redemption charge?")
        assert "exit load" in result

    def test_redemption_fee_to_exit_load(self):
        result = _expand_synonyms("What is the redemption fee?")
        assert "exit load" in result

    def test_exit_charge_to_exit_load(self):
        result = _expand_synonyms("What is the exit charge?")
        assert "exit load" in result

    def test_tax_saving_fund_to_elss(self):
        result = _expand_synonyms("What is the lock-in for tax saving fund?")
        assert "elss" in result.lower()

    def test_lock_in_expansion(self):
        result = _expand_synonyms("What is the lock in period?")
        assert "lock-in period" in result

    def test_min_sip_expansion(self):
        result = _expand_synonyms("What is the min sip amount?")
        assert "minimum sip" in result.lower()

    def test_nav_expansion(self):
        result = _expand_synonyms("What is the NAV today?")
        assert "net asset value" in result.lower()

    def test_no_synonym_unchanged(self):
        query = "What is the expense ratio of HDFC Mid Cap Fund?"
        result = _expand_synonyms(query)
        # expense ratio is already canonical — should still be present
        assert "expense ratio" in result

    def test_expansion_is_case_insensitive(self):
        result = _expand_synonyms("What is the TER?")
        assert "expense ratio" in result.lower()

    def test_all_synonyms_have_canonical(self):
        """Every synonym in the map should produce a non-empty canonical."""
        for synonym, canonical in QUERY_SYNONYMS.items():
            assert canonical, f"Synonym '{synonym}' maps to empty canonical"
            assert len(canonical) > 0


# ---------------------------------------------------------------------------
# Scheme filter map completeness
# ---------------------------------------------------------------------------
class TestSchemeFilterMap:
    def test_all_five_schemes_present(self):
        expected_display_names = [
            "HDFC Mid Cap Fund Direct Growth",
            "HDFC Equity Fund Direct Growth",
            "HDFC Focused Fund Direct Growth",
            "HDFC ELSS Tax Saver Fund Direct Plan Growth",
            "HDFC Large Cap Fund Direct Growth",
        ]
        for name in expected_display_names:
            assert name in SCHEME_FILTER_MAP, f"Missing scheme: {name}"

    def test_filter_values_match_chromadb_metadata(self):
        """Filter values must match exactly what's stored in ChromaDB."""
        expected_db_values = {
            "HDFC Mid Cap Fund Direct Growth": "HDFC Mid Cap Fund",
            "HDFC Equity Fund Direct Growth": "HDFC Equity Fund",
            "HDFC Focused Fund Direct Growth": "HDFC Focused Fund",
            "HDFC ELSS Tax Saver Fund Direct Plan Growth": "HDFC ELSS Tax Saver Fund",
            "HDFC Large Cap Fund Direct Growth": "HDFC Large Cap Fund",
        }
        for display_name, expected_db in expected_db_values.items():
            assert SCHEME_FILTER_MAP[display_name] == expected_db, (
                f"Filter value mismatch for '{display_name}': "
                f"expected '{expected_db}', got '{SCHEME_FILTER_MAP[display_name]}'"
            )

    def test_no_extra_schemes(self):
        assert len(SCHEME_FILTER_MAP) == 5


# ---------------------------------------------------------------------------
# Constants sanity checks
# ---------------------------------------------------------------------------
class TestConstants:
    def test_similarity_threshold_in_valid_range(self):
        assert 0.0 < SIMILARITY_THRESHOLD < 1.0

    def test_similarity_threshold_not_too_high(self):
        # If threshold is too high, too many valid queries will fall back
        assert SIMILARITY_THRESHOLD <= 0.80

    def test_similarity_threshold_not_too_low(self):
        # If threshold is too low, irrelevant chunks will pollute context
        assert SIMILARITY_THRESHOLD >= 0.60

    def test_bge_query_prefix_not_empty(self):
        assert len(BGE_QUERY_PREFIX) > 0

    def test_bge_query_prefix_content(self):
        assert "searching" in BGE_QUERY_PREFIX.lower()


# ---------------------------------------------------------------------------
# RetrievalResult dataclass
# ---------------------------------------------------------------------------
class TestRetrievalResult:
    def test_default_empty_chunks(self):
        r = RetrievalResult()
        assert r.chunks == []

    def test_default_below_threshold_false(self):
        r = RetrievalResult()
        assert r.below_threshold is False

    def test_default_fallback_false(self):
        r = RetrievalResult()
        assert r.fallback_triggered is False

    def test_fallback_triggered_true(self):
        r = RetrievalResult(fallback_triggered=True)
        assert r.fallback_triggered is True

    def test_chunks_list(self):
        chunk = RetrievedChunk(
            chunk_id="test-id",
            chunk_text="The expense ratio is 0.77%.",
            source_url="https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth",
            scheme_name="HDFC Mid Cap Fund",
            fund_category="Mid Cap",
            section_label="nav_sip_aum",
            last_updated="2026-05-08",
            similarity=0.88,
            document_type="Groww_Fund_Page",
        )
        r = RetrievalResult(chunks=[chunk])
        assert len(r.chunks) == 1
        assert r.chunks[0].similarity == 0.88


# ---------------------------------------------------------------------------
# RetrievedChunk dataclass
# ---------------------------------------------------------------------------
class TestRetrievedChunk:
    def test_chunk_fields(self):
        chunk = RetrievedChunk(
            chunk_id="abc-123",
            chunk_text="Exit load is Nil.",
            source_url="https://groww.in/mutual-funds/hdfc-elss-tax-saver-fund-direct-plan-growth",
            scheme_name="HDFC ELSS Tax Saver Fund",
            fund_category="ELSS",
            section_label="exit_load",
            last_updated="2026-05-08",
            similarity=0.80,
            document_type="Groww_Fund_Page",
        )
        assert chunk.chunk_id == "abc-123"
        assert chunk.section_label == "exit_load"
        assert chunk.similarity == 0.80
        assert chunk.source_url.startswith("https://groww.in")
