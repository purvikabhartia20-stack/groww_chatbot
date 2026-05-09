"""
Phase 4 — Step 2+3: Query Embedding & Vector Retrieval
========================================================
Embeds the user query using BAAI/bge-small-en-v1.5 (same model as indexing),
applies optional metadata filters, retrieves top-K chunks from ChromaDB,
and enforces the similarity threshold.

BGE asymmetric retrieval: queries get a prefix, indexed chunks do not.
EC-4.4: financial term synonym expansion applied before embedding.
EC-3.7: model mismatch guard on startup.
"""

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Paths & constants
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
VECTOR_STORE_DIR = BASE_DIR / "data" / "vector_store"
VECTOR_STORE_CONFIG_PATH = BASE_DIR / "data" / "vector_store_config.json"

EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"
CHROMA_COLLECTION_NAME = "hdfc_mutual_fund_corpus"

# BGE asymmetric retrieval prefix — applied to queries only, not to indexed chunks
BGE_QUERY_PREFIX = "Represent this sentence for searching relevant passages: "

TOP_K = 5
SIMILARITY_THRESHOLD = 0.72   # chunks below this are discarded (EC-4.14)
                              # tuned: lock-in/benchmark queries score 0.74-0.78 with scheme filter
MIN_CHUNKS_REQUIRED = 1       # fewer than this → trigger fallback

# Financial term synonym map (EC-4.4)
QUERY_SYNONYMS = {
    "management fee": "expense ratio",
    "annual fee": "expense ratio",
    "fund charges": "expense ratio",
    "ter": "expense ratio",
    "redemption charge": "exit load",
    "redemption fee": "exit load",
    "exit charge": "exit load",
    "tax saving fund": "ELSS",
    "tax saver": "ELSS",
    "equity linked savings": "ELSS",
    "elss fund": "ELSS tax saver fund",
    "lock in": "lock-in period",
    "lock-in": "lock-in period",
    "minimum amount": "minimum investment",
    "min sip": "minimum SIP",
    "minimum sip": "minimum SIP amount",
    "aum": "assets under management",
    "nav": "net asset value",
    "riskometer": "risk rating",
    "benchmark": "benchmark index",
}

# Scheme display name (from classifier) → ChromaDB metadata filter value
# Must match exactly what's stored in ChromaDB (verified via _check_metadata.py)
SCHEME_FILTER_MAP = {
    "HDFC Mid Cap Fund Direct Growth":              "HDFC Mid Cap Fund",
    "HDFC Equity Fund Direct Growth":               "HDFC Equity Fund",
    "HDFC Focused Fund Direct Growth":              "HDFC Focused Fund",
    "HDFC ELSS Tax Saver Fund Direct Plan Growth":  "HDFC ELSS Tax Saver Fund",
    "HDFC Large Cap Fund Direct Growth":            "HDFC Large Cap Fund",
}


# ---------------------------------------------------------------------------
# Retrieval result
# ---------------------------------------------------------------------------
@dataclass
class RetrievedChunk:
    chunk_id: str
    chunk_text: str
    source_url: str
    scheme_name: str
    fund_category: str
    section_label: str
    last_updated: str
    similarity: float
    document_type: str


@dataclass
class RetrievalResult:
    chunks: list[RetrievedChunk] = field(default_factory=list)
    below_threshold: bool = False   # True if not enough chunks passed threshold
    fallback_triggered: bool = False


# ---------------------------------------------------------------------------
# Singleton model + client (loaded once, reused across requests)
# ---------------------------------------------------------------------------
_model: SentenceTransformer | None = None
_collection = None


def _get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _check_model_mismatch()
        log.info(f"Loading embedding model: {EMBEDDING_MODEL}")
        _model = SentenceTransformer(EMBEDDING_MODEL)
        log.info("Embedding model loaded.")
    return _model


def _get_collection():
    global _collection
    if _collection is None:
        client = chromadb.PersistentClient(path=str(VECTOR_STORE_DIR))
        _collection = client.get_collection(CHROMA_COLLECTION_NAME)
        log.info(f"ChromaDB collection loaded: {CHROMA_COLLECTION_NAME} "
                 f"({_collection.count()} vectors)")
    return _collection


