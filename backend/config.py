"""
Configuration Module
Loads all environment variables for the LLM Firewall system.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# OpenRouter
OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL: str = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini")

# Ollama
OLLAMA_URL: str = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "llama3")

# LLM Settings
LLM_TIMEOUT: int = int(os.getenv("LLM_TIMEOUT", "10"))

# System prompt sent to the LLM (never leaked to users)
SYSTEM_PROMPT: str = (
    "You are a helpful, harmless, and honest AI assistant. "
    "Answer questions clearly and concisely."
)
