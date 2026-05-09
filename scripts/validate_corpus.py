"""
Phase 1 — Corpus Validation
=============================
Validates the collected raw files against the source registry.
Run after collect_documents.py to confirm Phase 1 is complete before
proceeding to Phase 2.

Usage:
    python scripts/validate_corpus.py
"""

import json
import logging
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = BASE_DIR / "data" / "raw"
REGISTRY_PATH = BASE_DIR / "data" / "source_registry.json"

REQUIRED_KEYWORDS = ["expense ratio", "exit load", "nav", "sip", "fund"]

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)


def validate_corpus() -> bool:
    """
    Validate all collected raw files.
    Returns True if all 5 sources are present and valid.
    """
    if not REGISTRY_PATH.exists():
        log.error("source_registry.json not found. Run collect_documents.py first.")
        return False

    with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
        registry = json.load(f)

    log.info(f"Registry contains {len(registry)} entries.")

    all_valid = True
    report = []

    # Skip metadata keys that are not scheme entries
    scheme_entries = {k: v for k, v in registry.items()
                      if not k.startswith("_") and isinstance(v, dict)}

    log.info(f"Found {len(scheme_entries)} scheme entries to validate.")

    for slug, entry in scheme_entries.items():
        status = entry.get("status", "unknown")
        output_file = BASE_DIR / entry.get("output_file", "")

        checks = {
            "registry_status": status == "success",
            "file_exists": output_file.exists(),
            "file_non_empty": False,
            "keywords_present": False,
        }

        if checks["file_exists"]:
            text = output_file.read_text(encoding="utf-8")
            checks["file_non_empty"] = len(text) > 1000
            text_lower = text.lower()
            checks["keywords_present"] = all(kw in text_lower for kw in REQUIRED_KEYWORDS)

        passed = all(checks.values())
        all_valid = all_valid and passed

        icon = "✓" if passed else "✗"
        report.append({
            "slug": slug,
            "scheme_name": entry.get("scheme_name"),
            "status": status,
            "passed": passed,
            "checks": checks,
        })

        log.info(f"  [{icon}] {entry.get('scheme_name', slug)}")
        if not passed:
            for check_name, result in checks.items():
                if not result:
                    log.warning(f"       FAIL: {check_name}")

    log.info("\n" + "=" * 50)
    passed_count = sum(1 for r in report if r["passed"])
    log.info(f"Validation: {passed_count}/{len(scheme_entries)} sources passed")

    if all_valid:
        log.info("Phase 1 corpus is COMPLETE. Ready for Phase 2.")
    else:
        log.error("Phase 1 corpus is INCOMPLETE. Fix failures before running Phase 2.")

    # Save validation report
    report_path = BASE_DIR / "data" / "validation_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    log.info(f"Validation report saved to {report_path}")

    return all_valid


if __name__ == "__main__":
    success = validate_corpus()
    exit(0 if success else 1)
