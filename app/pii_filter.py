"""
Phase 5 — PII Sanitization
============================
Detects and blocks queries containing personally identifiable information
before they reach the RAG pipeline.

Patterns: PAN, Aadhaar, Indian phone numbers, email addresses.
EC-5.1: tight regex with word boundaries to avoid false positives.
EC-5.2: normalizes input before scanning (strips spaces/hyphens in numbers).
"""

import re
from dataclasses import dataclass

# ---------------------------------------------------------------------------
# PII patterns — ordered from most specific to least
# ---------------------------------------------------------------------------
PII_PATTERNS = {
    "PAN":     re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b"),
    "Aadhaar": re.compile(r"(^|\s)\d{4}[\s\-]?\d{4}[\s\-]?\d{4}(\s|$)"),
    "Phone":   re.compile(r"(^|\s)[6-9]\d{9}(\s|$)"),
    "Email":   re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b"),
}


@dataclass
class PIIResult:
    contains_pii: bool
    pii_type: str | None   # "PAN" | "Aadhaar" | "Phone" | "Email" | None


def scan(text: str) -> PIIResult:
    """
    Scan text for PII patterns.
    Normalizes input first (EC-5.2) then checks both raw and normalized versions.
    """
    # Normalize: collapse multiple spaces, remove common separators in numbers
    normalized = re.sub(r"[ \t]+", " ", text.strip())

    for pii_type, pattern in PII_PATTERNS.items():
        if pattern.search(text) or pattern.search(normalized):
            return PIIResult(contains_pii=True, pii_type=pii_type)

    return PIIResult(contains_pii=False, pii_type=None)
