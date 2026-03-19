"""
Web Scraper for Secondary Learning
Fetches public circulars from RBI, NABARD, SEBI websites with resilient retry logic.
"""

import logging
import time
from typing import Optional, Dict, Any
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from document_processor import ingest_text
from config import SCRAPE_SOURCES, CHROMA_COLLECTION_EXTERNAL

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}
TIMEOUT = 30
MAX_RETRIES = 3


def get_session_with_retries() -> requests.Session:
    """Create a requests session with automatic retry logic and exponential backoff."""
    session = requests.Session()
    retry_strategy = Retry(
        total=MAX_RETRIES,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"]
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


def fetch_page(url: str) -> Optional[str]:
    """
    Fetch a webpage with retries and return its text content.
    Returns None if all retries fail.
    """
    try:
        session = get_session_with_retries()
        logger.info(f"Fetching: {url}")
        
        resp = session.get(url, headers=HEADERS, timeout=TIMEOUT)
        resp.raise_for_status()
        
        soup = BeautifulSoup(resp.content, "html.parser")

        # Remove scripts, styles, nav, footer, and other non-content elements
        for tag in soup(["script", "style", "nav", "footer", "header", "noscript", "form"]):
            tag.decompose()

        # Get main content from semantic HTML5 tags first, fallback to body
        main = soup.find("main") or soup.find("article") or soup.find("div", {"id": "content"}) or soup.body
        if main:
            text = main.get_text(separator="\n", strip=True)
        else:
            text = soup.get_text(separator="\n", strip=True)
        
        # Clean up excessive whitespace and empty lines
        text = "\n".join(line.strip() for line in text.split("\n") if line.strip())
        
        # Ensure we got meaningful content
        if len(text) < 50:
            logger.warning(f"Fetched content is too short ({len(text)} chars), might be empty or blocked")
            return None
        
        logger.info(f"Successfully fetched {len(text)} characters from {url}")
        return text
        
    except requests.exceptions.Timeout:
        logger.error(f"Timeout (>30s) fetching {url} - server may be slow or unresponsive")
        return None
    except requests.exceptions.ConnectionError:
        logger.error(f"Connection error fetching {url} - network or DNS issue")
        return None
    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP error {e.response.status_code} fetching {url}")
        return None
    except Exception as e:
        logger.error(f"Failed to fetch {url}: {type(e).__name__}: {e}")
        return None


def run_web_scraping(test_mode: bool = False) -> Dict[str, Any]:
    """
    Fetch and ingest content from RBI, NABARD, SEBI websites with error resilience.
    
    Args:
        test_mode: If True, only fetch summaries without storing to DB
    
    Returns:
        dict with success/failure status and statistics
    """
    stats = {
        "total_sources": 0,
        "successful_sources": 0,
        "failed_sources": 0,
        "total_chars_ingested": 0,
        "results": [],
        "errors": [],
        "timestamp": datetime.now().isoformat()
    }
    
    if not SCRAPE_SOURCES:
        logger.warning("No scrape sources configured in config.py")
        stats["errors"].append("No SCRAPE_SOURCES configured")
        return stats
    
    logger.info(f"Starting web scraping from {len(SCRAPE_SOURCES)} sources...")
    
    for source in SCRAPE_SOURCES:
        stats["total_sources"] += 1
        source_name = source.get("name", "Unknown")
        source_url = source.get("url")
        
        if not source_url:
            msg = f"{source_name}: No URL configured"
            logger.warning(msg)
            stats["errors"].append(msg)
            stats["failed_sources"] += 1
            continue
        
        try:
            # Fetch the main page
            content = fetch_page(source_url)
            
            if not content:
                msg = f"{source_name}: Failed to fetch page (may be network issue, firewall, or site blocked)"
                logger.warning(msg)
                stats["errors"].append(msg)
                stats["failed_sources"] += 1
                continue
            
            # Create a meaningful document title with metadata
            doc_title = f"{source_name} - Main Page ({datetime.now().strftime('%Y-%m-%d %H:%M')})"
            
            logger.info(f"Successfully fetched {len(content)} chars from {source_name} - {'[TEST MODE]' if test_mode else 'ingesting...'}")
            
            if test_mode:
                logger.info(f"[TEST MODE] Would ingest {len(content)} characters from {source_name}")
                stats["total_chars_ingested"] += len(content)
                stats["results"].append({
                    "source": source_name,
                    "status": "success",
                    "chars_fetched": len(content),
                    "mode": "test"
                })
            else:
                try:
                    # Prepare metadata
                    metadata = {
                        "source": source_name,
                        "source_url": source_url,
                        "fetch_date": datetime.now().isoformat(),
                        "type": "web_scrape"
                    }
                    
                    # Ingest the content
                    result = ingest_text(
                        text=content,
                        doc_name=doc_title,
                        metadata=metadata,
                        collection_name=CHROMA_COLLECTION_EXTERNAL
                    )
                    
                    stats["total_chars_ingested"] += len(content)
                    stats["successful_sources"] += 1
                    
                    logger.info(f"✓ Successfully ingested {len(content)} chars from {source_name}")
                    stats["results"].append({
                        "source": source_name,
                        "status": "success",
                        "chars_ingested": len(content),
                        "url": source_url
                    })
                    
                except Exception as ingest_err:
                    msg = f"{source_name}: Ingestion failed - {type(ingest_err).__name__}: {str(ingest_err)}"
                    logger.error(msg)
                    stats["errors"].append(msg)
                    stats["failed_sources"] += 1
                    stats["results"].append({
                        "source": source_name,
                        "status": "ingest_error",
                        "error": str(ingest_err)
                    })
            
            # Be respectful to servers - add delay between requests
            time.sleep(2)
            
        except Exception as e:
            msg = f"{source_name}: Unexpected error - {type(e).__name__}: {str(e)}"
            logger.error(msg)
            stats["errors"].append(msg)
            stats["failed_sources"] += 1
            stats["results"].append({
                "source": source_name,
                "status": "error",
                "error": str(e)
            })
            continue
    
    # Summary logging
    logger.info(f"\n{'='*60}")
    logger.info(f"Web Scraping Summary:")
    logger.info(f"  Total sources: {stats['total_sources']}")
    logger.info(f"  Successful: {stats['successful_sources']}")
    logger.info(f"  Failed: {stats['failed_sources']}")
    logger.info(f"  Total chars ingested: {stats['total_chars_ingested']}")
    if stats["errors"]:
        logger.warning(f"  Errors encountered: {len(stats['errors'])}")
        for error in stats["errors"][:3]:  # Show first 3 errors
            logger.warning(f"    - {error}")
    logger.info(f"{'='*60}\n")
    
    return stats


if __name__ == "__main__":
    # Test the scraper
    summary = run_web_scraping(test_mode=False)
    print(summary)
