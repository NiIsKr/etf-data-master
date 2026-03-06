"""
Vercel Serverless Function for ETF Monitoring
Agentic Workflow with Claude Haiku + Parallel Processing
"""
import json
import os
from http.server import BaseHTTPRequestHandler
import requests
from anthropic import Anthropic
from concurrent.futures import ThreadPoolExecutor, as_completed

# Create reusable session with connection pooling
_session = None

def get_session():
    """Get or create reusable requests session"""
    global _session
    if _session is None:
        _session = requests.Session()

        # Connection pooling (reuse TCP connections)
        from requests.adapters import HTTPAdapter
        adapter = HTTPAdapter(
            pool_connections=10,  # Match ThreadPoolExecutor workers
            pool_maxsize=20
        )
        _session.mount('http://', adapter)
        _session.mount('https://', adapter)

    return _session

# Reference data (embedded)
REFERENCE_DATA = {
    "LU3098954871": {
        "name": "TEQ - General Artificial Intelligence R EUR UCITS ETF (Acc)",
        "ter": 0.69
    },
    "LU3075459852": {
        "name": "Inyova Impact Investing Active Equity Fund UCITS ETF EUR",
        "ter": 0.95
    }
}

# Source URLs (embedded) - Full list (9 per ETF = 18 total, split across 2 requests)
SOURCES = {
    "LU3098954871": [
        # ISIN-based URLs (5)
        "https://www.justetf.com/de/etf-profile.html?isin=LU3098954871",
        "https://extraetf.com/de/etf-profile/LU3098954871",
        "https://www.finanzfluss.de/informer/etf/lu3098954871/",
        "https://www.comdirect.de/inf/etfs/LU3098954871",
        "https://www.avl-investmentfonds.de/fonds/details/LU3098954871",
        # Hardcoded URLs (4)
        "https://www.finanzen.net/etf/teq-general-artificial-intelligence-etf-r-lu3098954871",
        "https://www.onvista.de/etf/TEQ-General-Artificial-Intelligence-EUR-UCITS-ETF-Acc-ETF-LU3098954871",
        "https://de.finance.yahoo.com/quote/TGAI.DE/",
        "https://live.deutsche-boerse.com/etf/teq-general-artificial-intelligence-eur-ucits-etf-acc"
    ],
    "LU3075459852": [
        # ISIN-based URLs (5)
        "https://www.justetf.com/de/etf-profile.html?isin=LU3075459852",
        "https://extraetf.com/de/etf-profile/LU3075459852",
        "https://www.finanzfluss.de/informer/etf/lu3075459852/",
        "https://www.comdirect.de/inf/etfs/LU3075459852",
        "https://www.avl-investmentfonds.de/fonds/details/LU3075459852",
        # Hardcoded URLs (4)
        "https://www.finanzen.net/etf/inyova-impact-investing-active-equity-fund-etf-lu3075459852",
        "https://www.onvista.de/etf/INY-I-IM-IN-ACT-EQ-EXCH-TRADED-ACT-NOM-EUR-ACC-ON-ETF-LU3075459852",
        "https://de.finance.yahoo.com/quote/INY0.DE/",
        "https://live.deutsche-boerse.com/etf/inyova-impact-investing-active-equity-fund-ucits-etf-eur"
    ]
}

# Domain-specific timeout configuration
TIMEOUT_CONFIG = {
    # Fast German sites (< 3s typical)
    "justetf.com": 6,
    "extraetf.com": 6,
    "comdirect.de": 6,
    "onvista.de": 6,
    "deutsche-boerse.com": 6,

    # Medium speed sites (3-5s)
    "finanzfluss.de": 8,
    "avl-investmentfonds.de": 8,

    # Slow international sites (5-8s) - THE FIX!
    "finanzen.net": 10,
    "finance.yahoo.com": 10,

    # Default for unknown
    "default": 8
}

def get_timeout_for_url(url):
    """Get appropriate timeout based on domain"""
    from urllib.parse import urlparse
    domain = urlparse(url).netloc

    for known_domain, timeout in TIMEOUT_CONFIG.items():
        if known_domain in domain:
            return timeout

    return TIMEOUT_CONFIG["default"]


