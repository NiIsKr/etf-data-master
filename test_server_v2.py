#!/usr/bin/env python3
"""
Improved test server - directly implements the API logic
"""
import http.server
import socketserver
import json
import sys
import os
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

# Load environment
env_file = Path(__file__).parent / '.env'
if env_file.exists():
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key.strip()] = value.strip()

PORT = 3000

# Import after setting environment
from api.monitor import (
    REFERENCE_DATA, SOURCES,
    process_single_url,
    ThreadPoolExecutor, as_completed
)

class TestHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        """Suppress detailed logging"""
        pass

    def do_GET(self):
        """Serve static files"""
        if self.path == '/':
            self.path = '/public/index.html'
        elif self.path.startswith('/css/') or self.path.startswith('/js/'):
            self.path = '/public' + self.path
        elif self.path == '/favicon.ico':
            self.send_error(404)
            return
        else:
            self.path = '/public' + self.path

        return http.server.SimpleHTTPRequestHandler.do_GET(self)

    def do_POST(self):
        """Handle API requests - reimplemented from monitor.py"""
        if self.path != '/api/monitor':
            self.send_error(404)
            return

        try:
            # Parse request body
            content_length = int(self.headers.get('Content-Length', 0))
            target_isin = None

            if content_length > 0:
                body = self.rfile.read(content_length).decode('utf-8')
                try:
                    data = json.loads(body)
                    target_isin = data.get('isin')
                except:
                    pass

            print(f"🔍 API Request: ISIN={target_isin or 'ALL'}")
            results = []

            # Collect URLs to check
            tasks = []
            for isin, urls in SOURCES.items():
                if target_isin and isin != target_isin:
                    continue

                ref = REFERENCE_DATA[isin]
                for url in urls:
                    tasks.append((isin, url, ref))

            url_count = len(tasks)
            etf_names = [REFERENCE_DATA[isin]['name'] for isin in SOURCES.keys()
                         if not target_isin or isin == target_isin]

            print(f"  → Checking {url_count} URLs...")

            # Process URLs in parallel
            with ThreadPoolExecutor(max_workers=10) as executor:
                futures = [executor.submit(process_single_url, isin, url, ref)
                          for isin, url, ref in tasks]

                for i, future in enumerate(as_completed(futures), 1):
                    try:
                        result = future.result()
                        results.append(result)
                        print(f"  → Completed {i}/{url_count}: {result.get('status', 'UNKNOWN')}")
                    except Exception as e:
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
                'checked_isin': target_isin,
                'url_count': url_count,
                'note': f'Checked {url_count} URLs for {len(etf_names)} ETF(s) - intelligent extraction with Claude Haiku'
            }

            print(f"✅ Complete! {len(results)} results")

            # Send response
            response_json = json.dumps(response_data).encode('utf-8')

            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(response_json)))
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(response_json)

        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()

            error_response = {
                'success': False,
                'error': str(e)
            }

            error_json = json.dumps(error_response).encode('utf-8')

            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(error_json)))
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(error_json)

    def do_OPTIONS(self):
        """Handle CORS preflight"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.send_header('Content-Length', '0')
        self.end_headers()


if __name__ == '__main__':
    os.chdir(Path(__file__).parent)

    print("""
╔══════════════════════════════════════════════════════════╗
║     🚀 ETF Monitor - Per-ETF Architecture Test v2       ║
╚══════════════════════════════════════════════════════════╝

Server running on: http://localhost:{}

📱 Open this URL in your browser!

🔘 New Features:
   • Check TEQ button (8 URLs, ~25s)
   • Check Inyova button (8 URLs, ~25s)
   • Check ALL button (16 URLs, ~50s)

Press Ctrl+C to stop.
""".format(PORT))

    with socketserver.TCPServer(("", PORT), TestHandler) as httpd:
        httpd.allow_reuse_address = True
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n\n👋 Server stopped!")
