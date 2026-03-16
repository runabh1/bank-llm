"""
Web Scraper for Secondary Learning
Fetches public circulars from RBI, NABARD, SEBI websites.
"""

import logging
import time
from typing import Optional
import requests
from bs4 import BeautifulSoup
from datetime import datetime

from document_processor import ingest_text
from config import SCRAPE_SOURCES, CHROMA_COLLECTION_EXTERNAL

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}
TIMEOUT = 30


def fetch_page(url: str) -> Optional[str]:
    """Fetch a webpage and return its text content."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.content, "html.parser")

        # Remove scripts, styles, nav
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()

        # Get main content
        main = soup.find("main") or soup.find("article") or soup.find("div", {"id": "content"}) or soup.body
        if main:
            return main.get_text(separator="\n", strip=True)
        return soup.get_text(separator="\n", strip=True)
    except Exception as e:
        logger.error(f"Failed to fetch {url}: {e}")
        return None


def scrape_rbi(url: str) -> list[dict]:
    """Scrape RBI circulars listing page."""
    text = fetch_page(url)
    if not text:
        return []
    return [{
        "text": text,
        "metadata": {
            "filename": "rbi_circulars_web.txt",
            "ref_no": "RBI-WEB",
            "date": datetime.now().strftime("%Y-%m-%d"),
            "authority": "RBI",
            "source_url": url,
            "ingested_at": datetime.now().isoformat(),
        }
    }]


def scrape_nabard(url: str) -> list[dict]:
    """Scrape NABARD notifications."""
    text = fetch_page(url)
    if not text:
        return []
    return [{
        "text": text,
        "metadata": {
            "filename": "nabard_notifications_web.txt",
            "ref_no": "NABARD-WEB",
            "date": datetime.now().strftime("%Y-%m-%d"),
            "authority": "NABARD",
            "source_url": url,
            "ingested_at": datetime.now().isoformat(),
        }
    }]


def scrape_sebi(url: str) -> list[dict]:
    """Scrape SEBI circulars."""
    text = fetch_page(url)
    if not text:
        return []
    return [{
        "text": text,
        "metadata": {
            "filename": "sebi_circulars_web.txt",
            "ref_no": "SEBI-WEB",
            "date": datetime.now().strftime("%Y-%m-%d"),
            "authority": "SEBI",
            "source_url": url,
            "ingested_at": datetime.now().isoformat(),
        }
    }]


SCRAPERS = {
    "rbi": scrape_rbi,
    "nabard": scrape_nabard,
    "sebi": scrape_sebi,
}


def run_web_scraping() -> dict:
    """
    Scrape all configured sources and ingest into regulatory_docs collection.
    Returns a summary of results.
    """
    results = []
    total_ingested = 0

    for source in SCRAPE_SOURCES:
        logger.info(f"Scraping: {source['name']} from {source['url']}")
        scraper_fn = SCRAPERS.get(source["type"])
        if not scraper_fn:
            logger.warning(f"No scraper for type: {source['type']}")
            continue

        try:
            docs = scraper_fn(source["url"])
            for doc in docs:
                if doc["text"] and len(doc["text"]) > 100:
                    result = ingest_text(
                        text=doc["text"],
                        metadata=doc["metadata"],
                        collection_name=CHROMA_COLLECTION_EXTERNAL
                    )
                    if result["status"] == "success":
                        total_ingested += result["chunks"]
                        results.append({
                            "source": source["name"],
                            "status": "success",
                            "chunks": result["chunks"]
                        })
                    else:
                        results.append({"source": source["name"], "status": "error"})
            time.sleep(2)  # Be polite to servers
        except Exception as e:
            logger.error(f"Error scraping {source['name']}: {e}")
            results.append({"source": source["name"], "status": "error", "error": str(e)})

    return {"results": results, "total_chunks_ingested": total_ingested}


if __name__ == "__main__":
    summary = run_web_scraping()
    print(summary)