def fetch_url(url, timeout=None):
    """Fetch HTML from URL with smart timeout"""
    # Use domain-specific timeout if not provided
    if timeout is None:
        timeout = get_timeout_for_url(url)

    headers = {
        # Chrome 130 User-Agent (most common browser 2026)
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",

        # Standard HTML acceptance
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",

        # Enable compression (70% faster transfer!)
        "Accept-Encoding": "gzip, deflate, br",

        # Language preferences
        "Accept-Language": "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7",

        # Appear to come from Google (some sites whitelist Google)
        "Referer": "https://www.google.com/",

        # Modern browser security headers
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "cross-site",
        "Upgrade-Insecure-Requests": "1"
    }

    try:
        session = get_session()  # Use pooled connection
        response = session.get(url, headers=headers, timeout=timeout, allow_redirects=True)
        response.raise_for_status()
        return response.text
    except Exception:
        return None


def extract_with_heuristics(html, reference_name, reference_ter):
    """
    Fast heuristic extraction using regex (no LLM).
    Returns extracted name and TER, or None if not found.
    """
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, 'html.parser')

    # Extract name (priority order)
    name = None

    # Try og:title
    og_title = soup.find('meta', property='og:title')
    if og_title and og_title.get('content'):
        name = og_title['content'].strip()

    # Try h1
    if not name:
        h1 = soup.find('h1')
        if h1:
            name = h1.get_text().strip()

    # Try title
    if not name:
        title = soup.find('title')
        if title:
            name = title.get_text().strip()

    # Extract TER
    ter = None
    import re

    text = soup.get_text()
    ter_keywords = ['TER', 'Total Expense Ratio', 'Gesamtkostenquote', 'laufende Kosten', 'Kostenquote']

    for keyword in ter_keywords:
        if keyword.lower() in text.lower():
            # Find percentage near keyword
            idx = text.lower().find(keyword.lower())
            context = text[max(0, idx-50):idx+100]

            # Match percentage: 0.69% or 0,69% or 69 bps
            match = re.search(r'(\d+[.,]\d{1,4})\s*(?:%|bps)?', context)
            if match:
                ter_str = match.group(1).replace(',', '.')
                ter_value = float(ter_str)

                # Convert bps to percentage if needed
                if 'bps' in context.lower():
                    ter_value = ter_value / 100

                ter = ter_value
                break

    return name, ter


def extract_with_agent(html, url, reference_name, reference_ter):
    """
    Use Claude Haiku to intelligently extract and compare ETF data.
    Returns structured result with match status and explanation.
    """
    # Get API key from environment
    api_key = os.environ.get('ANTHROPIC_API_KEY')
    if not api_key:
        return {
            'extracted_name': None,
            'extracted_ter': None,
            'name_match': False,
            'ter_match': False,
            'status': 'FETCH_ERROR',
            'explanation': 'ANTHROPIC_API_KEY not configured'
        }

    # Truncate HTML if too long (keep first 5000 chars to reduce tokens - aggressive!)
    if len(html) > 5000:
        html = html[:5000]

    prompt = f"""Du bist ein ETF-Daten-Extractor. Analysiere diese Website und vergleiche die Daten mit den Referenzwerten.

**Referenzdaten (Soll-Werte):**
- Name: "{reference_name}"
- TER: {reference_ter}%

**Deine Aufgabe:**
1. Finde den ETF-Namen auf der Website (meist in Title, H1, oder Meta-Tags)
2. Finde die TER (Total Expense Ratio / laufende Kosten / Gesamtkostenquote)
   - Kann als "0.69%", "0,69%", "69 bps", oder ähnlich dargestellt sein
   - 100 bps = 1%
3. Vergleiche die gefundenen Werte mit den Referenzdaten

**Wichtige Matching-Regeln:**
- **Name:** Kleine Abweichungen sind OK:
  - "R EUR" kann fehlen (optional)
  - "(Acc)" oder "(Thes)" kann fehlen (optional)
  - ISIN/WKN am Ende ignorieren (z.B. "| LU123456")
  - Reihenfolge kann leicht variieren
  - Aber: Hauptbestandteile müssen übereinstimmen (z.B. "General Artificial Intelligence")

- **TER:** Numerisch gleich wenn auf 2 Dezimalstellen gerundet gleich:
  - 0.69% = 0,69% = 69 bps = 0.690%
  - Aber: 0.69% ≠ 0.70%

**Antwortformat (NUR JSON, keine Erklärung außerhalb):**
```json
{{
  "extracted_name": "Der gefundene ETF-Name (oder null wenn nicht gefunden)",
  "extracted_ter": 0.69 (nur die Zahl, oder null wenn nicht gefunden),
  "name_match": true/false,
  "ter_match": true/false,
  "explanation": "Kurze Erklärung was gefunden wurde und ob es matched"
}}
```

**Website HTML:**
{html}

Analysiere jetzt und gib NUR das JSON zurück."""

    try:
        client = Anthropic(api_key=api_key)
        response = client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=500,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        # Parse response
        content = response.content[0].text

        # Extract JSON from response (may be wrapped in markdown)
        import re
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group(0))

            # Determine status based on matches
            if data.get('name_match') and data.get('ter_match'):
                status = 'MATCH'
            elif not data.get('name_match') and not data.get('ter_match'):
                status = 'BOTH_MISMATCH'
            elif not data.get('name_match'):
                status = 'NAME_MISMATCH'
            elif not data.get('ter_match'):
                if data.get('extracted_ter') is None:
                    status = 'TER_MISSING'
                else:
                    status = 'TER_MISMATCH'
            else:
                status = 'TER_MISSING'

            data['status'] = status
            return data
        else:
            return {
                'extracted_name': None,
                'extracted_ter': None,
                'name_match': False,
                'ter_match': False,
                'status': 'FETCH_ERROR',
                'explanation': 'Failed to parse agent response'
            }

    except Exception as e:
        return {
            'extracted_name': None,
            'extracted_ter': None,
            'name_match': False,
            'ter_match': False,
            'status': 'FETCH_ERROR',
            'explanation': f'Agent error: {str(e)}'
        }


