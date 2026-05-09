# Mutual Fund FAQ Assistant — Phase-Wise Architecture

> **Project:** Groww-style Mutual Fund FAQ Assistant  
> **Architecture Pattern:** Retrieval-Augmented Generation (RAG)  
> **Philosophy:** Accuracy, transparency, and compliance over conversational intelligence

---

## Overview

The system is built in 5 phases, each independently deliverable and testable. The phases progress from data acquisition through to a production-ready, compliance-safe chat interface.

```
Phase 1 → Data Collection & Corpus Building
Phase 2 → Document Processing & Chunking Pipeline
Phase 3 → Embedding & Vector Store Indexing
Phase 4 → RAG Query Engine & LLM Response Layer
Phase 5 → Frontend Interface & Compliance Guardrails
```

---

## Phase 1 — Data Collection & Corpus Building

### Goal
Assemble a clean, verified corpus of official mutual fund documents from approved sources only.

### Approved Sources
| Source Type         | Examples                                              |
|---------------------|-------------------------------------------------------|
| AMC Website         | Mirae Asset, HDFC AMC, SBI MF, Axis MF (pick one)    |
| AMFI                | amfiindia.com — educational pages, NAV data, FAQs     |
| SEBI                | sebi.gov.in — investor education, circulars           |

### Document Types to Collect
| Document            | Purpose                                               |
|---------------------|-------------------------------------------------------|
| Scheme Information Document (SID) | Full scheme details, exit load, expense ratio, benchmark |
| Key Information Memorandum (KIM)  | Condensed scheme facts, minimum investment, riskometer   |
| Scheme Factsheet (monthly)        | Current NAV, AUM, portfolio composition                  |
| Operational FAQ pages             | Statement download, KYC, SIP setup instructions          |
| Capital Gains / Tax Help pages    | Tax document retrieval process                           |
| AMFI Investor Education pages     | Definitions, fund categories, SIP explanations           |
| SEBI Investor Education pages     | Regulatory definitions, riskometer methodology           |

### Scope
- AMC: **HDFC Mutual Fund**
- All data for this project is sourced exclusively from the following 5 URLs:

| Scheme | URL |
|--------|-----|
| HDFC Mid Cap Fund — Direct Growth | https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth |
| HDFC Equity Fund — Direct Growth | https://groww.in/mutual-funds/hdfc-equity-fund-direct-growth |
| HDFC Focused Fund — Direct Growth | https://groww.in/mutual-funds/hdfc-focused-fund-direct-growth |
| HDFC ELSS Tax Saver Fund — Direct Plan Growth | https://groww.in/mutual-funds/hdfc-elss-tax-saver-fund-direct-plan-growth |
| HDFC Large Cap Fund — Direct Growth | https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth |

> **Note:** These are the only data sources used across all phases of this project. No other URLs, documents, or external sources are to be added or substituted.

### Rejected Sources (Hard Block)
- Financial blogs, news sites (ET, Moneycontrol, Mint)
- Reddit, Quora, YouTube, social media
- Aggregator platforms (Groww, Zerodha, Paytm Money content pages)
- Influencer or advisory content

### Deliverables
- `/data/raw/` — downloaded PDFs, HTML pages, text files
- `/data/source_registry.json` — metadata log: source URL, document type, AMC name, scheme name, download date

---

## Phase 2 — Document Processing & Chunking Pipeline

### Goal
Convert raw documents into clean, semantically meaningful text chunks ready for embedding.

### Pipeline Steps

```
Raw Document (PDF / HTML / TXT)
        ↓
[Step 1] Format Normalization
        ↓
[Step 2] Text Extraction
        ↓
[Step 3] Noise Removal & Cleaning
        ↓
[Step 4] Section Detection
        ↓
[Step 5] Semantic Chunking
        ↓
[Step 6] Metadata Tagging
        ↓
Processed Chunk Store
```

### Step Details

