"""
Integration tests — PII filter + classifier + formatter pipeline
(no Groq API calls, no ChromaDB dependency)

Covers:
- PII filter blocks PAN, Aadhaar, phone, email (EC-5.1)
- PII filter false positive prevention (EC-5.1)
- Classifier + formatter refusal path end-to-end
- Classifier + formatter fallback path end-to-end
- Classifier + formatter normal path (mocked retrieval)
- Out-of-corpus path end-to-end
- Response structure contract matches FastAPI QueryResponse model
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from app.pii_filter import scan as pii_scan
from src.classifier import classify
from src.formatter import format_response, format_refusal, _fallback_response
from src.retriever import RetrievedChunk, RetrievalResult
from src.prompt_builder import build_prompt, assemble_context


# ---------------------------------------------------------------------------
# PII filter (EC-5.1, EC-5.2)
# ---------------------------------------------------------------------------
class TestPIIFilter:
    # --- PAN ---
    def test_pan_detected(self):
        r = pii_scan("My PAN is ABCDE1234F")
        assert r.contains_pii is True
        assert r.pii_type == "PAN"

    def test_pan_lowercase_not_detected(self):
        # PAN must be uppercase — lowercase is not a valid PAN
        r = pii_scan("abcde1234f")
        assert r.contains_pii is False

    def test_pan_in_sentence(self):
        r = pii_scan("Please check my PAN ABCDE1234F for tax purposes")
        assert r.contains_pii is True

    # --- Aadhaar ---
    def test_aadhaar_with_spaces(self):
        r = pii_scan("My Aadhaar is 1234 5678 9012")
        assert r.contains_pii is True
        assert r.pii_type == "Aadhaar"

    def test_aadhaar_with_hyphens(self):
        r = pii_scan("Aadhaar: 1234-5678-9012")
        assert r.contains_pii is True

    def test_aadhaar_no_separator(self):
        r = pii_scan(" 123456789012 ")
        assert r.contains_pii is True

    # --- Phone ---
    def test_indian_phone_detected(self):
        r = pii_scan(" 9876543210 ")
        assert r.contains_pii is True
        assert r.pii_type == "Phone"

    def test_phone_starting_with_6(self):
        r = pii_scan(" 6123456789 ")
        assert r.contains_pii is True

    def test_phone_starting_with_5_not_detected(self):
        # Indian mobile numbers start with 6-9
        r = pii_scan(" 5123456789 ")
        assert r.contains_pii is False

    # --- Email ---
    def test_email_detected(self):
        r = pii_scan("Contact me at user@example.com")
        assert r.contains_pii is True
        assert r.pii_type == "Email"

    def test_email_with_plus(self):
        r = pii_scan("user+tag@domain.co.in")
        assert r.contains_pii is True

    # --- Clean queries ---
    def test_clean_factual_query(self):
        r = pii_scan("What is the expense ratio of HDFC Mid Cap Fund?")
        assert r.contains_pii is False

    def test_clean_query_with_numbers(self):
        r = pii_scan("What is the minimum SIP of Rs 500?")
        assert r.contains_pii is False

    def test_clean_query_with_percentage(self):
        r = pii_scan("Is the expense ratio 0.77% correct?")
        assert r.contains_pii is False

    def test_empty_query(self):
        r = pii_scan("")
        assert r.contains_pii is False

    # --- EC-5.2: normalization ---
    def test_pan_with_extra_spaces_normalized(self):
        r = pii_scan("My PAN is  ABCDE1234F  please check")
        assert r.contains_pii is True


# ---------------------------------------------------------------------------
# Classifier → Formatter: refusal path
# ---------------------------------------------------------------------------
class TestRefusalPath:
    def test_advisory_query_refused(self):
        c = classify("Should I invest in HDFC Mid Cap Fund?")
        assert not c.allowed
        r = format_refusal()
        assert r["refused"] is True
        assert r["source_url"] is None
        assert r["last_updated"] is None

    def test_comparison_query_refused(self):
        c = classify("Compare HDFC Mid Cap and HDFC Large Cap")
        assert not c.allowed
        r = format_refusal()
        assert r["refused"] is True

    def test_refusal_answer_not_empty(self):
        r = format_refusal()
        assert len(r["answer"]) > 0

    def test_refusal_mentions_factual_scope(self):
        r = format_refusal()
        assert "factual" in r["answer"].lower()

    def test_refusal_redirects_to_amfi(self):
        r = format_refusal()
        assert "amfiindia.com" in r["answer"]

    def test_refusal_no_advisory_language_in_answer(self):
        r = format_refusal()
        lower = r["answer"].lower()
        assert "you should" not in lower
        assert "recommended" not in lower
        assert "best" not in lower


# ---------------------------------------------------------------------------
# Classifier → Formatter: out-of-corpus path
# ---------------------------------------------------------------------------
class TestOutOfCorpusPath:
    def test_flexi_cap_is_out_of_corpus(self):
        c = classify("What is the expense ratio of HDFC Flexi Cap Fund?")
        assert c.allowed is True
        assert c.out_of_corpus is True

    def test_out_of_corpus_fallback_no_url(self):
        r = _fallback_response(out_of_corpus=True)
        assert r["source_url"] is None

    def test_out_of_corpus_fallback_is_fallback(self):
        r = _fallback_response(out_of_corpus=True)
        assert r["fallback"] is True

    def test_out_of_corpus_answer_lists_covered_funds(self):
        r = _fallback_response(out_of_corpus=True)
        assert "HDFC Mid Cap" in r["answer"]
        assert "ELSS" in r["answer"]

    def test_out_of_corpus_not_refused(self):
        r = _fallback_response(out_of_corpus=True)
        assert r["refused"] is False


# ---------------------------------------------------------------------------
# Prompt builder with mock chunks
# ---------------------------------------------------------------------------
class TestPromptBuilder:
    def _make_chunk(self, text: str, scheme: str = "HDFC Mid Cap Fund",
                    section: str = "nav_sip_aum", similarity: float = 0.88) -> RetrievedChunk:
        return RetrievedChunk(
            chunk_id="test-id",
            chunk_text=text,
            source_url="https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth",
            scheme_name=scheme,
            fund_category="Mid Cap",
            section_label=section,
            last_updated="2026-05-08",
            similarity=similarity,
            document_type="Groww_Fund_Page",
        )

    def test_build_prompt_returns_system_prompt(self):
        chunk = self._make_chunk("Expense ratio: 0.77%")
        result = build_prompt("What is the expense ratio?", [chunk])
        assert "system_prompt" in result
        assert len(result["system_prompt"]) > 0

    def test_build_prompt_returns_user_prompt(self):
        chunk = self._make_chunk("Expense ratio: 0.77%")
        result = build_prompt("What is the expense ratio?", [chunk])
        assert "user_prompt" in result
        assert "What is the expense ratio?" in result["user_prompt"]

    def test_build_prompt_includes_context(self):
        chunk = self._make_chunk("Expense ratio: 0.77%")
        result = build_prompt("What is the expense ratio?", [chunk])
        assert "Expense ratio: 0.77%" in result["user_prompt"]

    def test_build_prompt_returns_source_url(self):
        chunk = self._make_chunk("Expense ratio: 0.77%")
        result = build_prompt("What is the expense ratio?", [chunk])
        assert result["top_source_url"] == "https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth"

    def test_build_prompt_returns_last_updated(self):
        chunk = self._make_chunk("Expense ratio: 0.77%")
        result = build_prompt("What is the expense ratio?", [chunk])
        assert result["last_updated"] == "2026-05-08"

    def test_build_prompt_empty_chunks(self):
        result = build_prompt("What is the expense ratio?", [])
        assert result["top_source_url"] == ""
        assert result["last_updated"] == "N/A"

    def test_context_budget_respected(self):
        # Create a chunk that's larger than the budget
        large_text = "x" * 2000
        chunk = self._make_chunk(large_text)
        context, _, _ = assemble_context([chunk])
        assert len(context) <= 1500 + 200  # budget + label overhead

    def test_multiple_chunks_assembled(self):
        chunks = [
            self._make_chunk("Expense ratio: 0.77%", similarity=0.90),
            self._make_chunk("Exit load: 1% within 1 year", section="exit_load", similarity=0.85),
        ]
        context, url, date = assemble_context(chunks)
        assert "Expense ratio" in context
        assert "Exit load" in context

    def test_system_prompt_contains_compliance_rules(self):
        chunk = self._make_chunk("Expense ratio: 0.77%")
        result = build_prompt("What is the expense ratio?", [chunk])
        system = result["system_prompt"]
        assert "investment advice" in system.lower()
        assert "3 sentences" in system.lower() or "maximum of 3" in system.lower()
        assert "fallback" in system.lower()


# ---------------------------------------------------------------------------
# Response structure contract (matches FastAPI QueryResponse)
# ---------------------------------------------------------------------------
class TestResponseContract:
    """Verify all response dicts have the required keys for the API contract."""

    REQUIRED_KEYS = {"answer", "source_url", "last_updated", "refused", "fallback"}

    def test_format_response_has_all_keys(self):
        r = format_response(
            "The expense ratio is 0.77%.",
            "https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth",
            "2026-05-08"
        )
        assert self.REQUIRED_KEYS.issubset(r.keys())

    def test_format_refusal_has_all_keys(self):
        r = format_refusal()
        assert self.REQUIRED_KEYS.issubset(r.keys())

    def test_fallback_response_has_all_keys(self):
        r = _fallback_response()
        assert self.REQUIRED_KEYS.issubset(r.keys())

    def test_out_of_corpus_response_has_all_keys(self):
        r = _fallback_response(out_of_corpus=True)
        assert self.REQUIRED_KEYS.issubset(r.keys())

    def test_answer_is_always_string(self):
        for r in [
            format_response("Test.", "https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth", "2026-05-08"),
            format_refusal(),
            _fallback_response(),
        ]:
            assert isinstance(r["answer"], str)
            assert len(r["answer"]) > 0

    def test_refused_and_fallback_are_bool(self):
        for r in [
            format_response("Test.", "https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth", "2026-05-08"),
            format_refusal(),
            _fallback_response(),
        ]:
            assert isinstance(r["refused"], bool)
            assert isinstance(r["fallback"], bool)

    def test_refused_and_fallback_mutually_exclusive(self):
        """A response should never be both refused AND fallback."""
        for r in [
            format_response("Test.", "https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth", "2026-05-08"),
            format_refusal(),
            _fallback_response(),
        ]:
            assert not (r["refused"] and r["fallback"]), (
                f"Response is both refused and fallback: {r}"
            )
