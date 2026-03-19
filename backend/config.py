"""
Configuration for Bank LLM System
All settings in one place — edit here to customize.
"""

import os
from pathlib import Path

# ─── Paths ────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent
CIRCULARS_DIR = BASE_DIR / "circulars"
VECTOR_DB_DIR = BASE_DIR / "vector_db"
LOGS_DIR = BASE_DIR / "logs"

# Create directories if they don't exist
for d in [CIRCULARS_DIR, VECTOR_DB_DIR, LOGS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# ─── Ollama / LLM Settings ────────────────────────────────────────────────────
OLLAMA_BASE_URL = "http://localhost:11434"
LLM_MODEL = "llama3.2"          # Change to "mistral" or "llama3.1:8b" etc.
EMBED_MODEL = "nomic-embed-text" # Local embedding model via Ollama

# ─── ChromaDB Settings ────────────────────────────────────────────────────────
CHROMA_COLLECTION_INTERNAL = "bank_circulars"    # Internal bank circulars
CHROMA_COLLECTION_EXTERNAL = "regulatory_docs"   # RBI / NABARD / SEBI docs

# ─── RAG Settings ─────────────────────────────────────────────────────────────
CHUNK_SIZE = 1000           # Characters per chunk (larger = more context per chunk)
CHUNK_OVERLAP = 200         # Overlap between chunks (prevents splitting key info)
TOP_K_RESULTS = 8           # Number of chunks to retrieve per query
MIN_SIMILARITY_SCORE = 0.10 # Low threshold — let more chunks through for LLM to evaluate

# ─── Server Settings ──────────────────────────────────────────────────────────
SERVER_HOST = "0.0.0.0"     # Bind to all interfaces (LAN access)
SERVER_PORT = 8000
CORS_ORIGINS = ["*"]        # Allow all origins on LAN

# ─── Web Scraping (Secondary Learning) ────────────────────────────────────────
# Web scraping disabled - using uploaded documents only
SCRAPE_SOURCES = []

# ─── System Prompt (Anti-Hallucination) ───────────────────────────────────────
SYSTEM_PROMPT = """You are BankAssist, an AI assistant for bank staff. You are trained on internal bank circulars and regulatory documents from RBI, NABARD, and SEBI.

CRITICAL RULES — YOU MUST FOLLOW THESE WITHOUT EXCEPTION:
1. Answer ONLY using information from the provided context documents below.
2. If the context does not contain sufficient information to answer the question, respond with: "I don't have information about this topic in the available circulars and documents. Please consult the relevant department or check the original source."
3. NEVER guess, infer, or make up information that is not explicitly in the context.
4. ALWAYS cite the source: include the Circular Reference Number, Date, and Issuing Authority if available.
5. If multiple circulars are relevant, cite all of them.
6. Be precise and factual. Bank data is sensitive and critical.
7. If a circular has been superseded by a newer one in the context, mention that.

FORMAT YOUR RESPONSE AS:
- Direct answer to the query
- Source: [Circular/Document Reference] | Date: [Date] | Issued by: [Authority]

Context Documents:
{context}

Remember: If the answer is not in the context above, say so clearly. Do not fabricate information."""
