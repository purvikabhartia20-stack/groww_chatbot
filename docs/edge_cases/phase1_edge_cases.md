# Phase 1 — Edge Cases: Data Collection & Corpus Building

## EC-1.1 — URL Returns 403 / 404 / 503
**Scenario:** One of the 5 Groww URLs is temporarily unavailable or returns an HTTP error.  
**Risk:** Silent data gap — a scheme is missing from the corpus entirely.  
**Handling:**
- Retry with exponential backoff (3 attempts, 5s / 15s / 30s delays)
- Log failed URL with timestamp and HTTP status to `source_registry.json`
- Mark scheme as `status: "fetch_failed"` — do NOT proceed to Phase 2 for that scheme
- Alert: surface a warning in the processing log so the operator knows coverage is incomplete

---

## EC-1.2 — Groww Page Renders via JavaScript (Dynamic Content)
**Scenario:** Groww fund pages load data via JS/React — a plain HTTP GET returns an empty shell with no fund data.  
**Risk:** Raw file saved is just HTML boilerplate with no actual scheme information.  
**Handling:**
- Use a headless browser (Playwright or Selenium) to render the page before scraping
- Validate that extracted text contains expected keywords (`expense ratio`, `exit load`, `NAV`) before saving
- If validation fails → log as `status: "empty_render"` and flag for manual review

---

## EC-1.3 — Page Structure Changes (Groww UI Update)
**Scenario:** Groww updates its frontend layout, breaking CSS selectors or HTML structure used for scraping.  
**Risk:** Scraper silently extracts wrong sections or nothing at all.  
**Handling:**
- After extraction, run a schema validation check: assert presence of at least 5 expected field names
- If validation fails → log as `status: "schema_mismatch"`, halt ingestion for that URL
- Do not ingest partially scraped data into the corpus

---

## EC-1.4 — Duplicate URL Ingestion
**Scenario:** The same URL is accidentally run through the collector twice (e.g., re-run without clearing `/data/raw/`).  
**Risk:** Duplicate chunks in the vector store, inflating retrieval noise.  
**Handling:**
- Check `source_registry.json` before downloading — if URL already exists with `status: "success"`, skip
- Deduplication key: `source_url` + `download_date`

---

## EC-1.5 — Stale / Outdated Page Content
**Scenario:** The Groww page was last updated months ago and shows outdated expense ratios or NAV figures.  
**Risk:** Assistant returns factually incorrect but confidently cited data.  
**Handling:**
- Record `download_date` in `source_registry.json` for every fetch
- Surface `last_updated` in every response so users can judge freshness
- Document that corpus must be re-ingested periodically (recommended: monthly, aligned with factsheet cycles)

---

## EC-1.6 — Partial Page Load (Network Timeout Mid-Fetch)
**Scenario:** Page starts loading but connection drops, resulting in a truncated HTML file.  
**Risk:** Incomplete data saved to `/data/raw/` — missing sections like exit load or benchmark.  
**Handling:**
- Validate file size against a minimum threshold (e.g., > 50KB for a fund page)
- Check that HTML has a closing `</html>` tag
- If either check fails → discard file, log as `status: "truncated"`, retry

---

## EC-1.7 — Rate Limiting / IP Block by Groww
**Scenario:** Rapid sequential requests to Groww trigger rate limiting or a temporary IP block.  
**Risk:** All 5 URLs fail after the first 1–2 succeed, leaving an incomplete corpus.  
**Handling:**
- Add a configurable delay between requests (default: 3–5 seconds)
- Randomize user-agent headers
- If HTTP 429 received → back off for 60 seconds before retrying
- Log all rate-limit events

---

## EC-1.8 — Fund Page Contains Disclaimer-Only Content
**Scenario:** A fund page shows only a legal disclaimer or "data not available" message (e.g., new fund with no history).  
**Risk:** Disclaimer text gets chunked and indexed, causing the assistant to cite disclaimers as factual answers.  
**Handling:**
- Detect disclaimer-only pages by checking for absence of structured data fields
- Flag as `status: "disclaimer_only"` — exclude from corpus
- Do not ingest into Phase 2

---

## EC-1.9 — Source Registry Corruption
**Scenario:** `source_registry.json` is corrupted or deleted mid-run.  
**Risk:** Re-ingestion of already-processed files, or loss of provenance metadata.  
**Handling:**
- Write registry entries atomically (write to temp file, then rename)
- Keep a backup copy: `source_registry.backup.json` updated after each successful fetch
- On startup, validate JSON schema of registry before proceeding
