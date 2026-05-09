"""
Phase 4 — Step 7: Response Formatter
======================================
Post-processes the raw LLM output to enforce compliance rules:
  1. 3-sentence cap
  2. Source citation injection
  3. Last-updated date footer
  4. Prohibited language scan — regenerate or fallback if detected
  5. Source URL validation — never show a URL for out-of-corpus or fallback responses

EC-4.5: prohibited language scan catches advisory phrases that slipped through.
EC-4.6: sentence cap enforced via nltk sentence tokenizer.
EC-5.11: source URL only rendered when it's a valid https:// URL from our corpus.
"""

import logging
import re

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Prohibited language patterns (EC-4.5)
# If any match → response is flagged for regeneration or fallback
# ---------------------------------------------------------------------------
_RAW_PROHIBITED = [
    r"\byou should\b",
    r"\byou must\b",
    r"\bi recommend\b",
    r"\brecommended\b",
    r"\bbest fund\b",
    r"\bbest option\b",
    r"\bbest choice\b",
    r"\bsafe investment\b",
    r"\bgood option\b",
    r"\bgood investment\b",
    r"\bperforms well\b",
    r"\bsuits your goals\b",
    r"\bsuitable for you\b",
    r"\badvised\b",
    r"\bwise choice\b",
    r"\bperfect for\b",
    r"\bideal for\b",
    r"\bgreat choice\b",
]
PROHIBITED_PATTERNS = [re.compile(p, re.IGNORECASE) for p in _RAW_PROHIBITED]

# Approved source URL prefix — only URLs from our corpus are shown
APPROVED_URL_PREFIX = "https://groww.in/mutual-funds/"

# Fallback response — used when context is insufficient or generation fails
FALLBACK_ANSWER = (
    "Verified information for this query could not be found in the indexed sources. "
    "Please refer directly to the fund page for accurate details."
)


# ---------------------------------------------------------------------------
# Sentence splitting (simple, no nltk dependency)
# ---------------------------------------------------------------------------
def _split_sentences(text: str) -> list[str]:
    """Split text into sentences using punctuation boundaries."""
    # Split on . ! ? followed by whitespace or end of string
    parts = re.split(r'(?<=[.!?])\s+', text.strip())
    return [p.strip() for p in parts if p.strip()]


# ---------------------------------------------------------------------------
# Core formatting
# ---------------------------------------------------------------------------
def format_response(
    raw_text: str | None,
    source_url: str,
    last_updated: str,
    is_fallback: bool = False,
    out_of_corpus: bool = False,
) -> dict:
    """
    Format the LLM output into a compliant final response.

    Args:
        raw_text:      Raw text from the LLM (None if generation failed).
        source_url:    Top chunk's source URL from metadata.
        last_updated:  Date string from top chunk's metadata.
        is_fallback:   True if retrieval triggered fallback (no good chunks).
        out_of_corpus: True if query was about a fund not in our index.

    Returns dict with:
        answer, source_url, last_updated, refused, fallback, prohibited_detected
    """
    # --- Fallback cases: no source URL shown (EC-5.11, user instruction) ---
    if is_fallback or out_of_corpus or raw_text is None:
        return _fallback_response(out_of_corpus=out_of_corpus)
    # --- Prohibited language scan (EC-4.5) ---
    prohibited_detected = _scan_prohibited(raw_text)
    if prohibited_detected:
        log.warning(f"Prohibited language detected in LLM output: '{prohibited_detected}'")
        return _fallback_response()

    # --- Sentence cap: max 3 sentences (EC-4.6) ---
    sentences = _split_sentences(raw_text)
    # Strip any "Source:" or "Last updated" lines the LLM may have added itself
    sentences = [
        s for s in sentences
        if not s.lower().startswith("source:")
        and not s.lower().startswith("last updated")
    ]
    capped = " ".join(sentences[:3])

    # --- Validate source URL (EC-5.11) ---
    # Only show URL if it's from our approved corpus
    safe_url = _validate_url(source_url)

    # --- Build final answer with footer ---
    answer = capped.strip()
    if not answer.endswith((".", "!", "?")):
        answer += "."

    return {
        "answer": answer,
        "source_url": safe_url,
        "last_updated": last_updated or "N/A",
        "refused": False,
        "fallback": False,
        "prohibited_detected": False,
    }


def format_refusal() -> dict:
    """
    Format a refusal response for advisory/comparative queries.
    No source URL — AMFI education link is provided in the answer text itself.
    """
    return {
        "answer": (
            "This assistant provides factual, source-backed information about "
            "HDFC Mutual Fund schemes only. "
            "Queries involving investment advice, comparisons, rankings, or "
            "recommendations are outside its scope. "
            "For investor education, visit: https://www.amfiindia.com/investor-corner/knowledge-center"
        ),
        "source_url": None,
        "last_updated": None,
        "refused": True,
        "fallback": False,
        "prohibited_detected": False,
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _fallback_response(out_of_corpus: bool = False) -> dict:
    """
    Soft fallback — no source URL shown (EC-5.11, user instruction:
    'for things we don't have stored, don't show irrelevant URL').
    """
    if out_of_corpus:
        answer = (
            "Verified information for this fund could not be found in the indexed sources. "
            "The assistant currently covers HDFC Mid Cap, Equity, Focused, ELSS Tax Saver, "
            "and Large Cap funds (Direct Growth). "
            "Please refer directly to the fund page on Groww for accurate details."
        )
    else:
        answer = FALLBACK_ANSWER

    return {
        "answer": answer,
        "source_url": None,       # No URL for fallback — never show irrelevant link
        "last_updated": None,
        "refused": False,
        "fallback": True,
        "prohibited_detected": False,
    }


def _scan_prohibited(text: str) -> str | None:
    """
    Scan text for prohibited advisory phrases.
    Returns the matched phrase string if found, else None.
    """
    for pattern in PROHIBITED_PATTERNS:
        match = pattern.search(text)
        if match:
            return match.group(0)
    return None


def _validate_url(url: str) -> str | None:
    """
    Only return the URL if it starts with our approved corpus prefix.
    Prevents irrelevant or fabricated URLs from appearing in responses.
    EC-5.11: never render non-https or non-corpus URLs.
    """
    if url and url.startswith(APPROVED_URL_PREFIX):
        return url
    return None