**Step 1 — Format Normalization**
- PDFs → extract via `pdfplumber` or `PyMuPDF`
- HTML pages → parse via `BeautifulSoup`, strip nav/footer/ads
- Tables (expense ratio, exit load) → preserve as structured text rows

**Step 2 — Text Extraction**
- Preserve section headers (e.g., "Exit Load", "Minimum Investment Amount")
- Retain table data as key-value pairs where possible
- Flag scanned/image PDFs for manual review (OCR fallback via `pytesseract`)

**Step 3 — Noise Removal**
- Remove boilerplate: page numbers, legal disclaimers repeated on every page, watermarks
- Normalize whitespace, encoding artifacts, special characters

**Step 4 — Section Detection**
- Identify and label known sections:
  - `expense_ratio`, `exit_load`, `benchmark`, `riskometer`, `minimum_investment`
  - `sip_details`, `lock_in_period`, `fund_category`, `tax_info`, `statement_download`
- Use regex + keyword matching for section boundary detection

**Step 5 — Semantic Chunking**
- Chunk size: **300–500 tokens** per chunk
- Strategy: split at section boundaries first, then by paragraph
- Overlap: **50-token overlap** between adjacent chunks to preserve context continuity
- Do NOT split mid-sentence or mid-table-row

**Step 6 — Metadata Tagging**
Each chunk gets a metadata envelope:
```json
{
  "chunk_id": "uuid",
  "source_url": "https://amfiindia.com/...",
  "document_type": "SID | KIM | Factsheet | FAQ | AMFI_Education | SEBI_Education",
  "amc_name": "Mirae Asset",
  "scheme_name": "Mirae Asset Large Cap Fund",
  "fund_category": "Large Cap",
  "section_label": "exit_load",
  "page_number": 12,
  "last_updated": "2025-04-01",
  "chunk_text": "..."
}
```

### Deliverables
- `/data/processed/chunks.jsonl` — all chunks with metadata
- `/data/processed/processing_log.json` — errors, skipped docs, OCR flags
- Chunking stats report: total chunks, avg chunk size, coverage per scheme

---

## Phase 3 — Embedding & Vector Store Indexing

### Goal
Convert text chunks into dense vector embeddings and store them in a searchable vector database.

### Embedding Model
| Option              | Notes                                                  |
|---------------------|--------------------------------------------------------|
| `BAAI/bge-small-en-v1.5` | **Selected** — open-source, local, 384-dim, retrieval-optimized, MTEB score ~51.7 |
| `sentence-transformers/all-MiniLM-L6-v2` | General similarity, 384-dim, MTEB ~49 — good fallback |
| `text-embedding-3-small` (OpenAI) | Higher quality but requires OpenAI API key — not used |

**Selected:** `BAAI/bge-small-en-v1.5` — retrieval-optimized via contrastive learning, outperforms MiniLM on passage retrieval benchmarks. Runs locally via `sentence-transformers`. Requires a query-time prefix: `"Represent this sentence for searching relevant passages: "` on user queries (not on indexed chunks).

### Vector Store
| Option     | Notes                                                        |
|------------|--------------------------------------------------------------|
| **ChromaDB** | Lightweight, local, easy setup — good for prototype         |
| **Pinecone** | Managed, scalable, production-ready                         |
| **Weaviate** | Open-source, supports hybrid search (BM25 + vector)         |
| **FAISS**    | In-memory, fast, no persistence — dev/testing only          |

**Recommended:** ChromaDB for Phase 3 prototype → Pinecone or Weaviate for production.

### Indexing Pipeline

```
chunks.jsonl
     ↓
[Batch Embedding] — embed chunk_text in batches of 100
     ↓
[Vector Store Upsert] — store vector + full metadata
     ↓
[Index Verification] — spot-check retrieval on known queries
```

### Index Structure
- One collection per AMC (e.g., `mirae_asset_corpus`)
- Metadata filters enabled for: `document_type`, `scheme_name`, `fund_category`, `section_label`
- Hybrid search enabled if using Weaviate (BM25 + semantic for financial terms like "ELSS", "NAV")

