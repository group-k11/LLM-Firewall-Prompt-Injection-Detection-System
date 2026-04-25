"""
LLM Connector — LLM Firewall v2.0

Fallback chain:
  1. Groq (primary — llama3-8b-8192, ultra-fast, free tier)
  2. OpenRouter (secondary cloud fallback)
  3. Ollama (local fallback)

Timeout: 10 seconds (configurable via config.py)
"""

import time
import httpx

from config import (
    GROQ_API_KEY, GROQ_MODEL,
    OPENROUTER_API_KEY, OPENROUTER_MODEL,
    OLLAMA_URL, OLLAMA_MODEL,
    LLM_TIMEOUT, SYSTEM_PROMPT,
)


# ---------------------------------------------------------------------------
# Groq Connector (Primary)
# ---------------------------------------------------------------------------

class GroqLLMConnector:
    """Calls the Groq REST API (OpenAI-compatible endpoint)."""

    BASE_URL = "https://api.groq.com/openai/v1/chat/completions"

    def is_available(self) -> bool:
        return bool(GROQ_API_KEY)

    async def call(self, prompt: str, system_prompt: str = SYSTEM_PROMPT) -> dict:
        if not self.is_available():
            return {"success": False, "error": "GROQ_API_KEY not set"}

        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": GROQ_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": prompt},
            ],
            "temperature": 0.7,
            "max_tokens": 1024,
        }

        t0 = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=LLM_TIMEOUT) as client:
                resp = await client.post(self.BASE_URL, json=payload, headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
                    choices = data.get("choices", [])
                    if choices:
                        content = choices[0].get("message", {}).get("content", "")
                        return {
                            "success":         True,
                            "response":        content,
                            "provider":        "groq",
                            "model":           GROQ_MODEL,
                            "response_time_ms": round((time.perf_counter() - t0) * 1000, 1),
                        }
                    return {"success": False, "error": "Empty response from Groq"}
                return {
                    "success": False,
                    "error":   f"Groq HTTP {resp.status_code}: {resp.text[:200]}",
                }
        except httpx.TimeoutException:
            return {"success": False, "error": "Groq timeout"}
        except Exception as e:
            return {"success": False, "error": f"Groq error: {e}"}


# ---------------------------------------------------------------------------
# OpenRouter Connector (Secondary)
# ---------------------------------------------------------------------------

class OpenRouterLLMConnector:
    """Calls the OpenRouter REST API (OpenAI-compatible)."""

    BASE_URL = "https://openrouter.ai/api/v1/chat/completions"

    def is_available(self) -> bool:
        return bool(OPENROUTER_API_KEY)

    async def call(self, prompt: str, system_prompt: str = SYSTEM_PROMPT) -> dict:
        if not self.is_available():
            return {"success": False, "error": "OPENROUTER_API_KEY not set"}

        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type":  "application/json",
            "HTTP-Referer":  "http://localhost:3000",
            "X-Title":       "LLM Firewall",
        }
        payload = {
            "model": OPENROUTER_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": prompt},
            ],
            "temperature": 0.7,
            "max_tokens":  1024,
        }

        t0 = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=LLM_TIMEOUT) as client:
                resp = await client.post(self.BASE_URL, json=payload, headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
                    choices = data.get("choices", [])
                    if choices:
                        content = choices[0].get("message", {}).get("content", "")
                        return {
                            "success":         True,
                            "response":        content,
                            "provider":        "openrouter",
                            "model":           OPENROUTER_MODEL,
                            "response_time_ms": round((time.perf_counter() - t0) * 1000, 1),
                        }
                    return {"success": False, "error": "Empty response from OpenRouter"}
                resp.raise_for_status()
        except httpx.TimeoutException:
            return {"success": False, "error": "OpenRouter timeout"}
        except Exception as e:
            return {"success": False, "error": f"OpenRouter error: {e}"}


# ---------------------------------------------------------------------------
# Ollama Connector (Local fallback)
# ---------------------------------------------------------------------------

class OllamaLLMConnector:
    """Calls a local Ollama instance."""

    def is_available(self) -> bool:
        return bool(OLLAMA_URL)

    async def call(self, prompt: str, system_prompt: str = SYSTEM_PROMPT) -> dict:
        url = f"{OLLAMA_URL.rstrip('/')}/api/generate"
        payload = {
            "model":  OLLAMA_MODEL,
            "prompt": f"{system_prompt}\n\nUser: {prompt}",
            "stream": False,
        }

        t0 = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=LLM_TIMEOUT) as client:
                resp = await client.post(url, json=payload)
                resp.raise_for_status()
                data = resp.json()
                return {
                    "success":         True,
                    "response":        data.get("response", ""),
                    "provider":        "ollama",
                    "model":           OLLAMA_MODEL,
                    "response_time_ms": round((time.perf_counter() - t0) * 1000, 1),
                }
        except httpx.TimeoutException:
            return {"success": False, "error": "Ollama timeout"}
        except Exception as e:
            return {"success": False, "error": f"Ollama error: {e}"}


