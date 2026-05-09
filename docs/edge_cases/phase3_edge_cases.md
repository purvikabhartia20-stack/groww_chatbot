# Phase 3 — Edge Cases: Embedding & Vector Store Indexing

## EC-3.1 — OpenAI Embedding API Rate Limit Hit During Batch Indexing
**Scenario:** Embedding 1000+ chunks in batches of 100 triggers OpenAI's rate limit (TPM or RPM).  
**Risk:** Indexing job crashes mid-way — partial index with no clear record of which chunks were embedded.  
**Handling:**
- Implement retry with exponential backoff on HTTP 429 responses
- Track indexed chunk IDs in a checkpoint file: `indexing_checkpoint.json`
- On restart, skip chunks already present in the checkpoint
- Log total tokens consumed per run for cost monitoring

---

## EC-3.2 — Embedding Model Returns Zero Vector
**Scenario:** An empty or near-empty chunk (slipped through Phase 2 validation) produces a zero or near-zero embedding vector.  
**Risk:** Zero vectors match everything equally — the chunk surfaces in every retrieval query as a false positive.  
**Handling:**
- After embedding, check L2 norm of each vector — discard if norm < 0.01
- Log discarded vectors with chunk ID and reason `"zero_vector"`
- Re-examine the source chunk to understand why it was empty

---

## EC-3.3 — Duplicate Chunks Indexed (Re-run Without Clearing Store)
**Scenario:** `embed_and_index.py` is run again without clearing the ChromaDB collection — all chunks are inserted a second time.  
**Risk:** Every query retrieves duplicate chunks, doubling context noise and wasting the context window budget.  
**Handling:**
- Use `chunk_id` (UUID from Phase 2) as the vector store document ID — upsert semantics prevent true duplicates
- Before indexing, check if collection already contains the chunk ID and skip if present
- Provide a `--force-reindex` flag that clears the collection before re-running

---

## EC-3.4 — Vector Store Collection Grows Stale After Corpus Update
**Scenario:** One of the 5 Groww URLs is re-scraped with updated data (e.g., new expense ratio after SEBI revision), but old chunks remain in the index alongside new ones.  
**Risk:** Retrieval returns both old and new values — LLM sees conflicting data.  
**Handling:**
- On re-ingestion of a scheme, delete all existing vectors with matching `scheme_name` metadata before upserting new ones
- Never append new chunks for a scheme without first purging the old ones
- Log purge events: `"purged": 47 chunks for HDFC Mid Cap Fund"`

---

## EC-3.5 — Metadata Filter Returns Zero Results
**Scenario:** A query filters by `scheme_name: "HDFC Mid Cap Fund"` but the stored metadata uses a slightly different string (e.g., `"HDFC Mid-Cap Fund"` with a hyphen).  
**Risk:** Metadata filter eliminates all valid chunks — retrieval returns nothing, triggering a false fallback.  
**Handling:**
- Normalize all scheme name strings at index time: lowercase, strip hyphens, strip "direct growth" suffix
- Apply the same normalization to query-time filter values
- Maintain a canonical name map: `{"hdfc-mid-cap-fund-direct-growth": "HDFC Mid Cap Fund"}`

---

## EC-3.6 — ChromaDB Persistence Failure (Local Storage Corruption)
**Scenario:** ChromaDB's local SQLite store becomes corrupted due to an unclean shutdown.  
**Risk:** Index is unreadable — all retrieval fails at runtime.  
**Handling:**
- Keep a backup of the ChromaDB directory after each successful full index run
- On startup, run a health check: attempt a test query and verify it returns results
- If health check fails → alert operator, do not serve queries until index is restored

---

## EC-3.7 — Embedding Dimension Mismatch
**Scenario:** The index was built with `all-MiniLM-L6-v2` (384-dim) but the query is embedded with `text-embedding-3-small` (1536-dim) after a model switch.  
**Risk:** Cosine similarity computation fails or returns garbage scores.  
**Handling:**
- Store the embedding model name in a config file: `vector_store_config.json`
- On startup, assert that the configured embedding model matches the model used to build the current index
- If mismatch detected → refuse to serve queries, require full re-index with the correct model

---

## EC-3.8 — Index Contains Chunks from Rejected Sources
**Scenario:** A bug in Phase 1 or 2 allows a non-approved URL's content to reach the indexing step.  
**Risk:** Assistant cites unofficial or aggregator content as a source.  
**Handling:**
- At index time, validate `source_url` of every chunk against the approved URL allowlist (the 5 Groww URLs)
- Reject any chunk whose `source_url` is not in the allowlist — log as `"rejected_source"`
- This is a hard gate, not a warning

---

## EC-3.9 — Very Large Single Chunk Exceeds Embedding Model Token Limit
**Scenario:** A chunk that slipped through Phase 2 size validation is 800+ tokens — exceeding the embedding model's context window.  
**Risk:** Embedding API returns an error or silently truncates the input, producing a misleading vector.  
**Handling:**
- Before embedding, check token count of each chunk using `tiktoken`
- If chunk exceeds model limit (e.g., 512 tokens for MiniLM, 8191 for OpenAI) → split into two sub-chunks and embed separately
- Log all oversized chunks that required splitting

---

## EC-3.10 — Index Verification Spot-Check Fails
**Scenario:** After indexing, the verification step queries "What is the exit load for HDFC ELSS?" and retrieves chunks from the wrong scheme.  
**Risk:** Metadata filtering or embedding quality is insufficient — retrieval is unreliable before the system goes live.  
**Handling:**
- Maintain a golden test set of 10 query → expected scheme/section pairs
- Run all 10 after every index build — require ≥ 9/10 to pass before marking index as production-ready
- If verification fails → do not proceed to Phase 4 testing, investigate chunking or embedding quality
