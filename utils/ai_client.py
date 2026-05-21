"""
Unified AI client with model tiering and automatic fallback.
Replaces 12 duplicate get_ai_response() functions across the codebase.

Usage:
    from utils.ai_client import ai_response, safe_json

    text = ai_response(prompt, task="classify")     # Fast/cheap tier
    text = ai_response(prompt, task="generate")     # Quality tier
    text = ai_response(prompt, task="creative")     # Premium tier (still uses sonnet)
"""

import os
import json
import re
import time
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# ─────────────────────────────────────────────────────────────────────────────
# TASK TIERS — map task types to models and default token limits
# ─────────────────────────────────────────────────────────────────────────────
TASK_TIERS = {
    # Tier 1: Fast/cheap — classification, verification, short extraction
    "classify":  {"max_tokens": 500},
    "verify":    {"max_tokens": 500},

    # Tier 2: Standard — auditing, enrichment, reply drafting
    "audit":     {"max_tokens": 1500},
    "enrich":    {"max_tokens": 800},
    "reply":     {"max_tokens": 600},

    # Tier 3: Quality — message writing, decisions
    "generate":  {"max_tokens": 1500},
    "decide":    {"max_tokens": 1500},

    # Tier 4: Creative — site building, complex content (high token limit)
    "creative":  {"max_tokens": 4000},
}

# Models
CLAUDE_MODEL = "claude-sonnet-4-20250514"
GROQ_MODEL = "llama-3.3-70b-versatile"
GROQ_FALLBACK_MODELS = ["mixtral-8x7b-32768", "llama-3.1-8b-instant"]

# Usage tracking
USAGE_LOG_PATH = "results/logs/ai_usage.json"


# ─────────────────────────────────────────────────────────────────────────────
# CORE AI FUNCTION
# ─────────────────────────────────────────────────────────────────────────────
def ai_response(
    prompt: str,
    task: str = "generate",
    max_tokens: int = None,
    retry: int = 2,
    prefer_free: bool = False
) -> str:
    """
    Get an AI response with automatic model selection and fallback.

    Args:
        prompt:      The prompt to send
        task:        Task tier key (classify, verify, audit, enrich, reply, generate, decide, creative)
        max_tokens:  Override default max_tokens for the task tier
        retry:       Number of retry attempts on rate limits
        prefer_free: If True, try Groq (free) first before Claude (paid)

    Returns:
        The AI response text, or "" if all providers fail
    """
    tier = TASK_TIERS.get(task, TASK_TIERS["generate"])
    tokens = max_tokens or tier["max_tokens"]

    if prefer_free:
        return _try_groq_then_claude(prompt, tokens, retry)
    else:
        return _try_claude_then_groq(prompt, tokens, retry)


def _try_claude_then_groq(prompt: str, max_tokens: int, retry: int) -> str:
    """Try Claude first, fall back to Groq on any error."""
    for attempt in range(retry):
        # Try Claude
        try:
            text = _call_claude(prompt, max_tokens)
            _log_usage("claude", CLAUDE_MODEL, max_tokens)
            return text
        except Exception as e:
            error = str(e).lower()
            if "rate" in error or "limit" in error:
                wait = (attempt + 1) * 15
                print(f"   ⏳ Claude rate limited — waiting {wait}s...")
                time.sleep(wait)
                continue

            # Non-rate-limit error → try Groq fallback
            text = _try_groq_chain(prompt, max_tokens)
            if text:
                return text

            # If Groq also failed and we have retries left, wait and retry
            if attempt < retry - 1:
                wait = (attempt + 1) * 10
                time.sleep(wait)
                continue

    return ""


def _try_groq_then_claude(prompt: str, max_tokens: int, retry: int) -> str:
    """Try Groq (free) first, fall back to Claude as last resort."""
    # Try all Groq models/keys first
    text = _try_groq_chain(prompt, max_tokens)
    if text:
        return text

    # Fall back to Claude
    for attempt in range(retry):
        try:
            text = _call_claude(prompt, max_tokens)
            _log_usage("claude", CLAUDE_MODEL, max_tokens)
            return text
        except Exception as e:
            error = str(e).lower()
            if "rate" in error or "limit" in error:
                wait = (attempt + 1) * 15
                print(f"   ⏳ Claude rate limited — waiting {wait}s...")
                time.sleep(wait)
                continue
            if attempt < retry - 1:
                continue
            print(f"   ❌ All AI models failed.")
            raise e

    return ""


# ─────────────────────────────────────────────────────────────────────────────
# PROVIDER CALLS
# ─────────────────────────────────────────────────────────────────────────────
def _call_claude(prompt: str, max_tokens: int) -> str:
    """Call Claude API. Raises on failure."""
    from anthropic import Anthropic

    api_key = os.getenv("CLAUDE_API_KEY")
    if not api_key:
        raise ValueError("CLAUDE_API_KEY not set")

    client = Anthropic(api_key=api_key)
    response = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}]
    )
    return response.content[0].text


def _try_groq_chain(prompt: str, max_tokens: int) -> str:
    """Try all Groq API keys × models. Returns text or None."""
    from groq import Groq

    groq_keys = [os.getenv("GROQ_API_KEY"), os.getenv("GROQ_API_KEY_BK")]
    groq_keys = [k for k in groq_keys if k]

    if not groq_keys:
        return None

    models = [GROQ_MODEL] + GROQ_FALLBACK_MODELS

    for model_name in models:
        for api_key in groq_keys:
            try:
                client = Groq(api_key=api_key)
                response = client.chat.completions.create(
                    model=model_name,
                    max_tokens=max_tokens,
                    messages=[{"role": "user", "content": prompt}]
                )
                _log_usage("groq", model_name, max_tokens)
                return response.choices[0].message.content
            except Exception as e:
                error_msg = str(e).lower()
                if "rate" in error_msg or "limit" in error_msg:
                    continue
                continue

    return None


# ─────────────────────────────────────────────────────────────────────────────
# USAGE TRACKING
# ─────────────────────────────────────────────────────────────────────────────
def _log_usage(provider: str, model: str, max_tokens: int):
    """Track AI usage for cost monitoring."""
    try:
        os.makedirs("results/logs", exist_ok=True)
        log = {}
        if os.path.exists(USAGE_LOG_PATH):
            with open(USAGE_LOG_PATH, "r", encoding="utf-8") as f:
                log = json.load(f)

        today = datetime.now().strftime("%Y-%m-%d")
        if today not in log:
            log[today] = {}

        key = f"{provider}/{model}"
        if key not in log[today]:
            log[today][key] = {"calls": 0, "total_max_tokens": 0}

        log[today][key]["calls"] += 1
        log[today][key]["total_max_tokens"] += max_tokens

        with open(USAGE_LOG_PATH, "w", encoding="utf-8") as f:
            json.dump(log, f, indent=2, ensure_ascii=False)
    except Exception:
        pass  # Never let logging break the main flow


# ─────────────────────────────────────────────────────────────────────────────
# UTILITY: safe JSON parser (also consolidated from 12 files)
# ─────────────────────────────────────────────────────────────────────────────
def safe_json(text: str) -> dict:
    """Parse AI response text that may contain markdown-wrapped JSON."""
    try:
        clean = re.sub(r'```json|```', '', text).strip()
        start = clean.find('{')
        end = clean.rfind('}')
        if start != -1 and end != -1:
            return json.loads(clean[start:end+1])
    except Exception:
        pass
    return {}
