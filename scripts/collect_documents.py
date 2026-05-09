"""
Phase 1 — Data Collection & Corpus Building
============================================
Scrapes the 5 approved HDFC fund pages from Groww using a headless browser
(Playwright), validates the extracted content, and saves raw HTML to /data/raw/.
Updates source_registry.json with provenance metadata for every fetch.

Usage:
    python scripts/collect_documents.py
    python scripts/collect_documents.py --force   # re-fetch even if already done
"""

import argparse
import json
import logging
import os
import time
from datetime import datetime
from pathlib import Path

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = BASE_DIR / "data" / "raw"
REGISTRY_PATH = BASE_DIR / "data" / "source_registry.json"

# The 5 approved source URLs — these are the ONLY data sources for this project
APPROVED_SOURCES = [
    {
        "scheme_name": "HDFC Mid Cap Fund",
        "fund_category": "Mid Cap",
        "amc_name": "HDFC Mutual Fund",
        "url": "https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth",
        "slug": "hdfc-mid-cap-fund-direct-growth",
    },
    {
        "scheme_name": "HDFC Equity Fund",
        "fund_category": "Flexi Cap",
        "amc_name": "HDFC Mutual Fund",
        "url": "https://groww.in/mutual-funds/hdfc-equity-fund-direct-growth",
        "slug": "hdfc-equity-fund-direct-growth",
    },
    {
        "scheme_name": "HDFC Focused Fund",
        "fund_category": "Focused Fund",
        "amc_name": "HDFC Mutual Fund",
        "url": "https://groww.in/mutual-funds/hdfc-focused-fund-direct-growth",
        "slug": "hdfc-focused-fund-direct-growth",
    },
    {
        "scheme_name": "HDFC ELSS Tax Saver Fund",
        "fund_category": "ELSS",
        "amc_name": "HDFC Mutual Fund",
        "url": "https://groww.in/mutual-funds/hdfc-elss-tax-saver-fund-direct-plan-growth",
        "slug": "hdfc-elss-tax-saver-fund-direct-plan-growth",
    },
    {
        "scheme_name": "HDFC Large Cap Fund",
        "fund_category": "Large Cap",
        "amc_name": "HDFC Mutual Fund",
        "url": "https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth",
        "slug": "hdfc-large-cap-fund-direct-growth",
    },
]

# Validation: these keywords must appear in the extracted text for a page to be
# considered successfully scraped (EC-1.2 guard against empty JS renders)
REQUIRED_KEYWORDS = ["expense ratio", "exit load", "nav", "sip", "fund"]

# Minimum file size in bytes to guard against truncated fetches (EC-1.6)
MIN_FILE_SIZE_BYTES = 5_000

# Retry settings (EC-1.1, EC-1.7)
MAX_RETRIES = 3
RETRY_DELAYS = [5, 15, 30]  # seconds between retries

# Delay between requests to avoid rate limiting (EC-1.7)
REQUEST_DELAY_SECONDS = 4

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(BASE_DIR / "data" / "collection.log", mode="a"),
    ],
)
log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Registry helpers
# ---------------------------------------------------------------------------

def load_registry() -> dict:
    """Load source_registry.json, returning an empty dict if it doesn't exist."""
    if REGISTRY_PATH.exists():
        try:
            with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            log.warning("source_registry.json is corrupted — starting fresh.")
            _backup_registry()
    return {}


def save_registry(registry: dict) -> None:
    """Atomically write registry to disk (EC-1.9 — atomic write via temp file)."""
    tmp_path = REGISTRY_PATH.with_suffix(".tmp")
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(registry, f, indent=2, ensure_ascii=False)
    tmp_path.replace(REGISTRY_PATH)

    # Keep a backup copy (EC-1.9)
    backup_path = REGISTRY_PATH.with_name("source_registry.backup.json")
    with open(backup_path, "w", encoding="utf-8") as f:
        json.dump(registry, f, indent=2, ensure_ascii=False)


def _backup_registry() -> None:
    """Back up a potentially corrupted registry before overwriting."""
    if REGISTRY_PATH.exists():
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup = REGISTRY_PATH.with_name(f"source_registry.corrupted_{ts}.json")
        REGISTRY_PATH.rename(backup)
        log.info(f"Corrupted registry backed up to {backup.name}")


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

