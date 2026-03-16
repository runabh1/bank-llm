"""
RAG Engine for Bank LLM System
Retrieves relevant document chunks and generates grounded answers using local LLM.
Ensures no hallucination — answers only from retrieved context.
"""

import logging
from typing import Optional
from langchain_ollama import OllamaEmbeddings, OllamaLLM

from document_processor import get_collection, get_embeddings
from config import (
    LLM_MODEL,
    EMBED_MODEL,
    OLLAMA_BASE_URL,
    CHROMA_COLLECTION_INTERNAL,
    TOP_K_RESULTS,
    MIN_SIMILARITY_SCORE,
    SYSTEM_PROMPT,
)

logger = logging.getLogger(__name__)


# ─── LLM Setup ────────────────────────────────────────────────────────────────

def get_llm():
    return OllamaLLM(
        model=LLM_MODEL,
        base_url=OLLAMA_BASE_URL,
        temperature=0.1,       # Low temperature = more deterministic, less creative
        top_p=0.9,
        repeat_penalty=1.1,
        num_predict=2048,       # Enough room for detailed answers with citations
    )


# ─── Retrieval ────────────────────────────────────────────────────────────────

def retrieve_context(query: str, collection_names: list = None) -> list[dict]:
    """
    Query ChromaDB vector store for relevant chunks.
    Returns list of dicts with text, metadata, and similarity score.
    """
    if collection_names is None:
        collection_names = [CHROMA_COLLECTION_INTERNAL, "regulatory_docs"]

    embedder = get_embeddings()
    query_embedding = embedder.embed_query(query)

    all_results = []

    for col_name in collection_names:
        try:
            collection = get_collection(col_name)
            if collection.count() == 0:
                continue

            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=min(TOP_K_RESULTS, collection.count()),
                include=["documents", "metadatas", "distances"]
            )

            for i, doc in enumerate(results["documents"][0]):
                distance = results["distances"][0][i]
                # ChromaDB cosine distance: 0 = identical, 2 = opposite
                # Convert to similarity score (0 to 1)
                similarity = 1 - (distance / 2)

                logger.info(f"  [{col_name}] chunk {i}: sim={similarity:.3f} file={results['metadatas'][0][i].get('filename','?')} preview={doc[:80]}...")

                if similarity >= MIN_SIMILARITY_SCORE:
                    meta = results["metadatas"][0][i]
                    all_results.append({
                        "text": doc,
                        "similarity": similarity,
                        "filename": meta.get("filename", "Unknown"),
                        "ref_no": meta.get("ref_no", "N/A"),
                        "date": meta.get("date", "N/A"),
                        "authority": meta.get("authority", "N/A"),
                        "collection": col_name,
                    })
                else:
                    logger.info(f"    -> SKIPPED (below {MIN_SIMILARITY_SCORE} threshold)")

        except Exception as e:
            logger.warning(f"Error querying collection {col_name}: {e}")
            continue

    # Sort by similarity (highest first) and deduplicate
    all_results.sort(key=lambda x: x["similarity"], reverse=True)

    # Deduplicate: remove near-identical chunks
    seen_texts = set()
    unique_results = []
    for r in all_results:
        text_key = r["text"][:100]  # First 100 chars as fingerprint
        if text_key not in seen_texts:
            seen_texts.add(text_key)
            unique_results.append(r)

    return unique_results[:TOP_K_RESULTS]


# ─── Context Formatter ────────────────────────────────────────────────────────

def format_context(retrieved_chunks: list[dict]) -> str:
    """Format retrieved chunks into a context string for the LLM."""
    if not retrieved_chunks:
        return "No relevant documents found in the knowledge base."

    context_parts = []
    for i, chunk in enumerate(retrieved_chunks, 1):
        source_info = f"[Document {i}]"
        if chunk["ref_no"] != "N/A":
            source_info += f" Ref: {chunk['ref_no']}"
        if chunk["date"] != "N/A":
            source_info += f" | Date: {chunk['date']}"
        if chunk["authority"] != "N/A":
            source_info += f" | Authority: {chunk['authority']}"
        source_info += f" | File: {chunk['filename']}"

        context_parts.append(f"{source_info}\n{chunk['text']}")

    separator = "\n\n" + "─" * 60 + "\n\n"
    return separator + separator.join(context_parts)


# ─── Answer Generation ────────────────────────────────────────────────────────

def generate_answer(query: str, context: str) -> str:
    """Generate an answer using the local LLM with strict grounding."""
    llm = get_llm()

    prompt = SYSTEM_PROMPT.format(context=context) + f"\n\nUser Query: {query}\n\nAnswer:"

    try:
        response = llm.invoke(prompt)
        return response.strip()
    except Exception as e:
        logger.error(f"LLM generation error: {e}")
        return f"Error generating response: {str(e)}. Please check if Ollama is running."


# ─── Main RAG Pipeline ────────────────────────────────────────────────────────

def ask(query: str) -> dict:
    """
    Full RAG pipeline:
    1. Retrieve relevant chunks
    2. Format context
    3. Generate grounded answer
    4. Return answer + sources
    """
    logger.info(f"Query: {query}")

    # Step 1: Retrieve
    retrieved = retrieve_context(query)

    if not retrieved:
        return {
            "answer": "I don't have information about this topic in the available circulars and documents. "
                      "No relevant content was found in the knowledge base. "
                      "Please consult the relevant department or refer to the original source.",
            "sources": [],
            "chunks_found": 0,
        }

    # Step 2: Format context
    context = format_context(retrieved)

    # Step 3: Generate
    answer = generate_answer(query, context)

    # Step 4: Build source citations
    sources = []
    seen_files = set()
    for chunk in retrieved:
        fname = chunk["filename"]
        if fname not in seen_files:
            seen_files.add(fname)
            sources.append({
                "filename": fname,
                "ref_no": chunk["ref_no"],
                "date": chunk["date"],
                "authority": chunk["authority"],
                "relevance": round(chunk["similarity"] * 100, 1),
                "collection": chunk["collection"],
            })

    logger.info(f"  Retrieved {len(retrieved)} chunks, citing {len(sources)} sources")

    return {
        "answer": answer,
        "sources": sources,
        "chunks_found": len(retrieved),
    }


if __name__ == "__main__":
    # Quick test
    result = ask("What is the interest rate for home loans?")
    print("Answer:", result["answer"])
    print("\nSources:")
    for s in result["sources"]:
        print(f"  - {s['filename']} | Ref: {s['ref_no']} | Date: {s['date']}")
