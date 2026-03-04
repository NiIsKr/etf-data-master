"""
Optional DuckDuckGo HTML search augmentation for source discovery.
"""
import json
import os
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import requests
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def search_duckduckgo(query: str, max_results: int = 5) -> List[str]:
    """
    Search DuckDuckGo HTML and extract result URLs.
    Returns list of URLs (may be empty if search fails).
    """
    search_url = "https://html.duckduckgo.com/html/"
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; ETF-Monitor/1.0)"
    }

    try:
        response = requests.post(
            search_url,
            data={"q": query},
            headers=headers,
            timeout=10
        )
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')
        urls = []

        # Extract URLs from search results
        for result in soup.find_all('a', class_='result__url'):
            url = result.get('href')
            if url and url.startswith('http'):
                urls.append(url)
                if len(urls) >= max_results:
                    break

        logger.info(f"Found {len(urls)} URLs from DuckDuckGo for query: {query}")
        return urls

    except Exception as e:
        logger.error(f"DuckDuckGo search failed: {e}")
        return []


def load_search_cache(cache_path: str = "outputs/search_cache.json") -> Dict:
    """Load cached search results."""
    if not os.path.exists(cache_path):
        return {}

    try:
        with open(cache_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load search cache: {e}")
        return {}


def save_search_cache(cache: Dict, cache_path: str = "outputs/search_cache.json"):
    """Save search results to cache."""
    output_dir = os.path.dirname(cache_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    with open(cache_path, 'w', encoding='utf-8') as f:
        json.dump(cache, f, indent=2, ensure_ascii=False)


def augment_sources(
    sources: Dict,
    isins: List[str],
    etf_names: Dict[str, str],
    max_results: int = 5,
    ttl_days: int = 14,
    cache_path: str = "outputs/search_cache.json"
) -> Dict:
    """
    Augment sources with DuckDuckGo search results.
    Uses cache with TTL to avoid repeated searches.

    Args:
        sources: Existing sources dict from curated_sources.py
        isins: List of ISINs to search for
        etf_names: Dict mapping ISIN to ETF name (for search query)
        max_results: Max additional URLs per ISIN
        ttl_days: Cache TTL in days
        cache_path: Path to cache file

    Returns:
        Updated sources dict
    """
    cache = load_search_cache(cache_path)
    now = datetime.utcnow()
    ttl = timedelta(days=ttl_days)

    for isin in isins:
        # Check cache
        cache_key = isin
        if cache_key in cache:
            cached_data = cache[cache_key]
            cached_time = datetime.fromisoformat(cached_data['timestamp'].replace('Z', ''))

            if now - cached_time < ttl:
                logger.info(f"Using cached search results for {isin} (age: {(now - cached_time).days} days)")
                search_urls = cached_data['urls']
            else:
                logger.info(f"Cache expired for {isin}, performing new search")
                search_urls = None
        else:
            search_urls = None

        # Perform search if not cached
        if search_urls is None:
            etf_name = etf_names.get(isin, "")
            query = f"{isin} {etf_name} ETF"
            logger.info(f"Searching DuckDuckGo: {query}")

            search_urls = search_duckduckgo(query, max_results)

            # Update cache
            cache[cache_key] = {
                "timestamp": now.isoformat() + "Z",
                "query": query,
                "urls": search_urls
            }
            save_search_cache(cache, cache_path)

            # Rate limiting
            time.sleep(1)

        # Add search results to sources (avoid duplicates)
        if isin in sources:
            existing_urls = set(sources[isin]['urls'])
            new_urls = [url for url in search_urls if url not in existing_urls]
            sources[isin]['urls'].extend(new_urls)
            logger.info(f"Added {len(new_urls)} new URLs from search for {isin}")

    return sources


if __name__ == "__main__":
    # Simple test
    query = "LU3098954871 TEQ ETF"
    urls = search_duckduckgo(query, 5)
    print(f"Found {len(urls)} URLs:")
    for url in urls:
        print(f"  - {url}")