def validate_content(text: str, slug: str) -> tuple[bool, str]:
    """
    Validate that extracted page text contains expected financial keywords.
    Returns (is_valid, reason).
    Guards against EC-1.2 (empty JS render) and EC-1.8 (disclaimer-only pages).
    """
    text_lower = text.lower()
    missing = [kw for kw in REQUIRED_KEYWORDS if kw not in text_lower]
    if missing:
        return False, f"Missing required keywords: {missing}"
    if len(text) < MIN_FILE_SIZE_BYTES:
        return False, f"Content too short: {len(text)} chars (min {MIN_FILE_SIZE_BYTES})"
    return True, "ok"


def is_disclaimer_only(text: str) -> bool:
    """
    Detect pages that contain only legal disclaimers with no fund data (EC-1.8).
    """
    text_lower = text.lower()
    has_data_fields = any(
        kw in text_lower for kw in ["expense ratio", "exit load", "minimum investment", "benchmark"]
    )
    return not has_data_fields


# ---------------------------------------------------------------------------
# Core scraper
# ---------------------------------------------------------------------------

def fetch_page(url: str, slug: str, page) -> tuple[str | None, str]:
    """
    Use Playwright to render the JS-heavy Groww page and extract visible text.
    Returns (text_content, status_string).
    Handles EC-1.2 (JS rendering), EC-1.6 (truncated load), EC-1.7 (rate limit).

    Strategy:
    1. Navigate and wait for DOM content
    2. Scroll the page to trigger lazy-loaded sections
    3. Wait for key financial data selectors to appear
    4. Extract full page text
    """
    try:
        log.info(f"  Navigating to: {url}")
        page.goto(url, wait_until="domcontentloaded", timeout=60_000)

        # Give the React app time to mount initial components
        page.wait_for_timeout(3000)

        # Scroll down in steps to trigger lazy-loaded sections (Groww uses
        # intersection-observer based lazy loading for fund data panels)
        log.info("  Scrolling page to trigger lazy-loaded content...")
        for scroll_pos in [500, 1000, 1500, 2000, 2500, 3000, 4000]:
            page.evaluate(f"window.scrollTo(0, {scroll_pos})")
            page.wait_for_timeout(800)

        # Scroll back to top
        page.evaluate("window.scrollTo(0, 0)")
        page.wait_for_timeout(1000)

        # Wait for key financial data to appear in the DOM
        # Try multiple selectors — Groww's class names change but text content is stable
        content_found = False
        wait_selectors = [
            "text=Expense Ratio",
            "text=Exit Load",
            "text=Minimum SIP",
            "text=Fund Category",
        ]
        for selector in wait_selectors:
            try:
                page.wait_for_selector(selector, timeout=8_000)
                log.info(f"  Content confirmed via selector: '{selector}'")
                content_found = True
                break
            except PlaywrightTimeout:
                continue

        if not content_found:
            log.warning(f"  No content selectors matched for {slug} — extracting anyway")

        # Additional wait after content detection to let remaining panels load
        page.wait_for_timeout(2000)

        # Extract full visible text from the page body
        text = page.inner_text("body")

        if not text or len(text.strip()) < 100:
            return None, "empty_render"

        log.info(f"  Extracted {len(text):,} chars from page")
        return text, "ok"

    except PlaywrightTimeout:
        return None, "timeout"
    except Exception as e:
        return None, f"error: {str(e)}"


