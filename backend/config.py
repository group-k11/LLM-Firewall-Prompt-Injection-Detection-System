"""
Configuration Module
Loads all environment variables for the LLM Firewall system.

LLM Provider Priority:
  1. Groq          (primary — llama3-8b-8192, ultra-fast inference, free tier)
  2. OpenRouter    (secondary cloud fallback)
  3. Ollama        (local fallback)
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Groq (Primary — ultra-fast inference, free tier available)
# Get your API key at: https://console.groq.com/keys
# ---------------------------------------------------------------------------
GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL:   str = os.getenv("GROQ_MODEL",   "llama3-8b-8192")

# ---------------------------------------------------------------------------
# OpenRouter (Secondary cloud fallback)
# Get your API key at: https://openrouter.ai/keys
# ---------------------------------------------------------------------------
OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL:   str = os.getenv("OPENROUTER_MODEL",   "openai/gpt-4o-mini")

# ---------------------------------------------------------------------------
# Ollama (Local fallback — no API key needed)
# ---------------------------------------------------------------------------
OLLAMA_URL:   str = os.getenv("OLLAMA_URL",   "http://localhost:11434")
OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "llama3")

# ---------------------------------------------------------------------------
# LLM Settings
# ---------------------------------------------------------------------------
LLM_TIMEOUT: int = int(os.getenv("LLM_TIMEOUT", "10"))

# System prompt sent to the LLM (never exposed to users)
SYSTEM_PROMPT: str = (
    "You are a helpful, harmless, and honest AI assistant. "
    "Answer questions clearly and concisely."
)
