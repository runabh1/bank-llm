"""
FastAPI Main Server for Bank LLM System
Exposes REST API endpoints consumed by the frontend.
Runs on 0.0.0.0 so it's accessible over LAN/Intranet.
"""

import shutil
import logging
import asyncio
from pathlib import Path
from typing import Optional
from datetime import datetime
from threading import Lock

import uvicorn
from fastapi import FastAPI, HTTPException, UploadFile, File, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from config import (
    SERVER_HOST, SERVER_PORT, CORS_ORIGINS,
    CIRCULARS_DIR, BASE_DIR, CHROMA_COLLECTION_INTERNAL
)
from document_processor import (
    ingest_document, get_ingestion_stats,
    list_ingested_files, get_collection, get_chroma_client, is_file_already_ingested
)
from rag_engine import ask
from web_scraper import run_web_scraping

# Global state for ingestion lock
ingestion_lock = Lock()
ingestion_in_progress = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ─── App Setup ────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Bank LLM API",
    description="Personalized LLM for Bank Staff — Powered by RAG",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve frontend files
FRONTEND_DIR = BASE_DIR / "frontend"
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


# ─── Pydantic Models ──────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    query: str
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    answer: str
    sources: list
    chunks_found: int
    timestamp: str


class DeleteDocRequest(BaseModel):
    filename: str


# ─── In-memory query log ──────────────────────────────────────────────────────
query_log: list[dict] = []


# ─── Routes ───────────────────────────────────────────────────────────────────

@app.get("/")
async def root():
    """Serve the frontend."""
    index_file = FRONTEND_DIR / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return {"message": "Bank LLM API is running. Frontend not found."}


