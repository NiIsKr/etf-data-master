"""
Fetch URLs and extract ETF name and TER using heuristics.
"""
import re
import logging
import time
from typing import Optional, Tuple, Dict
import requests
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def fetch_url(url: str, timeout: int = 10) -> Optional[str]:
    """
    Fetch HTML from URL with retries.
    Returns HTML string or None on failure.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; ETF-Monitor/1.0)",
        "Accept-Language": "de-DE,de;q=0.9,en;q=0.8"
    }

    try:
        response = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)
        response.raise_for_status()
        return response.text
    except requests.exceptions.Timeout:
        logger.error(f"Timeout fetching {url}")
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching {url}: {e}")
        return None


def extract_name_from_html(html: str, url: str) -> Tuple[Optional[str], str]:
    """
    Extract ETF name from HTML using multiple strategies.
    Returns (name, source) where source is the extraction method used.
    """
    soup = BeautifulSoup(html, 'html.parser')

    # Strategy 1: og:title meta tag
    og_title = soup.find('meta', property='og:title')
    if og_title and og_title.get('content'):
        name = og_title['content'].strip()
        if len(name) > 5:
            return name, "og:title"

    # Strategy 2: JSON-LD structured data
    json_ld = soup.find('script', type='application/ld+json')
    if json_ld:
        try:
            import json
            data = json.loads(json_ld.string)
            if isinstance(data, dict) and data.get('@type') in ['FinancialProduct', 'Product']:
                name = data.get('name')
                if name:
                    return name.strip(), "json-ld"
        except:
            pass

    # Strategy 3: h1 tag
    h1 = soup.find('h1')
    if h1:
        name = h1.get_text().strip()
        if len(name) > 5:
            return name, "h1"

    # Strategy 4: title tag
    title = soup.find('title')
    if title:
        name = title.get_text().strip()
        # Clean common title suffixes
        name = re.sub(r'\s*[|\-]\s*(JustETF|ExtraETF|Finanzen\.net|OnVista|Yahoo Finance|comdirect).*$', '', name, flags=re.IGNORECASE)
        if len(name) > 5:
            return name, "title"

    return None, "unknown"


def extract_ter_from_html(html: str, url: str) -> Tuple[Optional[float], str]:
    """
    Extract TER from HTML using keyword search and regex.
    Returns (ter_value, evidence_string) where evidence is context around the match.
    """
    # Keywords that indicate TER
    keywords = [
        "TER", "Total Expense Ratio", "Gesamtkostenquote",
        "laufende Kosten", "Kostenquote", "Ongoing Charges",
        "Verwaltungsgebühr", "Management Fee", "bps", "basis points"
    ]

    # Convert to lowercase for case-insensitive search
    text_lower = html.lower()

    for keyword in keywords:
        keyword_lower = keyword.lower()
        pos = text_lower.find(keyword_lower)

        if pos == -1:
            continue

        # Extract context around keyword (50 chars before, 150 chars after)
        context_start = max(0, pos - 50)
        context_end = min(len(html), pos + 150)
        context = html[context_start:context_end]

        # Look for percentage pattern in context
        # Matches: 0.95%, 0,95%, 0.95 %, 95 bps, 0.69%
        ter_pattern = r'(\d+(?:[.,]\d{1,4})?)\s*(?:%|bps)?'
        matches = re.findall(ter_pattern, context, re.IGNORECASE)

        if matches:
            # Try all matches, not just the first (some might fail sanity check)
            for ter_str in matches:
                ter_str = ter_str.replace(',', '.')
                try:
                    ter_value = float(ter_str)

                    # Handle bps (basis points) if present
                    if 'bps' in context.lower() or 'basis points' in context.lower():
                        # For bps, values are typically large numbers (e.g., 95 bps = 0.95%)
                        if ter_value > 5.0:
                            ter_value = ter_value / 100

                    # Sanity check (TER should be between 0.01% and 5%)
                    if 0.01 <= ter_value <= 5.0:
                        # Create evidence string (80-120 chars around match)
                        evidence_start = max(0, pos - 40)
                        evidence_end = min(len(html), pos + 80)
                        evidence = html[evidence_start:evidence_end]
                        # Clean up HTML tags and whitespace
                        evidence = re.sub(r'<[^>]+>', '', evidence)
                        evidence = re.sub(r'\s+', ' ', evidence).strip()
                        evidence = evidence[:120]  # Limit length

                        return ter_value, evidence
                except ValueError:
                    continue

    return None, ""


def extract_from_url(
    url: str,
    timeout: int = 10,
    sleep_ms: int = 250
) -> Dict:
    """
    Fetch URL and extract name + TER.
    Returns dict with keys: url, name, name_source, ter, ter_evidence, error
    """
    result = {
        "url": url,
        "name": None,
        "name_source": "unknown",
        "ter": None,
        "ter_evidence": "",
        "error": None
    }

    # Fetch HTML
    html = fetch_url(url, timeout)
    if html is None:
        result["error"] = f"Failed to fetch URL (timeout or HTTP error)"
        return result

    # Extract name
    name, name_source = extract_name_from_html(html, url)
    result["name"] = name
    result["name_source"] = name_source

    # Extract TER
    ter, ter_evidence = extract_ter_from_html(html, url)
    result["ter"] = ter
    result["ter_evidence"] = ter_evidence

    # Sleep between requests (rate limiting)
    if sleep_ms > 0:
        time.sleep(sleep_ms / 1000)

    return result


if __name__ == "__main__":
    # Simple test
    import sys
    if len(sys.argv) < 2:
        print("Usage: python -m src.extract_web <url>")
        sys.exit(1)

    url = sys.argv[1]
    result = extract_from_url(url)

    print(f"URL: {result['url']}")
    print(f"Name: {result['name']} (source: {result['name_source']})")
    print(f"TER: {result['ter']}")
    if result['ter_evidence']:
        print(f"Evidence: {result['ter_evidence']}")
    if result['error']:
        print(f"Error: {result['error']}")
