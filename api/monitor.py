"""
Vercel Serverless Function for ETF Monitoring
Standalone version - no external imports needed
"""
import json
import re
from http.server import BaseHTTPRequestHandler
import requests
from bs4 import BeautifulSoup

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

# Source URLs (embedded) - All 9 per ETF
SOURCES = {
    "LU3098954871": [
        "https://www.justetf.com/de/etf-profile.html?isin=LU3098954871",
        "https://extraetf.com/de/etf-profile/LU3098954871",
        "https://www.finanzfluss.de/informer/etf/lu3098954871/",
        "https://www.comdirect.de/inf/etfs/LU3098954871",
        "https://www.avl-investmentfonds.de/fonds/details/LU3098954871",
        "https://www.finanzen.net/etf/teq-general-artificial-intelligence-etf-r-lu3098954871",
        "https://www.onvista.de/etf/TEQ-General-Artificial-Intelligence-EUR-UCITS-ETF-Acc-ETF-LU3098954871",
        "https://de.finance.yahoo.com/quote/TGAI.DE/",
        "https://live.deutsche-boerse.com/etf/teq-general-artificial-intelligence-eur-ucits-etf-acc"
    ],
    "LU3075459852": [
        "https://www.justetf.com/de/etf-profile.html?isin=LU3075459852",
        "https://extraetf.com/de/etf-profile/LU3075459852",
        "https://www.finanzfluss.de/informer/etf/lu3075459852/",
        "https://www.comdirect.de/inf/etfs/LU3075459852",
        "https://www.avl-investmentfonds.de/fonds/details/LU3075459852",
        "https://www.finanzen.net/etf/inyova-impact-investing-active-equity-fund-etf-lu3075459852",
        "https://www.onvista.de/etf/INY-I-IM-IN-ACT-EQ-EXCH-TRADED-ACT-NOM-EUR-ACC-ON-ETF-LU3075459852",
        "https://de.finance.yahoo.com/quote/INY0.DE/",
        "https://live.deutsche-boerse.com/etf/inyova-impact-investing-active-equity-fund-ucits-etf-eur"
    ]
}


def fetch_url(url, timeout=5):
    """Fetch HTML from URL"""
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; ETF-Monitor/1.0)",
        "Accept-Language": "de-DE,de;q=0.9,en;q=0.8"
    }
    try:
        response = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)
        response.raise_for_status()
        return response.text
    except Exception:
        return None


def extract_name_from_html(html, url):
    """Extract ETF name from HTML"""
    soup = BeautifulSoup(html, 'html.parser')

    # Try og:title
    og_title = soup.find('meta', property='og:title')
    if og_title and og_title.get('content'):
        name = og_title['content'].strip()
        # Clean up: Remove ISIN/WKN suffixes (e.g., "| A41AXG | LU3098954871")
        name = re.split(r'\s*[|\-]\s*(?:[A-Z0-9]{6,}|LU\d+)', name)[0].strip()
        if len(name) > 5:
            return name, "og:title"

    # Try h1
    h1 = soup.find('h1')
    if h1:
        name = h1.get_text().strip()
        # Clean up
        name = re.split(r'\s*[|\-]\s*(?:[A-Z0-9]{6,}|LU\d+)', name)[0].strip()
        if len(name) > 5:
            return name, "h1"

    # Try title
    title = soup.find('title')
    if title:
        name = title.get_text().strip()
        # Clean up common title suffixes
        name = re.sub(r'\s*[|\-]\s*(JustETF|ExtraETF|Finanzen\.net|OnVista|Yahoo Finance|comdirect).*$', '', name, flags=re.IGNORECASE)
        name = re.split(r'\s*[|\-]\s*(?:[A-Z0-9]{6,}|LU\d+)', name)[0].strip()
        if len(name) > 5:
            return name, "title"

    return None, "unknown"


def extract_ter_from_html(html, url):
    """Extract TER from HTML"""
    keywords = ["TER", "Total Expense Ratio", "Gesamtkostenquote",
                "laufende Kosten", "Kostenquote"]

    text_lower = html.lower()

    for keyword in keywords:
        pos = text_lower.find(keyword.lower())
        if pos == -1:
            continue

        context_start = max(0, pos - 50)
        context_end = min(len(html), pos + 150)
        context = html[context_start:context_end]

        ter_pattern = r'(\d+(?:[.,]\d{1,4})?)\s*%'
        matches = re.findall(ter_pattern, context, re.IGNORECASE)

        if matches:
            for ter_str in matches:
                ter_str = ter_str.replace(',', '.')
                try:
                    ter_value = float(ter_str)
                    if 0.01 <= ter_value <= 5.0:
                        evidence = context[max(0, pos-40):min(len(context), pos+80)]
                        evidence = re.sub(r'<[^>]+>', '', evidence)
                        evidence = re.sub(r'\s+', ' ', evidence).strip()[:120]
                        return ter_value, evidence
                except ValueError:
                    continue

    return None, ""


def normalize_name(name):
    """Normalize name for comparison"""
    return ' '.join(name.strip().split())


def names_match(name1, name2):
    """Check if names match"""
    return normalize_name(name1) == normalize_name(name2)


def ters_match(ter1, ter2):
    """Check if TERs match"""
    return round(ter1, 4) == round(ter2, 4)


def compare_result(result, ref_name, ref_ter):
    """Compare extraction result with reference"""
    if result.get('error'):
        return 'FETCH_ERROR'

    name = result.get('name')
    ter = result.get('ter')

    if name is None:
        return 'FETCH_ERROR'

    if ter is None:
        return 'TER_MISSING'

    name_ok = names_match(name, ref_name)
    ter_ok = ters_match(ter, ref_ter)

    if name_ok and ter_ok:
        return 'MATCH'
    elif not name_ok and not ter_ok:
        return 'BOTH_MISMATCH'
    elif not name_ok:
        return 'NAME_MISMATCH'
    else:
        return 'TER_MISMATCH'


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        """Handle POST request to start monitoring"""
        try:
            results = []

            # Check each ISIN
            for isin, urls in SOURCES.items():
                ref = REFERENCE_DATA[isin]

                for url in urls:
                    result = {
                        'isin': isin,
                        'url': url,
                        'name': None,
                        'name_source': 'unknown',
                        'ter': None,
                        'ter_evidence': '',
                        'error': None
                    }

                    # Fetch HTML
                    html = fetch_url(url, timeout=3)
                    if html is None:
                        result['error'] = 'Failed to fetch URL'
                    else:
                        # Extract name
                        name, name_source = extract_name_from_html(html, url)
                        result['name'] = name
                        result['name_source'] = name_source

                        # Extract TER
                        ter, ter_evidence = extract_ter_from_html(html, url)
                        result['ter'] = ter
                        result['ter_evidence'] = ter_evidence

                    # Compare with reference
                    status = compare_result(result, ref['name'], ref['ter'])
                    result['status'] = status

                    results.append(result)

            # Prepare response
            response_data = {
                'success': True,
                'results': results,
                'reference': REFERENCE_DATA,
                'note': 'Checking 18 URLs (9 per ETF)'
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
