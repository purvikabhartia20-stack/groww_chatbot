# Edge Cases — Mutual Fund FAQ Assistant

This folder documents all identified edge cases across the 5 build phases. Each file maps directly to a phase in `docs/architecture.md`.

| File | Phase | Edge Cases |
|------|-------|------------|
| [phase1_edge_cases.md](./phase1_edge_cases.md) | Phase 1 — Data Collection & Corpus Building | 9 cases |
| [phase2_edge_cases.md](./phase2_edge_cases.md) | Phase 2 — Document Processing & Chunking | 10 cases |
| [phase3_edge_cases.md](./phase3_edge_cases.md) | Phase 3 — Embedding & Vector Store Indexing | 10 cases |
| [phase4_edge_cases.md](./phase4_edge_cases.md) | Phase 4 — RAG Query Engine & LLM Response Layer | 14 cases |
| [phase5_edge_cases.md](./phase5_edge_cases.md) | Phase 5 — Frontend Interface & Compliance Guardrails | 14 cases |

**Total: 57 edge cases documented.**

---

## Edge Case ID Convention

Each case is prefixed `EC-<phase>.<number>` for traceability:
- `EC-1.x` → Phase 1 (Data Collection)
- `EC-2.x` → Phase 2 (Processing & Chunking)
- `EC-3.x` → Phase 3 (Embedding & Indexing)
- `EC-4.x` → Phase 4 (RAG Pipeline & LLM)
- `EC-5.x` → Phase 5 (Frontend & Guardrails)

---

## High-Priority Cases (Address Before First Demo)

| ID | Description | Why Critical |
|----|-------------|--------------|
| EC-1.2 | Groww pages render via JavaScript | All 5 source URLs may return empty HTML without a headless browser |
| EC-3.7 | Embedding dimension mismatch | Silent failure — retrieval returns garbage scores |
| EC-4.3 | Retrieved chunks from wrong scheme | Confidently wrong answer with a valid-looking source citation |
| EC-4.5 | LLM hallucinates despite temperature=0 | Core compliance risk — advisory content reaches user |
| EC-4.10 | Prompt injection via long query | Security risk — system prompt override attempt |
| EC-5.1 | PII regex false positives | Blocks legitimate queries — breaks basic usability |
| EC-5.14 | Example questions trigger refusal | First user interaction fails — immediate trust loss |
