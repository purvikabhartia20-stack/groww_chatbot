"""
Phase 2 — Document Processing & Chunking Pipeline
===================================================
Reads raw .txt files from /data/raw/, cleans them, detects sections,
produces semantically meaningful chunks, and writes /data/processed/chunks.jsonl.

Chunking strategy (chosen after inspecting actual Groww page structure):
  - Pages are ~10KB plain text with label-value pairs, tab-separated tables,
    and FAQ prose blocks — NOT paragraph-heavy documents.
  - Strategy: SECTION-BOUNDARY chunking.
      1. Strip nav/footer boilerplate.
      2. Detect named section anchors from the actual page layout.
      3. Group all lines under each section into one chunk.
      4. FAQ section: split each individual Q&A pair into its own chunk.
      5. Holdings table: one chunk per holdings block (top holdings + sector split).
  - No sliding-window needed — each section fits well within 500 tokens.
  - Overlap is applied only between adjacent non-FAQ sections (50-token tail
    of previous section prepended to next) to preserve cross-section context.

Usage:
    python scripts/process_documents.py
    python scripts/process_documents.py --force   # reprocess even if chunks exist
"""

import argparse
import json
import logging
import re
import uuid
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = BASE_DIR / "data" / "raw"
PROCESSED_DIR = BASE_DIR / "data" / "processed"
CHUNKS_PATH = PROCESSED_DIR / "chunks.jsonl"
PROCESSING_LOG_PATH = PROCESSED_DIR / "processing_log.json"
REGISTRY_PATH = BASE_DIR / "data" / "source_registry.json"

# ---------------------------------------------------------------------------
# Chunking constants
# ---------------------------------------------------------------------------
OVERLAP_LINES = 3          # lines of previous section to prepend as overlap
MIN_CHUNK_LINES = 2        # discard chunks with fewer lines than this (EC-2.6)

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(BASE_DIR / "data" / "processing.log", mode="a"),
    ],
)
log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Boilerplate markers
# ---------------------------------------------------------------------------

# Lines that mark the START of useful content (fund name is the first real line)
# Everything before the fund name line is nav/header boilerplate.
HEADER_NOISE_PATTERNS = [
    r"^Stocks$", r"^F&O$", r"^Mutual Funds$", r"^More$",
    r"^Search Groww", r"^Ctrl\+K$", r"^Login/Sign up$",
]

# Lines that mark the START of footer boilerplate — everything from here down is noise
FOOTER_START_MARKERS = [
    "Looking to invest in mutual funds?",
    "Explore diversified funds designed for every investor",
    "Vaishnavi Tech Park",
    "© 2016-",
    "Home\n>\nMutual Funds",
]

# Lines to drop anywhere in the document (noise that appears mid-page)
INLINE_NOISE_PATTERNS = [
    r"^\d+$",                          # lone digit lines (from animated counter)
    r"^\.$",                           # lone period
    r"^[+\-]$",                        # lone sign
    r"^%$",                            # lone percent
    r"^See All$",
    r"^Compare$",
    r"^Invest Now$",
    r"^View details$",
    r"^\.\.\. ?Read more$",
    r"^Check past data$",
    r"^Compare similar funds$",
    r"^Scheme Information Document\(SID\)$",
    r"^Other plans in the same fund$",
    r"^Name$",                         # orphan table header
    r"^Rating$",
    r"^Return calculator$",
    r"^Monthly SIP$",
    r"^One time$",
    r"^Monthly investment$",
    r"^Annualised returns$",
    r"^Absolute returns$",
    r"^Holdings analysis$",
    r"^Advanced ratios$",
    r"^Returns and rankings$",
    r"^Also manages these schemes$",   # fund manager cross-scheme list header
]

# Lines that are part of the "Also manages these schemes" block.
# These are other HDFC fund names listed under a fund manager — not data about
# the current scheme. We detect this block and drop it entirely.
ALSO_MANAGES_START = re.compile(r"^Also manages these schemes$")
ALSO_MANAGES_LINE = re.compile(r"^HDFC .+ (Fund|Plan|Growth|Debt|Liquid|Overnight|Money Market) ?(Direct|Wholesale)? ?(Plan|Growth|IDCW|Fund)?")  

# ---------------------------------------------------------------------------
# Section detection
# ---------------------------------------------------------------------------

