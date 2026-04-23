"""
LLM Connector
Provides GroqLLMConnector, OllamaLLMConnector and a unified call_llm() function.

Fallback chain: Groq → Ollama → error
Timeout: 10 seconds (configurable via config.py)
"""

import time
import asyncio
import httpx

from config import (
    GROQ_API_KEY, GROQ_MODEL,
    OLLAMA_URL, OLLAMA_MODEL,
    LLM_TIMEOUT, SYSTEM_PROMPT,
)


# ---------------------------------------------------------------------------
# Groq Connector
# ---------------------------------------------------------------------------

class GroqLLMConnector:
    """Calls the Groq REST API."""

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
                    "provider": "groq",
                    "response_time_ms": elapsed_ms,
                }
        except httpx.TimeoutException:
            return {"success": False, "error": "Groq timeout"}
        except Exception as e:
            return {"success": False, "error": f"Groq error: {str(e)}"}


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

_groq = GroqLLMConnector()
_ollama = OllamaLLMConnector()


async def call_llm(prompt: str, system_prompt: str = SYSTEM_PROMPT) -> dict:
    """
    Try Groq first, fall back to Ollama on failure.

    Returns:
        {
            success: bool,
            response: str | None,
            provider: "groq" | "ollama" | "none",
            response_time_ms: float,
            error: str | None,
        }
    """
    # Try Groq
    if _groq.is_available():
        result = await _groq.call(prompt, system_prompt)
        if result["success"]:
            return result
        print(f"[!] Groq failed: {result.get('error')} — trying Ollama")

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
    groq_ok = False
    ollama_ok = False

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

    if _ollama.is_available():
        try:
            async with httpx.AsyncClient(timeout=3) as client:
                resp = await client.get(f"{OLLAMA_URL.rstrip('/')}/api/tags")
                ollama_ok = resp.status_code == 200
        except Exception:
            ollama_ok = False

    return {
        "groq": {"available": groq_ok, "model": GROQ_MODEL if groq_ok else None},
        "ollama": {"available": ollama_ok, "model": OLLAMA_MODEL if ollama_ok else None},
        "active_provider": "groq" if groq_ok else ("ollama" if ollama_ok else "none"),
    }
