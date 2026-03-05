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

# Source URLs (embedded) - Full list (9 per ETF = 18 total)
SOURCES = {
    "LU3098954871": [
        # ISIN-based URLs
        "https://www.justetf.com/de/etf-profile.html?isin=LU3098954871",
        "https://extraetf.com/de/etf-profile/LU3098954871",
        "https://www.finanzfluss.de/informer/etf/lu3098954871/",
        "https://www.comdirect.de/inf/etfs/LU3098954871",
        "https://www.avl-investmentfonds.de/fonds/details/LU3098954871",
        # Hardcoded URLs (slug-based)
        "https://www.finanzen.net/etf/teq-general-artificial-intelligence-etf-r-lu3098954871",
        "https://www.onvista.de/etf/TEQ-General-Artificial-Intelligence-EUR-UCITS-ETF-Acc-ETF-LU3098954871",
        "https://de.finance.yahoo.com/quote/TGAI.DE/",
        "https://live.deutsche-boerse.com/etf/teq-general-artificial-intelligence-eur-ucits-etf-acc"
    ],
    "LU3075459852": [
        # ISIN-based URLs
        "https://www.justetf.com/de/etf-profile.html?isin=LU3075459852",
        "https://extraetf.com/de/etf-profile/LU3075459852",
        "https://www.finanzfluss.de/informer/etf/lu3075459852/",
        "https://www.comdirect.de/inf/etfs/LU3075459852",
        "https://www.avl-investmentfonds.de/fonds/details/LU3075459852",
        # Hardcoded URLs (slug-based)
        "https://www.finanzen.net/etf/inyova-impact-investing-active-equity-fund-etf-lu3075459852",
        "https://www.onvista.de/etf/INY-I-IM-IN-ACT-EQ-EXCH-TRADED-ACT-NOM-EUR-ACC-ON-ETF-LU3075459852",
        "https://de.finance.yahoo.com/quote/INY0.DE/",
        "https://live.deutsche-boerse.com/etf/inyova-impact-investing-active-equity-fund-ucits-etf-eur"
    ]
}


def fetch_url(url, timeout=4):
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

    # Truncate HTML if too long (keep first 30000 chars - focus on main content)
    if len(html) > 30000:
        html = html[:30000]

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
    # Fetch HTML
    html = fetch_url(url, timeout=4)

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
    else:
        # Use agent to extract and compare
        agent_result = extract_with_agent(
            html,
            url,
            ref['name'],
            ref['ter']
        )

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

            # Collect all URLs to check
            tasks = []
            for isin, urls in SOURCES.items():
                ref = REFERENCE_DATA[isin]
                # Check all URLs (9 per ETF = 18 total)
                for url in urls:
                    tasks.append((isin, url, ref))

            # Process URLs in parallel (max 10 workers for 18 URLs)
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
                'note': 'Agentic workflow (parallel) - intelligent extraction with Claude Haiku'
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
