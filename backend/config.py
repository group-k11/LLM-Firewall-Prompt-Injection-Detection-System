"""
Configuration Module
Loads all environment variables for the LLM Firewall system.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# Groq
GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama3-8b-8192")

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
