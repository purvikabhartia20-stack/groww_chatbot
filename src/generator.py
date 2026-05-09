"""
Phase 4 — Step 6: LLM Generation via Groq API
===============================================
Calls the Groq API with constrained parameters to generate a grounded,
compliance-safe response from the assembled context.

Model: llama3-8b-8192
Temperature: 0.0 — fully deterministic, no creative generation
EC-4.12: retry on Groq API failure with graceful error message.
"""

import logging
import os
import time

from dotenv import load_dotenv
from groq import Groq, APIError, APIConnectionError, RateLimitError

load_dotenv(override=True)

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# LLM parameters
# ---------------------------------------------------------------------------
LLM_TEMPERATURE = 0.0
LLM_MAX_TOKENS = 200
LLM_TOP_P = 1.0

MAX_RETRIES = 2
RETRY_DELAY_SECONDS = 5

# Groq client (initialised once)
_client: Groq | None = None


def _get_client() -> Groq:
    global _client
    if _client is None:
        # Re-read env on every new client creation (supports .env changes)
        load_dotenv(override=True)
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError(
                "GROQ_API_KEY not found. "
                "Add it to your .env file: GROQ_API_KEY=gsk_..."
            )
        _client = Groq(api_key=api_key)
    return _client


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def generate(system_prompt: str, user_prompt: str) -> str | None:
    """
    Call the Groq API and return the generated text.

    Returns None if all retries fail (caller handles fallback).
    EC-4.12: retries twice with delay before giving up.
    """
    client = _get_client()

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            # Read model fresh each call so .env changes take effect without restart
            model = os.getenv("LLM_MODEL", "llama-3.1-8b-instant")
            log.debug(f"Groq API call attempt {attempt}/{MAX_RETRIES} (model: {model})")

            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user",   "content": user_prompt},
                ],
                temperature=LLM_TEMPERATURE,
                max_tokens=LLM_MAX_TOKENS,
                top_p=LLM_TOP_P,
            )

            text = response.choices[0].message.content
            if text:
                log.debug(f"Groq response received ({len(text)} chars)")
                return text.strip()

            log.warning("Groq returned empty content.")
            return None

        except RateLimitError as e:
            wait = RETRY_DELAY_SECONDS * (attempt * 3)  # 15s, 30s
            log.warning(f"Groq rate limit hit (attempt {attempt}), waiting {wait}s: {e}")
            if attempt < MAX_RETRIES:
                time.sleep(wait)

        except APIConnectionError as e:
            log.error(f"Groq connection error (attempt {attempt}): {e}")
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY_SECONDS)

        except APIError as e:
            log.error(f"Groq API error (attempt {attempt}): {e}")
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY_SECONDS)

        except Exception as e:
            log.error(f"Unexpected error calling Groq (attempt {attempt}): {e}")
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY_SECONDS)

    log.error(f"All {MAX_RETRIES} Groq API attempts failed.")
    return None