### Deliverables
- Populated vector store with all chunks indexed
- `/scripts/embed_and_index.py` — repeatable indexing script
- Index health report: total vectors, coverage per scheme, sample retrieval test results

---

## Phase 4 — RAG Query Engine & LLM Response Layer

### Goal
Build the retrieval + generation pipeline that takes a user query, retrieves relevant chunks, and produces a compliant, grounded response.

### Full Pipeline

```
User Query (natural language)
        ↓
[Step 1] Query Classifier — Allowed or Refused?
        ↓ (if allowed)
[Step 2] Query Embedding
        ↓
[Step 3] Vector Retrieval — Top-K chunks
        ↓
[Step 4] Context Assembly
        ↓
[Step 5] LLM Prompt Construction
        ↓
[Step 6] LLM Generation (constrained)
        ↓
[Step 7] Response Formatter
        ↓
Final Response to User
```

---

### Step 1 — Query Classifier

**Purpose:** Block non-factual, advisory, or comparison queries before retrieval.

**Refused Query Patterns:**
- Investment advice: "should I invest", "is it worth", "good time to invest"
- Comparisons: "compare", "better than", "vs", "which is best"
- Predictions: "will it grow", "expected returns", "beat inflation"
- Rankings: "top fund", "best performing", "safest"
- Suitability: "suits my goals", "right for me", "recommend"

**Implementation:**
- Rule-based keyword/phrase blocklist (fast, deterministic)
- Optional: lightweight intent classifier (fine-tuned or few-shot) as secondary layer

**Refusal Response Template:**
```
This assistant provides factual, source-backed mutual fund information only.
Queries involving investment advice, comparisons, or recommendations are outside
its scope. For guidance, visit AMFI Investor Education:
https://www.amfiindia.com/investor-corner/knowledge-center
```

---

### Step 2 — Query Embedding
- Embed the user query using the same model used during indexing
- No query rewriting or expansion (keeps retrieval deterministic)

---

### Step 3 — Vector Retrieval
- Retrieve **Top-5 chunks** by cosine similarity
- Apply metadata pre-filters where detectable from query:
  - Scheme name mentioned → filter by `scheme_name`
  - Category mentioned → filter by `fund_category`
  - Document type inferable → filter by `section_label`
- Minimum similarity threshold: **0.75** — chunks below this are discarded
- If fewer than 2 chunks pass threshold → trigger fallback response

---

### Step 4 — Context Assembly
- Concatenate retrieved chunks in order of relevance score
- Prepend each chunk with its source label:
  ```
  [Source: Mirae Asset Large Cap Fund — SID, Section: Exit Load]
  <chunk text>
  ```
- Total context window budget: **1500 tokens max** (leaves room for prompt + response)

---

### Step 5 — LLM Prompt Construction

**System Prompt:**
```
You are a compliance-safe mutual fund information assistant.
You answer ONLY using the retrieved context provided below.
You do NOT use general knowledge, make assumptions, or infer missing data.
You do NOT provide investment advice, recommendations, comparisons, or opinions.
If the context does not contain enough information to answer, respond with the fallback message.
Keep responses to a maximum of 3 sentences.
End every response with: "Last updated from sources: <date from metadata>"
Cite exactly one source URL.
Do not use persuasive, advisory, or evaluative language.
```

**User Prompt Structure:**
```
Retrieved Context:
-----------------
{assembled_context}

User Question:
--------------
{user_query}

Answer:
```

---

### Step 6 — LLM Generation

