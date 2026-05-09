"""
Phase 4 — Step 1: Query Classifier
====================================
Determines whether a user query is allowed (factual) or must be refused
(advisory, comparative, predictive, or suitability-based).

Strategy: rule-based phrase blocklist first (fast, deterministic, auditable).
No ML dependency — compliance-safe by design.

EC-4.1: blocklist uses phrase-level patterns, not isolated words, to avoid
        false positives on words like "best" appearing in factual contexts.
EC-4.2: evaluative adjectives in advisory context are also blocked.
"""

import re
from dataclasses import dataclass

# ---------------------------------------------------------------------------
# Refused query patterns
# Each pattern is a compiled regex. Matching ANY pattern → refuse.
# Patterns use word boundaries and phrase context to avoid false positives.
# ---------------------------------------------------------------------------
_RAW_REFUSED_PATTERNS = [
    # Investment advice
    r"\bshould i invest\b",
    r"\bshould i buy\b",
    r"\bis it worth\b",
    r"\bgood time to invest\b",
    r"\bright time to invest\b",
    r"\bworth investing\b",

    # Comparisons
    r"\bcompare\b",
    r"\bfund\b.{0,20}\bvs\b.{0,20}\bfund\b",
    r"\bhdfc\b.{0,20}\bvs\b",
    r"\bbetter than\b",
    r"\bwhich is better\b",
    r"\bwhich fund is best\b",
    r"\bwhich sip\b",
    r"\bwhich scheme\b.{0,30}\bbetter\b",

    # Rankings
    r"\bbest fund\b",
    r"\bbest performing\b",
    r"\btop fund\b",
    r"\btop performing\b",
    r"\bsafest fund\b",
    r"\bhighest return\b",
    r"\bbest sip\b",
    r"\bbest mutual fund\b",

    # Predictions / forecasts
    r"\bwill it grow\b",
    r"\bwill\b.{0,80}\bgrow\b",
    r"\bexpected returns\b",
    r"\bfuture returns\b",
    r"\bbeat inflation\b",
    r"\bwill outperform\b",
    r"\bwill\b.{0,80}\boutperform\b",
    r"\bprice prediction\b",
    r"\bmarket prediction\b",
    r"\bgive good returns\b",
    r"\bgive returns\b",
    r"\bwhat returns\b",
    r"\bhow much returns\b",
    r"\bwill.*return\b",

    # Suitability / recommendations
    r"\bsuit[s]? my goals\b",
    r"\bright for me\b",
    r"\bsuitable for me\b",
    r"\brecommend\b",
    r"\badvise\b",
    r"\bshould i\b",
    r"\bcan i trust\b",

    # Evaluative / opinion
    r"\bis it safe\b",
    r"\bis\b.{0,80}\bsafe\b",
    r"\bis it good\b",
    r"\bis it reliable\b",
    r"\bworth it\b",
    r"\bgood investment\b",
    r"\bsafe investment\b",
]

REFUSED_PATTERNS = [re.compile(p, re.IGNORECASE) for p in _RAW_REFUSED_PATTERNS]

# Phrases that are safe even if they contain blocklist-adjacent words
# e.g. "what is the best way to check" — "best" here is not advisory
_SAFE_OVERRIDE_PATTERNS = [
    re.compile(r"\bbest way to (check|download|access|find|view|get)\b", re.IGNORECASE),
    re.compile(r"\bbest time to (check|download|access)\b", re.IGNORECASE),
]

# ---------------------------------------------------------------------------
# Known scheme names — used to detect out-of-corpus queries (EC-4.13)
# ---------------------------------------------------------------------------
KNOWN_SCHEMES = [
    "hdfc mid cap fund",
    "hdfc equity fund",
    "hdfc focused fund",
    "hdfc elss tax saver fund",
    "hdfc elss",
    "hdfc large cap fund",
]

# Canonical slug → display name map
SCHEME_DISPLAY_NAMES = {
    "hdfc mid cap fund": "HDFC Mid Cap Fund Direct Growth",
    "hdfc equity fund": "HDFC Equity Fund Direct Growth",
    "hdfc focused fund": "HDFC Focused Fund Direct Growth",
    "hdfc elss tax saver fund": "HDFC ELSS Tax Saver Fund Direct Plan Growth",
    "hdfc elss": "HDFC ELSS Tax Saver Fund Direct Plan Growth",
    "hdfc large cap fund": "HDFC Large Cap Fund Direct Growth",
}


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------
@dataclass
class ClassifierResult:
    allowed: bool
    reason: str                  # "allowed" | "advisory" | "comparison" | etc.
    matched_pattern: str | None  # the pattern that triggered refusal, for logging
    detected_scheme: str | None  # scheme name if detected in query
    out_of_corpus: bool          # True if query mentions a fund not in our 5


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def classify(query: str) -> ClassifierResult:
    """
    Classify a user query as allowed or refused.

    Returns a ClassifierResult with full context for logging and response routing.
    """
    query_lower = query.lower().strip()

    # --- Safe override check (EC-4.1 — prevent false positives) ---
    for safe_pattern in _SAFE_OVERRIDE_PATTERNS:
        if safe_pattern.search(query_lower):
            scheme = _detect_scheme(query_lower)
            return ClassifierResult(
                allowed=True,
                reason="allowed",
                matched_pattern=None,
                detected_scheme=scheme,
                out_of_corpus=_is_out_of_corpus(query_lower, scheme),
            )

    # --- Blocklist check ---
    for pattern in REFUSED_PATTERNS:
        if pattern.search(query_lower):
            return ClassifierResult(
                allowed=False,
                reason="advisory_or_comparative",
                matched_pattern=pattern.pattern,
                detected_scheme=None,
                out_of_corpus=False,
            )

    # --- Allowed: detect scheme and corpus coverage ---
    scheme = _detect_scheme(query_lower)
    out_of_corpus = _is_out_of_corpus(query_lower, scheme)

    return ClassifierResult(
        allowed=True,
        reason="allowed",
        matched_pattern=None,
        detected_scheme=scheme,
        out_of_corpus=out_of_corpus,
    )


def _detect_scheme(query_lower: str) -> str | None:
    """
    Extract a known scheme name from the query if present.
    Returns the canonical display name or None.
    """
    for slug, display in SCHEME_DISPLAY_NAMES.items():
        if slug in query_lower:
            return display
    return None


def _is_out_of_corpus(query_lower: str, detected_scheme: str | None) -> bool:
    """
    Returns True if the query mentions an HDFC fund that is NOT in our 5 indexed schemes.
    EC-4.13: out-of-corpus queries get a soft fallback, not a retrieval attempt.
    """
    # If a known scheme was detected, it's in corpus
    if detected_scheme is not None:
        return False

    # If query mentions "hdfc" + a fund-like term but no known scheme matched,
    # it's likely asking about an out-of-corpus HDFC fund
    if "hdfc" in query_lower and any(
        kw in query_lower for kw in ["fund", "scheme", "sip", "nav", "elss", "cap"]
    ):
        return True

    return False