# Ordered list of (section_label, trigger_pattern).
# The FIRST pattern that matches a line opens that section.
# Sections are closed when the next section opens.
# NOTE: fund_basics only fires on the page title line (contains risk rating inline)
SECTION_ANCHORS = [
    ("fund_basics",         r"^HDFC .+ (Fund|Plan) .+"),
    ("nav_sip_aum",         r"^NAV:"),
    ("return_calculator",   r"^Over the past\s+Total investment"),
    ("holdings",            r"^Holdings \(\d+\)"),
    ("holdings_analysis",   r"^Equity / Debt / Cash split"),
    ("sector_allocation",   r"^Equity sector allocation"),
    ("advanced_ratios",     r"^Top 5$"),
    ("minimum_investment",  r"^Minimum investments$"),
    ("returns_rankings",    r"^Name\s+3Y\s+5Y"),
    ("exit_load",           r"^Exit load, stamp duty and tax$"),
    ("similar_funds",       r"^\s*Name\s+1Y\s+3Y\s+Fund Size"),
    ("fund_management",     r"^Fund management$"),
    ("about",               r"^About HDFC"),
    ("investment_objective",r"^Investment Objective$"),
    ("fund_info",           r"^Fund benchmark$"),
    ("fund_house_details",  r"^Fund house$"),
    ("faq",                 r"^FAQs$"),
]

# Sections to EXCLUDE entirely — not useful for RAG (noise, comparisons, boilerplate)
EXCLUDED_SECTIONS = {
    "return_calculator",   # historical return table with no factual labels
    "similar_funds",       # competitor fund comparison — out of scope
    "fund_management",     # fund manager bio — not factual fund data
}