def scrape_source(source: dict, registry: dict, force: bool, browser) -> dict:
    """
    Scrape a single source URL with retry logic.
    Returns an updated registry entry for this source.
    """
    slug = source["slug"]
    url = source["url"]
    output_path = RAW_DIR / f"{slug}.txt"

    # Skip if already successfully fetched and not forcing (EC-1.4)
    if not force and slug in registry and registry[slug].get("status") == "success":
        log.info(f"[SKIP] {slug} — already fetched. Use --force to re-fetch.")
        return registry[slug]

    log.info(f"[FETCH] {source['scheme_name']} ({slug})")

    entry = {
        "slug": slug,
        "scheme_name": source["scheme_name"],
        "fund_category": source["fund_category"],
        "amc_name": source["amc_name"],
        "source_url": url,
        "document_type": "Groww_Fund_Page",
        "download_date": datetime.now().isoformat(),
        "status": "pending",
        "output_file": str(output_path.relative_to(BASE_DIR)),
        "error": None,
    }

    text = None
    last_status = "pending"

    for attempt in range(1, MAX_RETRIES + 1):
        log.info(f"  Attempt {attempt}/{MAX_RETRIES}...")
        page = browser.new_page()

        try:
            # Set a realistic user agent to reduce bot detection (EC-1.7)
            page.set_extra_http_headers({
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                )
            })

            text, last_status = fetch_page(url, slug, page)

            if last_status == "ok" and text:
                break  # Success — exit retry loop

            log.warning(f"  Attempt {attempt} failed: {last_status}")

        finally:
            page.close()

        if attempt < MAX_RETRIES:
            delay = RETRY_DELAYS[attempt - 1]
            log.info(f"  Retrying in {delay}s...")
            time.sleep(delay)

    # --- Post-fetch validation ---
    if text is None:
        entry["status"] = last_status
        entry["error"] = f"All {MAX_RETRIES} attempts failed with status: {last_status}"
        log.error(f"  [FAILED] {slug}: {entry['error']}")
        return entry

    # Check for disclaimer-only content (EC-1.8)
    if is_disclaimer_only(text):
        entry["status"] = "disclaimer_only"
        entry["error"] = "Page contains only disclaimer text — no fund data found."
        log.warning(f"  [DISCLAIMER_ONLY] {slug}")
        return entry

    # Validate required keywords and minimum size (EC-1.2, EC-1.6)
    is_valid, reason = validate_content(text, slug)
    if not is_valid:
        entry["status"] = "validation_failed"
        entry["error"] = reason
        log.warning(f"  [VALIDATION_FAILED] {slug}: {reason}")
        return entry

    # --- Save to disk ---
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(text)

    entry["status"] = "success"
    entry["file_size_bytes"] = len(text.encode("utf-8"))
    entry["char_count"] = len(text)
    log.info(f"  [SUCCESS] {slug} — {entry['char_count']:,} chars saved to {output_path.name}")

    return entry


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Phase 1: Collect HDFC fund pages from Groww")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-fetch all URLs even if already present in the registry",
    )
    args = parser.parse_args()

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    (BASE_DIR / "data").mkdir(parents=True, exist_ok=True)

    registry = load_registry()
    log.info(f"Loaded registry with {len(registry)} existing entries.")

    results = {"success": 0, "skipped": 0, "failed": 0}

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        log.info("Chromium browser launched (headless).")

        try:
            for i, source in enumerate(APPROVED_SOURCES):
                entry = scrape_source(source, registry, args.force, browser)
                registry[source["slug"]] = entry

                # Save registry after every fetch (EC-1.9 — incremental persistence)
                save_registry(registry)

                if entry["status"] == "success":
                    results["success"] += 1
                elif entry["status"] == "pending" or "skip" in entry.get("error", ""):
                    results["skipped"] += 1
                else:
                    results["failed"] += 1

                # Polite delay between requests (EC-1.7)
                if i < len(APPROVED_SOURCES) - 1:
                    log.info(f"  Waiting {REQUEST_DELAY_SECONDS}s before next request...")
                    time.sleep(REQUEST_DELAY_SECONDS)

        finally:
            browser.close()
            log.info("Browser closed.")

    # --- Final summary ---
    log.info("\n" + "=" * 50)
    log.info("Phase 1 Collection Summary")
    log.info("=" * 50)
    log.info(f"  Total sources : {len(APPROVED_SOURCES)}")
    log.info(f"  Successful    : {results['success']}")
    log.info(f"  Skipped       : {results['skipped']}")
    log.info(f"  Failed        : {results['failed']}")
    log.info(f"  Registry      : {REGISTRY_PATH}")
    log.info(f"  Raw files     : {RAW_DIR}")

    if results["failed"] > 0:
        log.warning(
            f"\n  WARNING: {results['failed']} source(s) failed. "
            "Phase 2 will have incomplete coverage. Check collection.log for details."
        )

    return results["failed"] == 0


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
