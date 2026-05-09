"""
Phase 4 — RAG Pipeline Orchestrator
=====================================
Ties together all Phase 4 steps into a single callable:

  classify → retrieve → build_prompt → generate → format

This is the single entry point called by the Phase 5 FastAPI backend.

Usage:
    from src.rag_pipeline import run_pipeline
    result = run_pipeline("What is the exit load for HDFC ELSS Tax Saver Fund?")
"""

import logging
from dataclasses import dataclass

from dotenv import load_dotenv

from src.classifier import classify
from src.retriever import retrieve
from src.prompt_builder import build_prompt
from src.generator import generate
from src.formatter import format_response, format_refusal

load_dotenv(override=True)
log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Pipeline result
# ---------------------------------------------------------------------------
@dataclass
class PipelineResult:
    answer: str
    source_url: str | None
    last_updated: str | None
    refused: bool
    fallback: bool
    detected_scheme: str | None
    out_of_corpus: bool


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------
def run_pipeline(query: str) -> PipelineResult:
    """
    Run the full RAG pipeline for a user query.

    Steps:
      1. Classify — allow or refuse
      2. Retrieve — embed + vector search
      3. Build prompt — assemble context
      4. Generate — Groq LLM call
      5. Format — enforce compliance rules

    Returns a PipelineResult ready for the API response.
    """
    log.info(f"Pipeline start | query: '{query[:80]}'")

    # ── Step 1: Classify ──────────────────────────────────────────────────
    classification = classify(query)
    log.info(
        f"Classifier: allowed={classification.allowed}, "
        f"reason={classification.reason}, "
        f"scheme={classification.detected_scheme}, "
        f"out_of_corpus={classification.out_of_corpus}"
    )

    if not classification.allowed:
        log.info("Query refused by classifier.")
        result = format_refusal()
        return PipelineResult(
            answer=result["answer"],
            source_url=result["source_url"],
            last_updated=result["last_updated"],
            refused=True,
            fallback=False,
            detected_scheme=None,
            out_of_corpus=False,
        )

    # ── Out-of-corpus: soft fallback, no retrieval attempt ────────────────
    if classification.out_of_corpus:
        log.info("Out-of-corpus query — returning soft fallback.")
        from src.formatter import _fallback_response
        result = _fallback_response(out_of_corpus=True)
        return PipelineResult(
            answer=result["answer"],
            source_url=None,
            last_updated=None,
            refused=False,
            fallback=True,
            detected_scheme=classification.detected_scheme,
            out_of_corpus=True,
        )

    # ── Step 2: Retrieve ──────────────────────────────────────────────────
    retrieval = retrieve(
        query=query,
        detected_scheme=classification.detected_scheme,
    )

    if retrieval.fallback_triggered:
        log.info("Retrieval fallback triggered — insufficient chunks above threshold.")
        result = format_response(
            raw_text=None,
            source_url="",
            last_updated="",
            is_fallback=True,
        )
        return PipelineResult(
            answer=result["answer"],
            source_url=None,
            last_updated=None,
            refused=False,
            fallback=True,
            detected_scheme=classification.detected_scheme,
            out_of_corpus=False,
        )

    # ── Step 3: Build prompt ──────────────────────────────────────────────
    prompt_data = build_prompt(query=query, chunks=retrieval.chunks)

    # ── Step 4: Generate ──────────────────────────────────────────────────
    raw_text = generate(
        system_prompt=prompt_data["system_prompt"],
        user_prompt=prompt_data["user_prompt"],
    )

    # ── Step 5: Format ────────────────────────────────────────────────────
    result = format_response(
        raw_text=raw_text,
        source_url=prompt_data["top_source_url"] if raw_text else "",
        last_updated=prompt_data["last_updated"] if raw_text else "",
        is_fallback=(raw_text is None),
    )

    log.info(
        f"Pipeline complete | fallback={result['fallback']}, "
        f"refused={result['refused']}, "
        f"source={result['source_url']}"
    )

    return PipelineResult(
        answer=result["answer"],
        source_url=result["source_url"],
        last_updated=result["last_updated"],
        refused=result["refused"],
        fallback=result["fallback"],
        detected_scheme=classification.detected_scheme,
        out_of_corpus=False,
    )