# FAQ sections get split per Q&A pair instead of kept as one block
FAQ_QUESTION_PATTERN = re.compile(
    r"^(How to|What is|What kind|What are|Can I|How much|Is there|Who is|When)",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Text cleaning helpers
# ---------------------------------------------------------------------------

def is_header_noise(line: str) -> bool:
    return any(re.match(p, line.strip()) for p in HEADER_NOISE_PATTERNS)


def is_inline_noise(line: str) -> bool:
    return any(re.match(p, line.strip()) for p in INLINE_NOISE_PATTERNS)


def strip_boilerplate(lines: list[str]) -> list[str]:
    """
    Remove header nav, footer boilerplate, and the 'Also manages these schemes'
    cross-fund list that appears under each fund manager biography.
    """
    # Find fund name line — first line matching "HDFC ... Fund ..."
    fund_name_idx = 0
    for i, line in enumerate(lines):
        if re.match(r"^HDFC .+ (Fund|Plan) .+", line.strip()):
            fund_name_idx = i
            break

    lines = lines[fund_name_idx:]

    # Find footer start
    footer_idx = len(lines)
    for i, line in enumerate(lines):
        for marker in FOOTER_START_MARKERS:
            if marker in line:
                footer_idx = i
                break
        if footer_idx < len(lines):
            break

    lines = lines[:footer_idx]

    # Drop inline noise lines AND the "Also manages these schemes" block.
    # The block starts at "Also manages these schemes" and continues while lines
    # match the HDFC fund name pattern. It ends when a non-fund-name line appears.
    cleaned = []
    in_also_manages = False

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        # Detect start of "Also manages" block
        if ALSO_MANAGES_START.match(stripped):
            in_also_manages = True
            continue  # drop the header line too

        # While in the block, drop HDFC fund name lines
        if in_also_manages:
            if ALSO_MANAGES_LINE.match(stripped):
                continue  # drop this fund name line
            else:
                in_also_manages = False  # block ended

        if is_inline_noise(stripped):
            continue

        cleaned.append(stripped)

    return cleaned


def normalize_whitespace(text: str) -> str:
    """Collapse multiple spaces, normalize unicode spaces."""
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


# ---------------------------------------------------------------------------
# Section detection
# ---------------------------------------------------------------------------

def detect_sections(lines: list[str]) -> list[tuple[str, list[str]]]:
    """
    Walk through cleaned lines and group them into (section_label, [lines]) tuples.
    Returns a list of (label, lines) in document order.

    Sections that should only appear ONCE are tracked — if the same label would
    open again (e.g. fund_basics firing on a stray HDFC fund name), it is
    absorbed into the current section instead.
    """
    # Labels that must only open once — re-matches are absorbed into current section
    ONCE_ONLY = {"fund_basics", "fund_management"}

    sections: list[tuple[str, list[str]]] = []
    current_label = "preamble"
    current_lines: list[str] = []
    seen_labels: set[str] = set()

    for line in lines:
        matched_label = None
        for label, pattern in SECTION_ANCHORS:
            if re.match(pattern, line, re.IGNORECASE):
                matched_label = label
                break

        if matched_label:
            # If this label is once-only and already seen, absorb into current section
            if matched_label in ONCE_ONLY and matched_label in seen_labels:
                current_lines.append(line)
                continue

            # Save current section if it has content
            if current_lines:
                sections.append((current_label, current_lines))

            seen_labels.add(matched_label)
            current_label = matched_label
            current_lines = [line]
        else:
            current_lines.append(line)

    # Flush last section
    if current_lines:
        sections.append((current_label, current_lines))

    return sections


# ---------------------------------------------------------------------------
# FAQ splitting
# ---------------------------------------------------------------------------

def split_faq_into_pairs(faq_lines: list[str]) -> list[tuple[str, list[str]]]:
    """
    Split the FAQ section into individual Q&A chunks.
    Each question line starts a new chunk; the answer lines follow until the next question.
    Returns list of ("faq", [question_line, ...answer_lines]).
    """
    pairs: list[tuple[str, list[str]]] = []
    current: list[str] = []

    for line in faq_lines:
        if FAQ_QUESTION_PATTERN.match(line) and current:
            pairs.append(("faq", current))
            current = [line]
        elif FAQ_QUESTION_PATTERN.match(line):
            current = [line]
        else:
            if current:
                current.append(line)

    if current:
        pairs.append(("faq", current))

    return pairs


# ---------------------------------------------------------------------------
# Chunk builder
# ---------------------------------------------------------------------------

def build_chunks(
    sections: list[tuple[str, list[str]]],
    source_meta: dict,
) -> list[dict]:
    """
    Convert sections into chunk dicts with full metadata.
    - Excluded sections are dropped.
    - FAQ section is split per Q&A pair.
    - Other sections become one chunk each.
    - 3-line overlap from previous non-excluded section is prepended.
    """
    chunks: list[dict] = []
    prev_tail: list[str] = []   # last OVERLAP_LINES lines of previous chunk (for overlap)

    for label, lines in sections:
        # Drop excluded sections entirely
        if label in EXCLUDED_SECTIONS:
            continue

        # Drop chunks that are too short (EC-2.6)
        if len(lines) < MIN_CHUNK_LINES:
            log.debug(f"  Dropping short section '{label}' ({len(lines)} lines)")
            continue

        if label == "faq":
            # Split FAQ into individual Q&A pairs — no overlap between FAQ chunks
            qa_pairs = split_faq_into_pairs(lines[1:])  # skip "FAQs" header line
            for _, qa_lines in qa_pairs:
                if len(qa_lines) < 2:
                    continue
                chunk_text = normalize_whitespace("\n".join(qa_lines))
                chunks.append(_make_chunk(chunk_text, "faq", source_meta))
            # Update prev_tail from last FAQ pair
            if qa_pairs:
                prev_tail = qa_pairs[-1][1][-OVERLAP_LINES:]
        else:
            # Prepend overlap from previous section
            overlap_prefix = prev_tail[-OVERLAP_LINES:] if prev_tail else []
            full_lines = overlap_prefix + lines
            chunk_text = normalize_whitespace("\n".join(full_lines))

            chunks.append(_make_chunk(chunk_text, label, source_meta))
            prev_tail = lines[-OVERLAP_LINES:]

    return chunks


def _make_chunk(text: str, section_label: str, source_meta: dict) -> dict:
    """Construct a single chunk dict with full metadata envelope."""
    return {
        "chunk_id": str(uuid.uuid4()),
        "source_url": source_meta["source_url"],
        "document_type": source_meta["document_type"],
        "amc_name": source_meta["amc_name"],
        "scheme_name": source_meta["scheme_name"],
        "fund_category": source_meta["fund_category"],
        "section_label": section_label,
        "last_updated": source_meta["download_date"][:10],  # YYYY-MM-DD
        "char_count": len(text),
        "chunk_text": text,
    }


# ---------------------------------------------------------------------------
# Per-file processor
# ---------------------------------------------------------------------------

def process_file(slug: str, registry_entry: dict, log_entries: list) -> list[dict]:
    """
    Full Phase 2 pipeline for a single raw file.
    Returns list of chunk dicts.
    """
    raw_path = BASE_DIR / registry_entry["output_file"]

    if not raw_path.exists():
        msg = f"Raw file not found: {raw_path}"
        log.error(f"  [ERROR] {slug}: {msg}")
        log_entries.append({"slug": slug, "status": "file_not_found", "error": msg})
        return []

    log.info(f"  Processing: {slug}")
    raw_text = raw_path.read_text(encoding="utf-8")
    lines = raw_text.splitlines()

    # Step 1+3: Strip boilerplate and inline noise
    cleaned_lines = strip_boilerplate(lines)
    log.info(f"    Lines after cleaning: {len(cleaned_lines)} (from {len(lines)} raw)")

    # Step 4: Section detection
    sections = detect_sections(cleaned_lines)
    section_labels = [s[0] for s in sections]
    log.info(f"    Sections detected: {section_labels}")

    # Step 5+6: Build chunks with metadata
    source_meta = {
        "source_url": registry_entry["source_url"],
        "document_type": registry_entry["document_type"],
        "amc_name": registry_entry["amc_name"],
        "scheme_name": registry_entry["scheme_name"],
        "fund_category": registry_entry["fund_category"],
        "download_date": registry_entry["download_date"],
    }

    chunks = build_chunks(sections, source_meta)
    log.info(f"    Chunks produced: {len(chunks)}")

    # Log section coverage
    chunk_labels = [c["section_label"] for c in chunks]
    log_entries.append({
        "slug": slug,
        "scheme_name": registry_entry["scheme_name"],
        "status": "success",
        "raw_lines": len(lines),
        "cleaned_lines": len(cleaned_lines),
        "sections_detected": section_labels,
        "chunks_produced": len(chunks),
        "chunk_section_labels": chunk_labels,
        "processed_at": datetime.now().isoformat(),
    })

    return chunks


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Phase 2: Process and chunk raw fund pages")
    parser.add_argument("--force", action="store_true",
                        help="Reprocess even if chunks.jsonl already exists")
    args = parser.parse_args()

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    if CHUNKS_PATH.exists() and not args.force:
        log.info(f"chunks.jsonl already exists. Use --force to reprocess.")
        return True

    # Load registry
    if not REGISTRY_PATH.exists():
        log.error("source_registry.json not found. Run Phase 1 first.")
        return False

    with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
        registry = json.load(f)

    scheme_entries = {
        k: v for k, v in registry.items()
        if not k.startswith("_") and isinstance(v, dict) and v.get("status") == "success"
    }

    if not scheme_entries:
        log.error("No successfully collected sources in registry. Run Phase 1 first.")
        return False

    log.info(f"Processing {len(scheme_entries)} scheme(s)...")

    all_chunks: list[dict] = []
    log_entries: list[dict] = []

    for slug, entry in scheme_entries.items():
        chunks = process_file(slug, entry, log_entries)
        all_chunks.extend(chunks)

    # Write chunks.jsonl — one JSON object per line
    with open(CHUNKS_PATH, "w", encoding="utf-8") as f:
        for chunk in all_chunks:
            f.write(json.dumps(chunk, ensure_ascii=False) + "\n")

    # Write processing log
    with open(PROCESSING_LOG_PATH, "w", encoding="utf-8") as f:
        json.dump(log_entries, f, indent=2, ensure_ascii=False)

    # --- Summary ---
    log.info("\n" + "=" * 50)
    log.info("Phase 2 Processing Summary")
    log.info("=" * 50)
    log.info(f"  Schemes processed : {len(scheme_entries)}")
    log.info(f"  Total chunks      : {len(all_chunks)}")
    log.info(f"  Output            : {CHUNKS_PATH}")
    log.info(f"  Processing log    : {PROCESSING_LOG_PATH}")

    if all_chunks:
        avg_chars = sum(c["char_count"] for c in all_chunks) / len(all_chunks)
        log.info(f"  Avg chunk size    : {avg_chars:.0f} chars")

        # Coverage report per scheme
        log.info("\n  Coverage per scheme:")
        from collections import Counter
        scheme_counts = Counter(c["scheme_name"] for c in all_chunks)
        for scheme, count in scheme_counts.items():
            log.info(f"    {scheme}: {count} chunks")

        # Coverage per section label
        log.info("\n  Chunks per section label:")
        section_counts = Counter(c["section_label"] for c in all_chunks)
        for section, count in sorted(section_counts.items()):
            log.info(f"    {section}: {count}")

    failed = [e for e in log_entries if e.get("status") != "success"]
    if failed:
        log.warning(f"\n  WARNING: {len(failed)} scheme(s) failed processing.")
        for f_entry in failed:
            log.warning(f"    {f_entry['slug']}: {f_entry.get('error')}")

    return len(failed) == 0


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
