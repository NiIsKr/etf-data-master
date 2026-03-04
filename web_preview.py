#!/usr/bin/env python3
"""
Local preview server for the ETF Monitor Web App.
Run this to test the web interface before deploying to Vercel.
"""
import http.server
import socketserver
import os
import json
import sys
from urllib.parse import urlparse, parse_qs
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from src import reference, curated_sources, extract_web, monitor

PORT = 8000

class PreviewHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        """Serve static files"""
        if self.path == '/':
            self.path = '/web/public/index.html'
        elif self.path.startswith('/css/'):
            self.path = '/web/public' + self.path
        elif self.path.startswith('/js/'):
            self.path = '/web/public' + self.path
        else:
            self.path = '/web/public' + self.path

        return http.server.SimpleHTTPRequestHandler.do_GET(self)

    def do_POST(self):
        """Handle API requests"""
        if self.path == '/api/monitor':
            self.handle_monitor()
        else:
            self.send_error(404)

    def do_OPTIONS(self):
        """Handle CORS preflight"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def handle_monitor(self):
        """Handle monitoring request"""
        try:
            # Parse request body
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length).decode('utf-8')

            try:
                data = json.loads(body) if body else {}
            except json.JSONDecodeError:
                data = {}

            print("📡 Monitoring request received...")

            # Load reference data
            ref_data = {
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

            # Generate sources
            sources_data = self.generate_sources()

            # Run monitoring (limited to 3 URLs per ISIN for speed)
            results = []
            isins = list(ref_data.keys())

            for isin in isins:
                if isin not in sources_data:
                    continue

                urls = sources_data[isin]['urls'][:3]
                ref = ref_data[isin]

                print(f"🔍 Checking {isin}...")
                for url in urls:
                    print(f"  → {url}")
                    result = extract_web.extract_from_url(url, timeout=5, sleep_ms=0)
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
                'note': 'Local preview - checking 3 URLs per ETF'
            }

            print(f"✅ Monitoring complete! {len(results)} results")

            # Send response
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(response_data).encode('utf-8'))

        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()

            error_response = {
                'success': False,
                'error': str(e)
            }

            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(error_response).encode('utf-8'))

    def generate_sources(self):
        """Generate source URLs"""
        isins = ["LU3098954871", "LU3075459852"]
        sources = {}

        # Load overrides
        overrides_path = Path(__file__).parent / 'src' / 'source_overrides.json'
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
                "urls": urls
            }

        return sources


if __name__ == '__main__':
    os.chdir(Path(__file__).parent)

    print("""
╔══════════════════════════════════════════════════════════╗
║          🚀 ETF Monitor - Web App Preview               ║
╚══════════════════════════════════════════════════════════╝

Server läuft auf: http://localhost:{}

📱 Öffne diese URL in deinem Browser!

⚠️  Dies ist nur eine Vorschau. Für das echte Deployment
    folge der Anleitung in WEB_DEPLOYMENT.md

Drücke Ctrl+C zum Beenden.
""".format(PORT))

    with socketserver.TCPServer(("", PORT), PreviewHandler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n\n👋 Server beendet!")
