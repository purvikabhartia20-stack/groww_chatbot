"""
Central configuration for the Mutual Fund FAQ Assistant.
All phases import constants from here — never hardcode values in individual scripts.
"""

from pathlib import Path

# ---------------------------------------------------------------------------
# Project root
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent

# ---------------------------------------------------------------------------
# Phase 1 — Data Collection
# ---------------------------------------------------------------------------
RAW_DIR = BASE_DIR / "data" / "raw"
REGISTRY_PATH = BASE_DIR / "data" / "source_registry.json"
COLLECTION_LOG = BASE_DIR / "data" / "collection.log"

# The 5 approved source URLs — immutable for this project
APPROVED_SOURCES = [
    {
        "scheme_name": "HDFC Mid Cap Fund",
        "fund_category": "Mid Cap",
        "amc_name": "HDFC Mutual Fund",
        "url": "https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth",
        "slug": "hdfc-mid-cap-fund-direct-growth",
    },
    {
        "scheme_name": "HDFC Equity Fund",
        "fund_category": "Flexi Cap",
        "amc_name": "HDFC Mutual Fund",
        "url": "https://groww.in/mutual-funds/hdfc-equity-fund-direct-growth",
        "slug": "hdfc-equity-fund-direct-growth",
    },
    {
        "scheme_name": "HDFC Focused Fund",
        "fund_category": "Focused Fund",
        "amc_name": "HDFC Mutual Fund",
        "url": "https://groww.in/mutual-funds/hdfc-focused-fund-direct-growth",
        "slug": "hdfc-focused-fund-direct-growth",
    },
    {
        "scheme_name": "HDFC ELSS Tax Saver Fund",
        "fund_category": "ELSS",
        "amc_name": "HDFC Mutual Fund",
        "url": "https://groww.in/mutual-funds/hdfc-elss-tax-saver-fund-direct-plan-growth",
        "slug": "hdfc-elss-tax-saver-fund-direct-plan-growth",
    },
    {
        "scheme_name": "HDFC Large Cap Fund",
        "fund_category": "Large Cap",
        "amc_name": "HDFC Mutual Fund",
        "url": "https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth",
        "slug": "hdfc-large-cap-fund-direct-growth",
    },
]

# Canonical scheme name lookup by slug (used in Phase 4 for query-time scheme detection)
SLUG_TO_SCHEME = {s["slug"]: s["scheme_name"] for s in APPROVED_SOURCES}

# Approved URL allowlist (used in Phase 3 as a hard gate on chunk source_url)
APPROVED_URLS = {s["url"] for s in APPROVED_SOURCES}

# ---------------------------------------------------------------------------
# Phase 2 — Document Processing
# ---------------------------------------------------------------------------
PROCESSED_DIR = BASE_DIR / "data" / "processed"
CHUNKS_PATH = PROCESSED_DIR / "chunks.jsonl"
PROCESSING_LOG_PATH = PROCESSED_DIR / "processing_log.json"

CHUNK_SIZE_TOKENS = 400       # target chunk size
CHUNK_OVERLAP_TOKENS = 50     # overlap between adjacent chunks
MIN_CHUNK_TOKENS = 30         # discard chunks shorter than this (EC-2.6)
MAX_CHUNK_TOKENS = 512        # hard cap before embedding model limit (EC-3.9)

# Section label synonym map (EC-2.3)
SECTION_SYNONYMS = {
    "charges": "exit_load",
    "redemption charge": "exit_load",
    "redemption fee": "exit_load",
    "costs": "expense_ratio",
    "management fee": "expense_ratio",
    "total expense ratio": "expense_ratio",
    "ter": "expense_ratio",
    "lock-in": "lock_in_period",
    "lock in period": "lock_in_period",
    "tax saving": "lock_in_period",
    "minimum investment": "minimum_investment",
    "minimum application": "minimum_investment",
    "min sip": "sip_details",
    "systematic investment": "sip_details",
    "risk": "riskometer",
    "risk-o-meter": "riskometer",
    "index": "benchmark",
    "benchmark index": "benchmark",
}

KNOWN_SECTIONS = [
    "expense_ratio",
    "exit_load",
    "benchmark",
    "riskometer",
    "minimum_investment",
    "sip_details",
    "lock_in_period",
    "fund_category",
    "tax_info",
    "statement_download",
    "nav",
    "aum",
    "fund_manager",
    "portfolio",
    "general",
]

