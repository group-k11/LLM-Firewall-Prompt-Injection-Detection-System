"""
LLM Connector
Provides OpenRouterLLMConnector, OllamaLLMConnector and a unified call_llm() function.

Fallback chain: OpenRouter → Ollama → error
Timeout: 10 seconds (configurable via config.py)
"""

import time
import httpx

from config import (
    OPENROUTER_API_KEY, OPENROUTER_MODEL,
    OLLAMA_URL, OLLAMA_MODEL,
    LLM_TIMEOUT, SYSTEM_PROMPT,
)


# ---------------------------------------------------------------------------
# OpenRouter Connector
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
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost:3000",  # required by OpenRouter
            "X-Title": "LLM Firewall",
        }
        payload = {
            "model": OPENROUTER_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.7,
            "max_tokens": 1024,
        }

        t0 = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=LLM_TIMEOUT) as client:
                resp = await client.post(self.BASE_URL, json=payload, headers=headers)
                resp.raise_for_status()
                data = resp.json()
                response_text = data["choices"][0]["message"]["content"]
                elapsed_ms = round((time.perf_counter() - t0) * 1000, 1)
                return {
                    "success": True,
                    "response": response_text,
                    "provider": "openrouter",
                    "response_time_ms": elapsed_ms,
                }
        except httpx.TimeoutException:
            return {"success": False, "error": "OpenRouter timeout"}
        except Exception as e:
            return {"success": False, "error": f"OpenRouter error: {str(e)}"}


# ---------------------------------------------------------------------------
# Ollama Connector
# ---------------------------------------------------------------------------

class OllamaLLMConnector:
    """Calls a local Ollama instance."""

    def is_available(self) -> bool:
        return bool(OLLAMA_URL)

    async def call(self, prompt: str, system_prompt: str = SYSTEM_PROMPT) -> dict:
        url = f"{OLLAMA_URL.rstrip('/')}/api/generate"
        payload = {
            "model": OLLAMA_MODEL,
            "prompt": f"{system_prompt}\n\nUser: {prompt}",
            "stream": False,
        }

        t0 = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=LLM_TIMEOUT) as client:
                resp = await client.post(url, json=payload)
                resp.raise_for_status()
                data = resp.json()
                response_text = data.get("response", "")
                elapsed_ms = round((time.perf_counter() - t0) * 1000, 1)
                return {
                    "success": True,
                    "response": response_text,
                    "provider": "ollama",
                    "response_time_ms": elapsed_ms,
                }
        except httpx.TimeoutException:
            return {"success": False, "error": "Ollama timeout"}
        except Exception as e:
            return {"success": False, "error": f"Ollama error: {str(e)}"}


# ---------------------------------------------------------------------------
# Unified call_llm()
# ---------------------------------------------------------------------------

_openrouter = OpenRouterLLMConnector()
_ollama = OllamaLLMConnector()


async def call_llm(prompt: str, system_prompt: str = SYSTEM_PROMPT) -> dict:
    """
    Try OpenRouter first, fall back to Ollama on failure.

    Returns:
        {
            success: bool,
            response: str | None,
            provider: "openrouter" | "ollama" | "none",
            response_time_ms: float,
            error: str | None,
        }
    """
    # Try OpenRouter
    if _openrouter.is_available():
        result = await _openrouter.call(prompt, system_prompt)
        if result["success"]:
            return result
        print(f"[!] OpenRouter failed: {result.get('error')} — trying Ollama")

    # Fallback to Ollama
    if _ollama.is_available():
        result = await _ollama.call(prompt, system_prompt)
        if result["success"]:
            return result
        print(f"[!] Ollama failed: {result.get('error')}")

    return {
        "success": False,
        "response": None,
        "provider": "none",
        "response_time_ms": 0.0,
        "error": "All LLM providers unavailable",
    }


async def check_llm_status() -> dict:
    """Ping both providers and return their availability status."""
    openrouter_ok = False
    ollama_ok = False

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

    if _ollama.is_available():
        try:
            async with httpx.AsyncClient(timeout=3) as client:
                resp = await client.get(f"{OLLAMA_URL.rstrip('/')}/api/tags")
                ollama_ok = resp.status_code == 200
        except Exception:
            ollama_ok = False

    return {
        "openrouter": {"available": openrouter_ok, "model": OPENROUTER_MODEL if openrouter_ok else None},
        "ollama": {"available": ollama_ok, "model": OLLAMA_MODEL if ollama_ok else None},
        "active_provider": "openrouter" if openrouter_ok else ("ollama" if ollama_ok else "none"),
    }
