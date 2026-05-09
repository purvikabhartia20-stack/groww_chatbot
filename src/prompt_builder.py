"""
Phase 4 — Step 4+5: Context Assembly & Prompt Construction
============================================================
Assembles retrieved chunks into a context block within the token budget,
then constructs the system + user prompt for the LLM.

EC-4.8: greedy context assembly respects 1500-token budget.
"""

import logging

from src.retriever import RetrievedChunk

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
CONTEXT_WINDOW_BUDGET = 1500   # max chars for assembled context (approx tokens)

SYSTEM_PROMPT = """You are a compliance-safe mutual fund information assistant for HDFC Mutual Fund schemes.

STRICT RULES — follow every rule without exception:
1. Answer ONLY using the retrieved context provided below. Do not use general knowledge.
2. Do NOT make assumptions or infer data that is not explicitly stated in the context.
3. Do NOT provide investment advice, recommendations, comparisons, rankings, or opinions.
4. Do NOT use language like: "you should", "recommended", "best", "safe investment", "good option", "performs well", "suits your goals", "suitable for you".
5. Keep your answer to a MAXIMUM of 3 sentences.
6. End EVERY response with exactly: "Last updated from sources: <date>"
   where <date> comes from the context metadata provided.
7. Cite exactly ONE source URL from the context. Place it on its own line as: Source: <url>
8. If the context does not contain enough information to answer confidently, respond ONLY with the fallback message — do not guess.

FALLBACK MESSAGE (use verbatim when context is insufficient):
"Verified information for this query could not be found in the indexed sources. Please refer directly to the fund page for accurate details."
"""

USER_PROMPT_TEMPLATE = """Retrieved Context:
-----------------
{context}

User Question:
--------------
{query}

Answer (max 3 sentences, cite one source URL, end with last updated date):"""


# ---------------------------------------------------------------------------
# Context assembly
# ---------------------------------------------------------------------------
def assemble_context(chunks: list[RetrievedChunk]) -> tuple[str, str, str]:
    """
    Assemble retrieved chunks into a context string within the token budget.

    Returns:
        (context_text, top_source_url, last_updated_date)
    """
    if not chunks:
        return "", "", "N/A"

    assembled_parts = []
    total_chars = 0
    top_source_url = chunks[0].source_url
    last_updated = chunks[0].last_updated

    for chunk in chunks:
        label = (
            f"[Source: {chunk.scheme_name} | "
            f"Section: {chunk.section_label} | "
            f"Updated: {chunk.last_updated}]"
        )
        part = f"{label}\n{chunk.chunk_text}"

        if total_chars + len(part) > CONTEXT_WINDOW_BUDGET:
            # Budget exhausted — include at least the first chunk regardless
            if not assembled_parts:
                assembled_parts.append(part[:CONTEXT_WINDOW_BUDGET])
                log.warning(f"Single chunk truncated to fit context budget.")
            else:
                log.debug(f"Context budget reached after {len(assembled_parts)} chunks.")
            break

        assembled_parts.append(part)
        total_chars += len(part)

    context_text = "\n\n".join(assembled_parts)
    return context_text, top_source_url, last_updated


# ---------------------------------------------------------------------------
# Prompt construction
# ---------------------------------------------------------------------------
def build_prompt(query: str, chunks: list[RetrievedChunk]) -> dict:
    """
    Build the full prompt payload for the LLM.

    Returns a dict with:
        system_prompt, user_prompt, top_source_url, last_updated
    """
    context_text, top_source_url, last_updated = assemble_context(chunks)

    user_prompt = USER_PROMPT_TEMPLATE.format(
        context=context_text,
        query=query,
    )

    log.debug(
        f"Prompt built — context chars: {len(context_text)}, "
        f"source: {top_source_url}, updated: {last_updated}"
    )

    return {
        "system_prompt": SYSTEM_PROMPT,
        "user_prompt": user_prompt,
        "top_source_url": top_source_url,
        "last_updated": last_updated,
    }
