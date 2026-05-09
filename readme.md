# Mutual Fund FAQ Assistant

A compliance-safe, RAG-powered chatbot that answers factual questions about HDFC Mutual Fund schemes. Built on official Groww fund pages as the sole data source.

> **Philosophy:** Accuracy, transparency, and compliance over conversational intelligence.

---

## Disclaimer

This assistant provides **factual, source-backed information only**. It does not provide investment advice, recommendations, comparisons, or predictions. Always consult a SEBI-registered financial advisor before making investment decisions.

---

## Data Sources

All data is sourced exclusively from these 5 Groww fund pages:

| Scheme | URL |
|--------|-----|
| HDFC Mid Cap Fund | https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth |
| HDFC Equity Fund | https://groww.in/mutual-funds/hdfc-equity-fund-direct-growth |
| HDFC Focused Fund | https://groww.in/mutual-funds/hdfc-focused-fund-direct-growth |
| HDFC ELSS Tax Saver Fund | https://groww.in/mutual-funds/hdfc-elss-tax-saver-fund-direct-plan-growth |
| HDFC Large Cap Fund | https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth |

---

## Project Structure

```
groww_chatbot/
├── config.py                       # Central config for all phases
├── requirements.txt
├── .env.example                    # Copy to .env and add your API keys
│
├── scripts/
│   ├── collect_documents.py        # Phase 1: scrape Groww fund pages
│   ├── validate_corpus.py          # Phase 1: validate collected raw files
│   ├── process_documents.py        # Phase 2: extract, chunk, tag
│   └── embed_and_index.py          # Phase 3: embed chunks + build vector store
│
├── src/
│   ├── classifier.py               # Phase 4: query classifier (allow/refuse)
│   ├── retriever.py                # Phase 4: vector retrieval with filters
│   ├── prompt_builder.py           # Phase 4: context assembly + prompt
│   ├── generator.py                # Phase 4: LLM call (constrained)
│   ├── formatter.py                # Phase 4: response post-processing
│   └── rag_pipeline.py             # Phase 4: pipeline orchestrator
│
├── app/
│   ├── main.py                     # Phase 5: FastAPI backend
│   ├── ui.py                       # Phase 5: Streamlit frontend
│   └── pii_filter.py               # Phase 5: PII sanitization
│
├── tests/
│   ├── test_classifier.py
│   ├── test_retriever.py
│   ├── test_formatter.py
│   └── test_integration.py
│
├── data/
│   ├── raw/                        # Scraped fund page text files (gitignored)
│   ├── processed/                  # Chunks + processing logs (gitignored)
│   └── source_registry.json        # Provenance metadata (tracked)
│
└── docs/
    ├── architecture.md             # Phase-wise architecture
    └── edge_cases/                 # Edge case documentation per phase
```

---

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
playwright install chromium
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY
```

### 3. Run Phase 1 — Collect data

```bash
python scripts/collect_documents.py
python scripts/validate_corpus.py
```

### 4. Run Phase 2 — Process & chunk

```bash
python scripts/process_documents.py
```

### 5. Run Phase 3 — Embed & index

```bash
python scripts/embed_and_index.py
```

### 6. Run Phase 5 — Start the assistant

```bash
# Terminal 1: start the API
uvicorn app.main:app --host 0.0.0.0 --port 8000

# Terminal 2: start the UI (Next.js)
cd frontend
npm install
npm run dev
```

---

## Automated Corpus Refresh (GitHub Actions)

The corpus is kept fresh automatically via `.github/workflows/refresh_corpus.yml`.

**Schedule:** Runs on the 1st of every month at 06:00 UTC, on every push to `scripts/` or `config.py`, and can be triggered manually from the Actions tab.

**Required GitHub Secrets** (set in repo Settings → Secrets → Actions):

| Secret | Purpose |
|--------|---------|
| `GROQ_API_KEY` | Phase 4 LLM generation via Groq (used at query time, not in refresh pipeline) |
| `GH_PAT` | Write-back of updated `chunks.jsonl` and `source_registry.json` to repo |

> No `OPENAI_API_KEY` needed — embeddings run locally via `sentence-transformers`.

**What it does on each run:**
1. Scrapes all 5 Groww fund pages (Phase 1)
2. Re-chunks and re-tags (Phase 2)
3. Re-embeds and re-indexes into ChromaDB (Phase 3)
4. Commits updated `source_registry.json`, `chunks.jsonl`, and `processing_log.json` back to `main`
5. Opens a GitHub Issue automatically if the run fails

---

## Architecture

See [`docs/architecture.md`](docs/architecture.md) for the full phase-wise architecture.  
See [`docs/edge_cases/`](docs/edge_cases/) for documented edge cases per phase.