def process_single_url(isin, url, ref):
    """Process a single URL (used for parallel processing)"""
    import time

    # Fetch HTML (uses smart timeout: 6-10s depending on domain)
    html = fetch_url(url)

    if html is None:
        # Failed to fetch
        return {
            'isin': isin,
            'url': url,
            'name': None,
            'ter': None,
            'status': 'FETCH_ERROR',
            'explanation': 'Failed to fetch URL',
            'error': 'Failed to fetch URL (timeout or HTTP error)'
        }

    # Always use agent (intelligent extraction + comparison)
    agent_result = extract_with_agent(
        html,
        url,
        ref['name'],
        ref['ter']
    )

    # Small delay to avoid rate limiting (distributed over time)
    time.sleep(0.15)  # 150ms delay between agent calls

    return {
        'isin': isin,
        'url': url,
        'name': agent_result.get('extracted_name'),
        'ter': agent_result.get('extracted_ter'),
        'status': agent_result.get('status'),
        'explanation': agent_result.get('explanation'),
        'error': None if agent_result.get('status') != 'FETCH_ERROR' else agent_result.get('explanation')
    }


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        """Handle POST request to start monitoring"""
        try:
            results = []

            # Collect all URLs to check (18 total)
            tasks = []
            for isin, urls in SOURCES.items():
                ref = REFERENCE_DATA[isin]
                # Check all URLs for this ISIN (9 URLs per ETF = 18 total)
                for url in urls:
                    tasks.append((isin, url, ref))

            # Process URLs in parallel (max 10 workers, handles 18 URLs in ~57s)
            with ThreadPoolExecutor(max_workers=10) as executor:
                futures = [executor.submit(process_single_url, isin, url, ref) for isin, url, ref in tasks]

                for future in as_completed(futures):
                    try:
                        result = future.result()
                        results.append(result)
                    except Exception as e:
                        # Handle individual task failure
                        results.append({
                            'isin': 'unknown',
                            'url': 'unknown',
                            'name': None,
                            'ter': None,
                            'status': 'FETCH_ERROR',
                            'explanation': f'Task failed: {str(e)}',
                            'error': str(e)
                        })

            # Prepare response
            response_data = {
                'success': True,
                'results': results,
                'reference': REFERENCE_DATA,
                'note': 'Agent-only workflow (18 parallel calls) - intelligent extraction & comparison with Claude Haiku'
            }

            # Send response
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(response_data).encode('utf-8'))

        except Exception as e:
            # Error response
            error_response = {
                'success': False,
                'error': str(e)
            }

            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(error_response).encode('utf-8'))

    def do_OPTIONS(self):
        """Handle CORS preflight"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