**Provider:** Groq API — OpenAI-compatible interface, ultra-low latency inference on open-source models. Free tier available at [console.groq.com](https://console.groq.com).

| Parameter        | Value                                                        |
|------------------|--------------------------------------------------------------|
| Provider         | Groq API (`groq` Python SDK)                                 |
| Model            | `llama-3.1-8b-instant` (fast, free) / `llama-3.3-70b-versatile` (higher quality) |
| Temperature      | `0.0` — fully deterministic                                  |
| Max tokens       | `200`                                                        |
| Top-p            | `1.0`                                                        |
| Context window   | 8,192 tokens (llama3-8b) / 8,192 tokens (llama3-70b)        |

Temperature is set to 0 to eliminate creative generation and enforce strict grounding. Groq's low-latency inference (typically < 1s) keeps the chat UI responsive without streaming.

---

### Step 7 — Response Formatter

Every response is post-processed to enforce:
1. **3-sentence cap** — truncate or regenerate if exceeded
2. **Source citation** — inject `[Source: <url>]` from top retrieved chunk metadata
3. **Date footer** — append `Last updated from sources: <last_updated from metadata>`
4. **Prohibited language scan** — regex check for banned phrases:
   - "you should", "recommended", "best", "safe investment", "good option", "performs well", "suits your goals"
   - If detected → regenerate with stricter prompt or return fallback

**Fallback Response:**
```
Verified information for this query could not be found in the indexed official sources.
Please refer directly to the AMC website or AMFI for accurate details.
Source: https://www.amfiindia.com
Last updated from sources: N/A
```

---

### Deliverables
- `/src/classifier.py` — query classifier with blocklist + optional ML layer
- `/src/retriever.py` — vector retrieval with metadata filtering and threshold logic
- `/src/prompt_builder.py` — context assembly and prompt construction
- `/src/generator.py` — LLM call with constrained parameters
- `/src/formatter.py` — response post-processing, citation injection, prohibited language scan
- `/src/rag_pipeline.py` — orchestrator tying all steps together
- Unit tests for classifier, retriever threshold logic, and formatter guardrails

---

## Phase 5 — Frontend Interface & Compliance Guardrails

### Goal
Build a minimal, compliance-safe chat UI that presents factual responses clearly and never misleads users.

### UI Layout

```
┌─────────────────────────────────────────────────────────┐
│  Mutual Fund FAQ Assistant                              │
│  ⚠️  Facts-only. No investment advice.                  │
├─────────────────────────────────────────────────────────┤
│  Example questions:                                     │
│  • What is the expense ratio of Mirae Asset Large Cap?  │
│  • What is the exit load for HDFC ELSS Tax Saver?       │
│  • How do I download my capital gains statement?        │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  [Chat message area — scrollable]                       │
│                                                         │
│  User: What is the minimum SIP amount?                  │
│                                                         │
│  Assistant: The minimum SIP amount for Mirae Asset      │
│  Large Cap Fund is ₹1,000 per month as per the KIM.     │
│  Refer to the official document for full details.       │
│  Source: https://miraeassetmf.co.in/...                 │
│  Last updated from sources: 2025-03-01                  │
│                                                         │
├─────────────────────────────────────────────────────────┤
│  [Text input]                          [Send button]    │
└─────────────────────────────────────────────────────────┘
```

### Tech Stack Options

| Layer        | Option A (Lightweight)          | Option B (Production)         |
|--------------|---------------------------------|-------------------------------|
| Frontend     | Streamlit                       | React + Tailwind CSS          |
| Backend API  | FastAPI                         | FastAPI + Uvicorn             |
| Embeddings   | sentence-transformers (local)   | sentence-transformers (local) |
| Vector Store | ChromaDB (local)                | Pinecone / Weaviate           |
| LLM          | Groq API (`llama3-8b-8192`)     | Groq API (`llama3-70b-8192`)  |
| Hosting      | Local / Streamlit Cloud         | AWS / GCP / Render            |

**Recommended for prototype:** Streamlit + FastAPI + ChromaDB + Groq (`llama3-8b-8192`)

### Compliance Guardrails in UI

1. **Disclaimer banner** — always visible, non-dismissable:
   `"Facts-only. No investment advice."`

2. **Input sanitization** — strip PII patterns before query reaches backend:
   - PAN regex: `[A-Z]{5}[0-9]{4}[A-Z]`
   - Aadhaar regex: `\d{4}\s\d{4}\s\d{4}`
   - Phone regex: `[6-9]\d{9}`
   - Email regex: standard RFC pattern
   - If PII detected → block query, show message: `"Please do not share personal information."`

3. **No session storage** — chat history held in memory only, cleared on page refresh

4. **No logging of user queries** — backend must not persist query text to any database or file

5. **Refused query UI handling** — refusal responses displayed in a distinct neutral style (no red/warning color that implies error — just informational)

### API Contract (FastAPI)

**POST `/query`**
```json
Request:
{
  "query": "What is the exit load for Mirae Asset Large Cap Fund?"
}

Response:
{
  "answer": "The exit load for Mirae Asset Large Cap Fund is 1% if redeemed within 1 year from the date of allotment, as stated in the SID.",
  "source_url": "https://miraeassetmf.co.in/downloads/sid/...",
  "last_updated": "2025-03-01",
  "refused": false
}
```

**Response when refused:**
```json
{
  "answer": "This assistant provides factual, source-backed mutual fund information only. Queries involving investment advice, comparisons, or recommendations are outside its scope.",
  "source_url": "https://www.amfiindia.com/investor-corner/knowledge-center",
  "last_updated": null,
  "refused": true
}
```

### Deliverables
- `/app/main.py` — FastAPI app with `/query` endpoint
- `/app/ui.py` — Streamlit frontend (or `/frontend/` for React)
- `/app/pii_filter.py` — input sanitization module
- End-to-end integration test: 10 allowed queries + 5 refused queries
- UI screenshot / demo recording

---

## Directory Structure

```
groww_chatbot/
├── data/
│   ├── raw/                        # Downloaded PDFs, HTML, TXT files
│   ├── processed/
│   │   ├── chunks.jsonl            # All processed chunks with metadata
│   │   └── processing_log.json     # Errors, skipped docs
│   └── source_registry.json        # Source URL + metadata log
│
├── scripts/
│   ├── collect_documents.py        # Phase 1: document downloader
│   ├── process_documents.py        # Phase 2: extraction + chunking
│   └── embed_and_index.py          # Phase 3: embedding + vector store
│
├── src/
│   ├── classifier.py               # Phase 4: query classifier
│   ├── retriever.py                # Phase 4: vector retrieval
│   ├── prompt_builder.py           # Phase 4: context + prompt assembly
│   ├── generator.py                # Phase 4: LLM call
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
├── docs/
│   └── architecture.md             # This document
│
├── .env.example                    # API keys template (never commit .env)
├── requirements.txt
└── README.md
```

---

## Phase Summary Table

| Phase | Name                              | Key Output                                      | Dependencies     |
|-------|-----------------------------------|-------------------------------------------------|------------------|
| 1     | Data Collection & Corpus Building | `/data/raw/`, `source_registry.json`            | None             |
| 2     | Document Processing & Chunking    | `chunks.jsonl`, section-labeled metadata        | Phase 1          |
| 3     | Embedding & Vector Store Indexing | Populated vector DB, indexing scripts           | Phase 2          |
| 4     | RAG Query Engine & LLM Layer      | Full pipeline: classify → retrieve → generate   | Phase 3          |
| 5     | Frontend & Compliance Guardrails  | Chat UI, FastAPI, PII filter, integration tests | Phase 4          |

---

## Key Design Decisions

| Decision                        | Choice                          | Reason                                                    |
|---------------------------------|---------------------------------|-----------------------------------------------------------|
| Chunking strategy               | Section-boundary chunking       | Preserves semantic units like expense ratio tables        |
| Embedding model                 | `bge-small-en-v1.5` (local)    | Retrieval-optimized, outperforms MiniLM on passage retrieval, no API dependency |
| LLM provider                    | Groq API                        | Ultra-low latency, free tier, OpenAI-compatible SDK       |
| Model            | `llama-3.1-8b-instant`              | Fast and free; official replacement for deprecated llama3-8b-8192 |
| Retrieval threshold             | 0.75 cosine similarity          | Prevents low-confidence chunks from polluting context     |
| LLM temperature                 | 0.0                             | Eliminates hallucination risk from creative generation    |
| Query classification            | Rule-based blocklist first      | Deterministic, auditable, no ML dependency for compliance |
| No query logging                | Hard requirement                | Privacy compliance — no PII risk from query storage       |
| Source citation enforcement     | Post-processing formatter       | Ensures every response is traceable to official source    |
| Fallback on low retrieval score | Safe fallback message           | Prevents hallucination when context is insufficient       |

---

## Phase 6 — Automated Data Refresh via GitHub Actions

### Goal
Keep the corpus fresh automatically by re-running Phase 1 (scraping) and Phase 2 (chunking) on a schedule, then re-indexing the vector store (Phase 3), so the assistant always answers from up-to-date fund data without manual intervention.

### Why GitHub Actions
- Free for public/private repos (within usage limits)
- No additional infrastructure — runs entirely in the cloud
- Cron scheduling built-in
- Secrets management for API keys (OpenAI, etc.)
- Artifacts and commit-back support for persisting updated data

### Trigger Strategy

| Trigger | Schedule | Purpose |
|---------|----------|---------|
| Scheduled cron | Monthly (1st of every month, 06:00 UTC) | Aligned with Groww factsheet update cycle |
| Manual dispatch | `workflow_dispatch` | Force a refresh at any time from GitHub UI |
| Push to `main` | On changes to `scripts/` | Re-index when scraping or chunking logic changes |

### Workflow Architecture

```
[Trigger: cron / manual / push]
        ↓
[Job 1: refresh-corpus]
  ├── Checkout repo
  ├── Set up Python 3.12
  ├── Install dependencies (pip + playwright chromium)
  ├── Run scripts/collect_documents.py --force
  ├── Run scripts/process_documents.py --force
  ├── Run scripts/embed_and_index.py --force
  ├── Commit updated source_registry.json + chunks.jsonl back to repo
  └── Upload raw/*.txt as workflow artifacts (30-day retention)

[Job 2: notify-on-failure] (runs only if Job 1 fails)
  └── Create GitHub Issue with failure details
```

### Secrets Required

| Secret Name | Value | Used In |
|-------------|-------|---------|
| `GROQ_API_KEY` | Groq API key (free at console.groq.com) | Phase 4 LLM at query time (not in refresh pipeline) |
| `GH_PAT` | GitHub Personal Access Token (repo write scope) | Commit updated registry back to repo |

> **Note:** No `OPENAI_API_KEY` is needed. Embeddings are generated locally via `sentence-transformers` — the refresh pipeline runs entirely without any paid API calls.

### Data Persistence Strategy

Since GitHub Actions runners are ephemeral, data is persisted via two mechanisms:

1. **Commit-back** — `source_registry.json` and `data/processed/chunks.jsonl` are committed back to the repo after each successful run. This gives a full audit trail of every refresh.
2. **Workflow Artifacts** — Raw `.txt` files are uploaded as artifacts (30-day retention) for debugging without bloating the repo.
3. **Vector store** — ChromaDB is rebuilt fresh on every run (not persisted in repo). For production, switch to Pinecone/Weaviate with persistent storage.

### Failure Handling

- If any script exits with a non-zero code, the job fails immediately
- A `notify-on-failure` job automatically opens a GitHub Issue with the error log
- The previous committed `chunks.jsonl` remains intact — the assistant continues serving from the last good corpus until the next successful run

### Workflow File Location

```
.github/
└── workflows/
    └── refresh_corpus.yml
```

### Refresh Cadence Recommendation

| Data Type | Recommended Frequency | Reason |
|-----------|----------------------|--------|
| NAV, AUM, Expense Ratio | Monthly | Groww updates factsheet data monthly |
| Exit Load, Benchmark | Quarterly | Rarely changes; SEBI circulars drive changes |
| Fund Manager | On-demand | Changes are infrequent but impactful |
| FAQ content | Monthly | Groww may update FAQ text periodically |

---

*Document generated for: `c:\Users\HP\groww_chatbot\`*  
*Architecture version: 1.1*  
*Date: May 2026*