# ---------------------------------------------------------------------------
# Singleton connectors
# ---------------------------------------------------------------------------

_groq        = GroqLLMConnector()
_openrouter  = OpenRouterLLMConnector()
_ollama      = OllamaLLMConnector()


# ---------------------------------------------------------------------------
# Unified call_llm() — Groq → OpenRouter → Ollama
# ---------------------------------------------------------------------------

async def call_llm(prompt: str, system_prompt: str = SYSTEM_PROMPT) -> dict:
    """
    Try Groq first, then OpenRouter, then Ollama.

    Returns:
        {
          success: bool,
          response: str | None,
          provider: "groq" | "openrouter" | "ollama" | "none",
          model: str | None,
          response_time_ms: float,
          error: str | None,
        }
    """
    # 1 — Groq (primary)
    if _groq.is_available():
        result = await _groq.call(prompt, system_prompt)
        if result["success"]:
            return result
        print(f"[!] Groq failed: {result.get('error')} — trying OpenRouter")

    # 2 — OpenRouter (secondary)
    if _openrouter.is_available():
        result = await _openrouter.call(prompt, system_prompt)
        if result["success"]:
            return result
        print(f"[!] OpenRouter failed: {result.get('error')} — trying Ollama")

    # 3 — Ollama (local)
    if _ollama.is_available():
        result = await _ollama.call(prompt, system_prompt)
        if result["success"]:
            return result
        print(f"[!] Ollama failed: {result.get('error')}")

    return {
        "success":         False,
        "response":        None,
        "provider":        "none",
        "model":           None,
        "response_time_ms": 0.0,
        "error":           "All LLM providers unavailable",
    }


# ---------------------------------------------------------------------------
# Status check — ping all three providers
# ---------------------------------------------------------------------------

async def check_llm_status() -> dict:
    """Ping all providers and return their availability + active provider."""
    groq_ok       = False
    openrouter_ok = False
    ollama_ok     = False

    # Check Groq
    if _groq.is_available():
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(
                    "https://api.groq.com/openai/v1/models",
                    headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
                )
                groq_ok = resp.status_code == 200
        except Exception:
            groq_ok = False

    # Check OpenRouter
    if _openrouter.is_available():
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(
                    "https://openrouter.ai/api/v1/models",
                    headers={"Authorization": f"Bearer {OPENROUTER_API_KEY}"},
                )
                openrouter_ok = resp.status_code == 200
        except Exception:
            openrouter_ok = False

    # Check Ollama
    if _ollama.is_available():
        try:
            async with httpx.AsyncClient(timeout=3) as client:
                resp = await client.get(f"{OLLAMA_URL.rstrip('/')}/api/tags")
                ollama_ok = resp.status_code == 200
        except Exception:
            ollama_ok = False

    if groq_ok:
        active_provider = "groq"
    elif openrouter_ok:
        active_provider = "openrouter"
    elif ollama_ok:
        active_provider = "ollama"
    else:
        active_provider = "none"

    return {
        "groq": {
            "available": groq_ok,
            "model":     GROQ_MODEL if groq_ok else None,
        },
        "openrouter": {
            "available": openrouter_ok,
            "model":     OPENROUTER_MODEL if openrouter_ok else None,
        },
        "ollama": {
            "available": ollama_ok,
            "model":     OLLAMA_MODEL if ollama_ok else None,
        },
        "active_provider": active_provider,
    }