def _check_model_mismatch():
    """EC-3.7: refuse to serve if index was built with a different model."""
    if not VECTOR_STORE_CONFIG_PATH.exists():
        return
    with open(VECTOR_STORE_CONFIG_PATH, "r") as f:
        config = json.load(f)
    stored = config.get("embedding_model", "")
    if stored and stored != EMBEDDING_MODEL:
        raise RuntimeError(
            f"Embedding model mismatch: index built with '{stored}', "
            f"but retriever is configured for '{EMBEDDING_MODEL}'. "
            "Re-index with scripts/embed_and_index.py --force."
        )


# ---------------------------------------------------------------------------
# Synonym expansion (EC-4.4)
# ---------------------------------------------------------------------------
def _expand_synonyms(query: str) -> str:
    """Replace known financial term synonyms before embedding."""
    q = query.lower()
    for synonym, canonical in QUERY_SYNONYMS.items():
        if synonym in q:
            q = q.replace(synonym, canonical)
    return q


# ---------------------------------------------------------------------------
# Public retrieval API
# ---------------------------------------------------------------------------
def retrieve(
    query: str,
    detected_scheme: str | None = None,
    top_k: int = TOP_K,
    threshold: float = SIMILARITY_THRESHOLD,
) -> RetrievalResult:
    """
    Embed the query and retrieve top-K chunks from ChromaDB.

    Args:
        query:            Raw user query text.
        detected_scheme:  Scheme display name if detected by classifier (for metadata filter).
        top_k:            Number of chunks to retrieve before threshold filtering.
        threshold:        Minimum cosine similarity to accept a chunk.

    Returns:
        RetrievalResult with chunks, below_threshold flag, and fallback_triggered flag.
    """
    # Step 1: synonym expansion
    expanded_query = _expand_synonyms(query)

    # Step 2: apply BGE query prefix (asymmetric retrieval)
    prefixed_query = BGE_QUERY_PREFIX + expanded_query

    # Step 3: embed
    model = _get_model()
    query_vector = model.encode(
        [prefixed_query],
        normalize_embeddings=True,
        show_progress_bar=False,
    ).tolist()

    # Step 4: build metadata filter if scheme detected (EC-4.3)
    where_filter = None
    if detected_scheme and detected_scheme in SCHEME_FILTER_MAP:
        filter_value = SCHEME_FILTER_MAP[detected_scheme]
        where_filter = {"scheme_name": {"$eq": filter_value}}
        log.debug(f"Applying metadata filter: scheme_name = '{filter_value}'")

    # Step 5: query ChromaDB
    collection = _get_collection()
    try:
        results = collection.query(
            query_embeddings=query_vector,
            n_results=top_k,
            where=where_filter,
            include=["documents", "metadatas", "distances"],
        )
    except Exception as e:
        log.error(f"ChromaDB query failed: {e}")
        return RetrievalResult(fallback_triggered=True)

    # Step 6: unpack and apply similarity threshold
    ids = results.get("ids", [[]])[0]
    docs = results.get("documents", [[]])[0]
    metas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    chunks: list[RetrievedChunk] = []
    for chunk_id, doc, meta, dist in zip(ids, docs, metas, distances):
        # ChromaDB cosine distance → similarity
        similarity = 1.0 - dist

        if similarity < threshold:
            log.debug(f"Chunk {chunk_id} below threshold ({similarity:.3f} < {threshold})")
            continue

        chunks.append(RetrievedChunk(
            chunk_id=chunk_id,
            chunk_text=doc,
            source_url=meta.get("source_url", ""),
            scheme_name=meta.get("scheme_name", ""),
            fund_category=meta.get("fund_category", ""),
            section_label=meta.get("section_label", ""),
            last_updated=meta.get("last_updated", ""),
            similarity=round(similarity, 4),
            document_type=meta.get("document_type", ""),
        ))

    # Sort by similarity descending
    chunks.sort(key=lambda c: c.similarity, reverse=True)

    below_threshold = len(chunks) < MIN_CHUNKS_REQUIRED
    fallback = below_threshold

    log.info(
        f"Retrieved {len(chunks)} chunks above threshold "
        f"(scheme filter: {detected_scheme or 'none'}, "
        f"fallback: {fallback})"
    )

    return RetrievalResult(
        chunks=chunks,
        below_threshold=below_threshold,
        fallback_triggered=fallback,
    )
