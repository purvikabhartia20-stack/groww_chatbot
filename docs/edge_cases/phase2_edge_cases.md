# Phase 2 — Edge Cases: Document Processing & Chunking Pipeline

## EC-2.1 — Fund Data Presented Entirely as an Image / Scanned Table
**Scenario:** Key data (expense ratio table, exit load table) is embedded as an image inside the HTML or a linked PDF, not as selectable text.  
**Risk:** Text extraction returns nothing for the most important fields.  
**Handling:**
- Detect image-only sections using absence of text in bounding regions
- Apply OCR fallback via `pytesseract` on extracted images
- Flag chunks sourced from OCR with `"ocr_sourced": true` in metadata — lower confidence score
- If OCR confidence < 80% → exclude chunk, log as `status: "ocr_low_confidence"`

---

## EC-2.2 — Table Extraction Produces Garbled Key-Value Pairs
**Scenario:** Multi-column tables (e.g., expense ratio by plan type) are extracted as a flat string with merged cells, losing the row-column relationship.  
**Risk:** Chunk reads "Direct Plan Regular Plan 0.5% 1.2%" with no structure — retrieval returns ambiguous data.  
**Handling:**
- Use `pdfplumber` table extraction or `pandas` HTML table parsing to preserve row/column structure
- Serialize tables as explicit key-value text: `"Direct Plan Expense Ratio: 0.5%"`
- Validate that numeric values appear adjacent to their label in the extracted text

---

## EC-2.3 — Section Detection Fails (No Recognizable Headers)
**Scenario:** A fund page uses non-standard section labels (e.g., "Charges" instead of "Exit Load", "Costs" instead of "Expense Ratio").  
**Risk:** Chunks are tagged with `section_label: "unknown"` — metadata filtering in Phase 4 becomes ineffective.  
**Handling:**
- Maintain a synonym map: `{"charges": "exit_load", "costs": "expense_ratio", "lock-in": "lock_in_period"}`
- Apply fuzzy matching on section headers (Levenshtein distance ≤ 2)
- If no section match found → tag as `"section_label": "general"` rather than leaving blank
- Log all `"general"` tagged chunks for manual review

---

## EC-2.4 — Chunk Splits Mid-Sentence or Mid-Table-Row
**Scenario:** Token-based chunking cuts a sentence like "The exit load is 1% if redeemed with—" at the boundary.  
**Risk:** Incomplete information in a chunk — retrieval returns a truncated, misleading answer.  
**Handling:**
- Always split at sentence boundaries (use `nltk.sent_tokenize` or `spacy` sentence segmentation)
- Never split inside a table row — treat each table row as an atomic unit
- If a single table row exceeds 500 tokens → keep as one oversized chunk, log a warning

---

## EC-2.5 — Overlapping Chunks Contain Contradictory Data
**Scenario:** 50-token overlap causes two adjacent chunks to each contain a partial version of a value (e.g., one chunk says "exit load: 1%" and the next says "exit load: Nil after 1 year").  
**Risk:** Both chunks retrieved — LLM sees conflicting data and may hallucinate a synthesis.  
**Handling:**
- Overlap should never split a key-value pair — overlap boundary must fall between complete statements
- In the prompt, instruct the LLM: "If retrieved chunks contain conflicting values, cite the most specific one and note the discrepancy"
- Flag chunks with overlapping numeric values for review during index verification

---

## EC-2.6 — Empty Chunk After Cleaning
**Scenario:** After noise removal, a chunk contains only whitespace, punctuation, or boilerplate (e.g., "Page 1 of 12 | HDFC Mutual Fund").  
**Risk:** Empty or near-empty vectors pollute the index and may surface as false positives.  
**Handling:**
- Enforce minimum chunk length: discard any chunk with fewer than 30 tokens after cleaning
- Log discarded chunks with reason `"too_short"` in `processing_log.json`

---

## EC-2.7 — Same Data Field Appears Multiple Times in One Document
**Scenario:** Expense ratio is mentioned in the summary section, the fee table, and the footer disclaimer — three separate chunks all tagged `section_label: "expense_ratio"`.  
**Risk:** Retrieval returns all three — context window fills with redundant data, crowding out other relevant chunks.  
**Handling:**
- During chunking, deduplicate chunks with identical `section_label` + near-identical text (cosine similarity > 0.95 between chunk texts)
- Keep the chunk from the most authoritative section (fee table > summary > footer)

---

## EC-2.8 — Non-English Content in Page
**Scenario:** Groww pages may contain Hindi or regional language text in certain sections (e.g., fund name translations, disclaimers).  
**Risk:** Non-English chunks degrade embedding quality and retrieval accuracy.  
**Handling:**
- Detect language per chunk using `langdetect`
- If language != `"en"` → exclude chunk from corpus, log as `"non_english_excluded"`
- Do not attempt to translate — translation introduces inaccuracy risk

---

## EC-2.9 — Metadata Field Missing or Null
**Scenario:** `scheme_name` or `fund_category` cannot be reliably extracted from the page (e.g., page title is generic).  
**Risk:** Chunk has incomplete metadata — Phase 4 metadata filtering returns wrong results.  
**Handling:**
- Derive `scheme_name` from the source URL slug (e.g., `hdfc-mid-cap-fund-direct-growth` → `HDFC Mid Cap Fund Direct Growth`)
- Derive `fund_category` from a hardcoded URL-to-category map maintained in config
- Never leave `scheme_name` or `fund_category` as null — use derived values with a `"derived": true` flag

---

## EC-2.10 — Processing Pipeline Crashes Mid-Run
**Scenario:** The chunking script crashes after processing 3 of 5 schemes.  
**Risk:** `chunks.jsonl` is partially written — Phase 3 indexes an incomplete corpus without knowing it.  
**Handling:**
- Write chunks per-scheme to separate temp files first, then merge into `chunks.jsonl` only after all schemes complete
- Track progress in `processing_log.json` with per-scheme status: `"pending" | "processing" | "done" | "failed"`
- On restart, skip schemes already marked `"done"`