# ---------------------------------------------------------------------------
# Phase 3 — Embedding & Vector Store
# ---------------------------------------------------------------------------
VECTOR_STORE_DIR = BASE_DIR / "data" / "vector_store"
VECTOR_STORE_CONFIG_PATH = BASE_DIR / "data" / "vector_store_config.json"
CHROMA_COLLECTION_NAME = "hdfc_mutual_fund_corpus"

# Embeddings use sentence-transformers (open-source, no API key needed)
# Groq does not provide an embeddings API — local model is used for Phase 3
# BGE-small is retrieval-optimized (MTEB ~51.7) vs MiniLM (MTEB ~49)
EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"
EMBEDDING_BATCH_SIZE = 100
EMBEDDING_DIMENSIONS = 384      # bge-small-en-v1.5 output dims

# BGE models require a prefix on QUERY embeddings only (not on indexed chunks)
# This is the asymmetric retrieval pattern BGE is trained for
BGE_QUERY_PREFIX = "Represent this sentence for searching relevant passages: "

INDEXING_CHECKPOINT_PATH = BASE_DIR / "data" / "indexing_checkpoint.json"

# Minimum L2 norm to accept an embedding vector (EC-3.2)
MIN_VECTOR_NORM = 0.01

# ---------------------------------------------------------------------------
# Phase 4 — RAG Pipeline
# ---------------------------------------------------------------------------
TOP_K_CHUNKS = 5
SIMILARITY_THRESHOLD = 0.72      # tuned after Phase 3 verification (EC-4.14)
CONTEXT_WINDOW_BUDGET = 1500     # max tokens for assembled context

# LLM — Groq API (OpenAI-compatible interface)
# Groq provides ultra-low latency inference on open-source models
LLM_PROVIDER = "groq"
LLM_MODEL = "llama3-8b-8192"     # fast, free-tier friendly; swap to llama3-70b-8192 for higher quality
LLM_TEMPERATURE = 0.0
LLM_MAX_TOKENS = 200
LLM_TOP_P = 1.0

MAX_RESPONSE_SENTENCES = 3
MAX_QUERY_CHARS = 500            # hard query length limit (EC-4.10, EC-5.3)

# Financial term synonym map for query expansion (EC-4.4)
QUERY_SYNONYMS = {
    "management fee": "expense ratio",
    "redemption charge": "exit load",
    "redemption fee": "exit load",
    "tax saving fund": "ELSS",
    "tax saver": "ELSS",
    "equity linked savings": "ELSS",
    "lock in": "lock-in period",
    "minimum amount": "minimum investment",
    "min sip": "minimum SIP",
}

# Prohibited language patterns in generated responses (EC-4.5)
PROHIBITED_PHRASES = [
    r"\byou should\b",
    r"\brecommended\b",
    r"\bbest fund\b",
    r"\bbest option\b",
    r"\bsafe investment\b",
    r"\bgood option\b",
    r"\bperforms well\b",
    r"\bsuits your goals\b",
    r"\bsuitable for you\b",
    r"\badvised\b",
    r"\bwise choice\b",
    r"\bperfect for\b",
]

# Query classifier blocklist patterns (EC-4.1, EC-4.2)
REFUSED_PATTERNS = [
    r"\bshould i invest\b",
    r"\bis it worth\b",
    r"\bgood time to invest\b",
    r"\bwhich fund is best\b",
    r"\bbest fund\b",
    r"\bbest performing\b",
    r"\btop fund\b",
    r"\bsafest fund\b",
    r"\bcompare\b.*\bfund\b",
    r"\bfund\b.*\bvs\b.*\bfund\b",
    r"\bbetter than\b",
    r"\bwill it grow\b",
    r"\bexpected returns\b",
    r"\bbeat inflation\b",
    r"\bsuits my goals\b",
    r"\bright for me\b",
    r"\brecommend\b",
    r"\bshould i\b",
    r"\bwhich sip\b",
    r"\bwhich scheme\b.*\bbetter\b",
]

# ---------------------------------------------------------------------------
# Phase 5 — Frontend & Compliance
# ---------------------------------------------------------------------------
API_HOST = "0.0.0.0"
API_PORT = 8000
STREAMLIT_PORT = 8501

# PII detection patterns (EC-5.1, EC-5.2)
PII_PATTERNS = {
    "PAN": r"\b[A-Z]{5}[0-9]{4}[A-Z]\b",
    "Aadhaar": r"(^|\s)\d{4}[\s-]\d{4}[\s-]\d{4}(\s|$)",
    "Phone": r"(^|\s)[6-9]\d{9}(\s|$)",
    "Email": r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b",
}

AMFI_EDUCATION_URL = "https://www.amfiindia.com/investor-corner/knowledge-center"
AMFI_FALLBACK_URL = "https://www.amfiindia.com"
