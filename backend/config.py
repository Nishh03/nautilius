"""Central configuration. Everything tweakable lives here or in .env."""
import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

# --- Vault -----------------------------------------------------------------
# The folder of markdown notes. Point this at an Obsidian vault to use one.
VAULT_PATH = Path(os.getenv("VAULT_PATH") or PROJECT_ROOT / "vault")

# Notes sitting directly in the vault root have no folder, so they get this name.
UNFILED_DOMAIN = "unfiled"

# --- LLM -------------------------------------------------------------------
# ollama = free and local. groq / gemini = free cloud tiers, need a key.
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama").lower()

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

# --- Retrieval -------------------------------------------------------------
TOP_K = int(os.getenv("TOP_K", "5"))          # notes sent to the LLM per question
MAX_NOTE_CHARS = int(os.getenv("MAX_NOTE_CHARS", "4000"))  # truncate huge notes

# --- Server ----------------------------------------------------------------
HOST = os.getenv("HOST", "127.0.0.1")
PORT = int(os.getenv("PORT", "8000"))
