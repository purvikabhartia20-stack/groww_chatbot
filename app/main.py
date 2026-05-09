"""
Phase 5 — FastAPI Backend
==========================
Exposes the RAG pipeline as a REST API consumed by the Next.js frontend.

Endpoints:
  POST /query   — run the full RAG pipeline for a user query
  GET  /health  — liveness check

Compliance:
  - No query logging (EC-5.4 / architecture requirement)
  - PII blocked before pipeline (EC-5.1)
  - CORS restricted to Next.js dev origin (EC-5.13)
  - Query length capped at 500 chars (EC-4.10 / EC-5.3)
"""

import sys
from pathlib import Path

# Ensure project root is on the path so src/ and app/ imports work
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, field_validator
from dotenv import load_dotenv

from app.pii_filter import scan as pii_scan
from src.rag_pipeline import run_pipeline

load_dotenv(override=True)

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------
app = FastAPI(
    title="HDFC Mutual Fund FAQ Assistant",
    description="Factual, source-backed answers about HDFC Mutual Fund schemes. No investment advice.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url=None,
)

# CORS — allow Next.js dev server and production origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",   # Next.js dev
        "http://127.0.0.1:3000",
    ],
    allow_methods=["POST", "GET"],
    allow_headers=["Content-Type"],
)

# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------
MAX_QUERY_CHARS = 500

class QueryRequest(BaseModel):
    query: str

    @field_validator("query")
    @classmethod
    def validate_query(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Query cannot be empty.")
        if len(v) > MAX_QUERY_CHARS:
            raise ValueError(f"Query exceeds {MAX_QUERY_CHARS} character limit.")
        return v


class QueryResponse(BaseModel):
    answer: str
    source_url: str | None
    last_updated: str | None
    refused: bool
    fallback: bool


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@app.get("/health")
def health():
    return {"status": "ok", "service": "HDFC Mutual Fund FAQ Assistant"}


@app.post("/query", response_model=QueryResponse)
def query(request: QueryRequest):
    """
    Run the RAG pipeline for a user query.

    - Blocks PII before processing
    - Blocks advisory/comparative queries (classifier)
    - Returns factual answer with source URL and date
    - Never logs the query text
    """
    # PII check (EC-5.1) — block before any processing
    pii_result = pii_scan(request.query)
    if pii_result.contains_pii:
        raise HTTPException(
            status_code=400,
            detail=f"Please do not share personal information ({pii_result.pii_type}).",
        )

    # Run pipeline — no query text is logged anywhere
    result = run_pipeline(request.query)

    return QueryResponse(
        answer=result.answer,
        source_url=result.source_url,
        last_updated=result.last_updated,
        refused=result.refused,
        fallback=result.fallback,
    )
