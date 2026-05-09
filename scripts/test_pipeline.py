"""
Phase 4 — End-to-End Pipeline Test
Runs 8 allowed queries + 4 refused queries + 2 out-of-corpus queries.
Prints results clearly. Run with: python scripts/test_pipeline.py
"""
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
logging.basicConfig(level=logging.WARNING)  # suppress debug noise during test

from src.rag_pipeline import run_pipeline

ALLOWED = [
    "What is the exit load for HDFC ELSS Tax Saver Fund?",
    "What is the expense ratio of HDFC Mid Cap Fund?",
    "What is the minimum SIP amount for HDFC Large Cap Fund?",
    "What is the lock-in period of HDFC ELSS Tax Saver Fund?",
    "What is the benchmark index of HDFC Equity Fund?",
    "What is the NAV of HDFC Focused Fund?",
    "What is the fund category of HDFC Mid Cap Fund?",
    "What is the AUM of HDFC Large Cap Fund?",
]

REFUSED = [
    "Which HDFC fund should I invest in?",
    "Is HDFC Mid Cap Fund better than HDFC Large Cap Fund?",
    "Will HDFC ELSS give good returns?",
    "Which is the best SIP to start?",
]

OUT_OF_CORPUS = [
    "What is the expense ratio of HDFC Flexi Cap Fund?",
    "What is the NAV of HDFC Small Cap Fund?",
]

SEP = "-" * 70

import time

def run_tests():
    passed = 0
    failed = 0
    REQUEST_DELAY = 2.5  # seconds between API calls — stays under 30 RPM free tier

    print(f"\n{'='*70}")
    print("PHASE 4 — END-TO-END PIPELINE TEST")
    print(f"{'='*70}\n")

    # --- Allowed queries ---
    print(f"[ALLOWED QUERIES — expect factual answers]\n{SEP}")
    for q in ALLOWED:
        r = run_pipeline(q)
        ok = not r.refused and not r.fallback and r.answer
        status = "PASS" if ok else "FAIL"
        if ok: passed += 1
        else: failed += 1
        print(f"[{status}] {q}")
        print(f"  Answer   : {r.answer[:120]}...")
        print(f"  Source   : {r.source_url or 'None'}")
        print(f"  Updated  : {r.last_updated}")
        print(f"  Scheme   : {r.detected_scheme or 'not detected'}")
        print()
        time.sleep(REQUEST_DELAY)

    # --- Refused queries ---
    print(f"\n[REFUSED QUERIES — expect refusal]\n{SEP}")
    for q in REFUSED:
        r = run_pipeline(q)
        ok = r.refused
        status = "PASS" if ok else "FAIL"
        if ok: passed += 1
        else: failed += 1
        print(f"[{status}] {q}")
        print(f"  Answer   : {r.answer[:120]}...")
        print(f"  Source   : {r.source_url or 'None (correct)'}")
        print()

    # --- Out-of-corpus queries ---
    print(f"\n[OUT-OF-CORPUS QUERIES — expect soft fallback, no URL]\n{SEP}")
    for q in OUT_OF_CORPUS:
        r = run_pipeline(q)
        ok = r.fallback and r.source_url is None
        status = "PASS" if ok else "FAIL"
        if ok: passed += 1
        else: failed += 1
        print(f"[{status}] {q}")
        print(f"  Answer   : {r.answer[:120]}...")
        print(f"  Source   : {r.source_url or 'None (correct — no irrelevant URL)'}")
        print()

    total = len(ALLOWED) + len(REFUSED) + len(OUT_OF_CORPUS)
    print(f"\n{'='*70}")
    print(f"RESULTS: {passed}/{total} passed")
    print(f"{'='*70}\n")
    return failed == 0

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
