"""
Vercel Serverless Function for ETF Monitoring
"""
import json
import sys
import os
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs

# Add parent directory to path to import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src import reference, curated_sources, extract_web, monitor

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        """Handle POST request to start monitoring"""
        try:
            # Parse request body
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length).decode('utf-8')

            try:
                data = json.loads(body) if body else {}
            except json.JSONDecodeError:
                data = {}

            slack_webhook = data.get('slack_webhook', '')

            # Set Slack webhook in environment if provided
            if slack_webhook:
                os.environ['SLACK_WEBHOOK_URL'] = slack_webhook

            # Load reference data (use cached or generate)
            ref_data = load_or_generate_reference()

            # Load sources (use cached or generate)
            sources_data = load_or_generate_sources()

            # Due to Vercel timeout limits (10s on Hobby), we'll check a subset of URLs
            # Full monitoring should be done via GitHub Actions or cron
            results = []
            isins = list(ref_data.keys())

            # Check first 3 URLs per ISIN (total 6 URLs, should finish in <10s)
            for isin in isins:
                if isin not in sources_data:
                    continue

                urls = sources_data[isin]['urls'][:3]  # Limit to 3 URLs per ISIN
                ref = ref_data[isin]

                for url in urls:
                    result = extract_web.extract_from_url(url, timeout=3, sleep_ms=0)
                    result['isin'] = isin

                    # Compare with reference
                    status = monitor.compare_result(result, ref['name'], ref['ter'])
                    result['status'] = status

                    results.append(result)

            # Prepare response
            response_data = {
                'success': True,
                'results': results,
                'reference': ref_data,
                'note': 'Quick scan (3 URLs per ETF). For full scan, use scheduled monitoring.'
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


def load_or_generate_reference():
    """Load reference data from cache or generate from PDFs"""
    # For Vercel, we'll embed the reference data directly
    # since we can't access local files
    return {
        "LU3098954871": {
            "name": "TEQ - General Artificial Intelligence R EUR UCITS ETF (Acc)",
            "ter": 0.69,
            "source": "embedded"
        },
        "LU3075459852": {
            "name": "Inyova Impact Investing Active Equity Fund UCITS ETF EUR",
            "ter": 0.95,
            "source": "embedded"
        }
    }


def load_or_generate_sources():
    """Load sources data"""
    # Generate sources using our curated list
    isins = ["LU3098954871", "LU3075459852"]

    # Use the curated sources module to generate URLs
    sources = {}
    from src.source_overrides import load_overrides
    from src.curated_sources import ISIN_TEMPLATES
    from datetime import datetime

    # Load overrides
    overrides_path = os.path.join(os.path.dirname(__file__), '..', '..', 'src', 'source_overrides.json')
    with open(overrides_path, 'r') as f:
        overrides = json.load(f)

    for isin in isins:
        urls = []

        # Add ISIN-based template URLs
        templates = [
            "https://www.justetf.com/de/etf-profile.html?isin={ISIN}",
            "https://extraetf.com/de/etf-profile/{ISIN}",
            "https://www.finanzfluss.de/informer/etf/{isin_lower}/",
            "https://www.comdirect.de/inf/etfs/{ISIN}",
            "https://www.avl-investmentfonds.de/fonds/details/{ISIN}"
        ]

        for template in templates:
            url = template.format(ISIN=isin, isin_lower=isin.lower())
            urls.append(url)

        # Add hardcoded overrides
        if isin in overrides:
            urls.extend(overrides[isin])

        sources[isin] = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "urls": urls
        }

    return sources