@app.get("/admin")
async def admin():
    """Serve the admin panel."""
    admin_file = FRONTEND_DIR / "admin.html"
    if admin_file.exists():
        return FileResponse(str(admin_file))
    raise HTTPException(status_code=404, detail="Admin page not found")


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Main chat endpoint. Receives a query, runs RAG pipeline,
    returns grounded answer with citations.
    """
    global ingestion_in_progress
    
    # Prevent queries during ingestion
    if ingestion_in_progress:
        raise HTTPException(
            status_code=503,
            detail="System is currently ingesting documents. Please wait 30-60 seconds and try again."
        )
    
    if not request.query or len(request.query.strip()) < 3:
        raise HTTPException(status_code=400, detail="Query too short")

    query = request.query.strip()
    logger.info(f"Chat query: {query}")

    try:
        result = ask(query)

        response = ChatResponse(
            answer=result["answer"],
            sources=result["sources"],
            chunks_found=result["chunks_found"],
            timestamp=datetime.now().isoformat(),
        )

        # Log query
        query_log.append({
            "query": query,
            "answer_length": len(result["answer"]),
            "sources_count": len(result["sources"]),
            "timestamp": response.timestamp,
        })

        return response

    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@app.post("/api/ingest/upload")
async def upload_document(
    file: UploadFile = File(...),
):
    """
    Upload a circular (PDF/DOCX/XLSX/TXT) and ingest it into the vector store.
    Ingestion is done synchronously so the user gets immediate feedback.
    """
    global ingestion_in_progress
    
    allowed_extensions = {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".txt"}
    suffix = Path(file.filename).suffix.lower()

    if suffix not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {suffix}. Allowed: {', '.join(allowed_extensions)}"
        )

    # Save file to circulars directory
    save_path = CIRCULARS_DIR / file.filename
    with open(save_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    logger.info(f"Saved uploaded file to {save_path}")

    # Check if file is already ingested to prevent duplicates
    if is_file_already_ingested(file.filename):
        logger.info(f"File {file.filename} already ingested, skipping")
        return {
            "status": "skipped",
            "filename": file.filename,
            "message": f"File already ingested previously. No duplicate indexing needed."
        }

    # Mark ingestion as in progress
    with ingestion_lock:
        ingestion_in_progress = True
    
    # Ingest synchronously so the user knows if it worked
    try:
        result = ingest_document(save_path)
        if result.get("status") == "error":
            logger.warning(f"Ingestion failed for {file.filename}: {result.get('message')}")
            return {
                "status": "error",
                "filename": file.filename,
                "message": f"File saved but ingestion failed: {result.get('message', 'Could not extract text from the file')}. "
                           f"The file may be empty, scanned (image-only PDF), or corrupted."
            }

        return {
            "status": "success",
            "filename": file.filename,
            "chunks": result.get("chunks", 0),
            "message": f"File uploaded and ingested successfully! "
                       f"{result.get('chunks', 0)} text chunks indexed and ready for queries."
        }
    except Exception as e:
        logger.error(f"Ingestion error for {file.filename}: {e}")
        return {
            "status": "error",
            "filename": file.filename,
            "message": f"File saved but ingestion encountered an error: {str(e)}"
        }
    finally:
        # Mark ingestion as complete
        with ingestion_lock:
            ingestion_in_progress = False


@app.post("/api/ingest/folder")
async def ingest_folder(background_tasks: BackgroundTasks):
    """
    Ingest all documents in the circulars/ folder.
    Only ingests files that haven't been ingested before.
    """
    global ingestion_in_progress
    
    supported_ext = {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".txt"}
    files = [f for f in CIRCULARS_DIR.glob("**/*") if f.suffix.lower() in supported_ext]

    if not files:
        return {"status": "no_files", "message": "No supported files found in circulars/ folder"}

    # Filter out already ingested files
    files_to_ingest = [f for f in files if not is_file_already_ingested(f.name)]
    
    if not files_to_ingest:
        return {"status": "all_ingested", "message": "All files in circulars/ folder have already been ingested."}
    
    logger.info(f"Found {len(files_to_ingest)} new files to ingest out of {len(files)} total")
    
    with ingestion_lock:
        ingestion_in_progress = True
    
    background_tasks.add_task(_ingest_all, files_to_ingest)

    return {
        "status": "processing",
        "files_found": len(files),
        "message": f"Found {len(files)} files. Ingestion started in background."
    }


@app.post("/api/ingest/reingest")
async def reingest_all(background_tasks: BackgroundTasks):
    """
    Clear the entire vector DB collection and re-ingest all documents fresh.
    This is critical when RAG parameters (chunk size, overlap, etc.) have changed.
    """
    supported_ext = {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".txt"}
    files = [f for f in CIRCULARS_DIR.glob("**/*") if f.suffix.lower() in supported_ext]

    if not files:
        return {"status": "no_files", "message": "No supported files found in circulars/ folder"}

    # Clear the existing collection completely
    try:
        client = get_chroma_client()
        try:
            client.delete_collection(CHROMA_COLLECTION_INTERNAL)
            logger.info("Deleted old collection for clean re-ingestion")
        except Exception:
            pass  # Collection might not exist yet
    except Exception as e:
        logger.warning(f"Could not clear collection: {e}")

    background_tasks.add_task(_ingest_all, files)

    return {
        "status": "processing",
        "files_found": len(files),
        "message": f"Cleared vector DB. Re-ingesting {len(files)} files from scratch in background."
    }


async def _ingest_all(files: list[Path]):
    """Run blocking ingestion in a thread pool to avoid blocking the event loop."""
    global ingestion_in_progress
    import concurrent.futures

    loop = asyncio.get_event_loop()
    results = []

    try:
        for f in files:
            try:
                result = await loop.run_in_executor(None, ingest_document, f)
                results.append(result)
                logger.info(f"  Bulk ingest result for {f.name}: {result.get('status')}")
            except Exception as e:
                logger.error(f"  Bulk ingest error for {f.name}: {e}")
                results.append({"status": "error", "file": f.name, "message": str(e)})

        success = sum(1 for r in results if r.get("status") == "success")
        errors = sum(1 for r in results if r.get("status") == "error")
        logger.info(f"Bulk ingestion complete: {success} succeeded, {errors} failed out of {len(results)} files")
    finally:
        # Mark ingestion as complete
        with ingestion_lock:
            ingestion_in_progress = False


@app.post("/api/ingest/web")
async def ingest_web_sources(background_tasks: BackgroundTasks):
    """
    Web scraping is disabled. Please upload documents directly to the circulars/ folder
    or use the /api/ingest/upload endpoint.
    """
    return {
        "status": "disabled",
        "message": "Web scraping is currently disabled. Please upload documents directly using the /api/ingest/upload endpoint or place them in the circulars/ folder and use /api/ingest/folder."
    }


@app.delete("/api/documents/{filename}")
async def delete_document(filename: str):
    """
    Remove a document from the vector store (and optionally the circulars folder).
    """
    try:
        collection = get_collection(CHROMA_COLLECTION_INTERNAL)
        existing = collection.get(where={"filename": filename})
        if not existing["ids"]:
            raise HTTPException(status_code=404, detail=f"Document '{filename}' not found in knowledge base")

        collection.delete(ids=existing["ids"])

        # Optionally delete the file
        file_path = CIRCULARS_DIR / filename
        if file_path.exists():
            file_path.unlink()

        return {
            "status": "deleted",
            "filename": filename,
            "chunks_removed": len(existing["ids"])
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/documents")
async def list_documents():
    """List all ingested documents with their metadata."""
    internal = list_ingested_files(CHROMA_COLLECTION_INTERNAL)
    external = list_ingested_files("regulatory_docs")
    return {
        "internal_circulars": internal,
        "regulatory_docs": external,
    }


@app.get("/api/status")
async def get_status():
    """System health check and stats."""
    stats = get_ingestion_stats()
    return {
        "status": "online",
        "timestamp": datetime.now().isoformat(),
        "vector_db": stats,
        "queries_served": len(query_log),
        "ollama_model": "llama3.2",
        "server": f"http://{SERVER_HOST}:{SERVER_PORT}",
    }


@app.get("/api/logs")
async def get_query_logs():
    """Return recent query logs (last 50)."""
    return {"logs": query_log[-50:]}


# ─── Startup ──────────────────────────────────────────────────────────────────

@app.on_event("startup")
async def startup_event():
    logger.info("=" * 60)
    logger.info("  Bank LLM System Starting Up")
    logger.info(f"  Server: http://0.0.0.0:{SERVER_PORT}")
    logger.info(f"  Circulars Dir: {CIRCULARS_DIR}")
    logger.info(f"  Vector DB: {BASE_DIR / 'vector_db'}")
    logger.info("=" * 60)

    # Log vector DB stats
    stats = get_ingestion_stats()
    for col, count in stats.items():
        logger.info(f"  Vector DB [{col}]: {count} chunks")


# ─── Entry Point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=SERVER_HOST,
        port=SERVER_PORT,
        reload=False,
        log_level="info",
    )
