#!/usr/bin/env python3
"""
Test server for the new per-ETF API
Simulates Vercel serverless function locally
"""
import http.server
import socketserver
import json
import sys
import os
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

# Set environment variable for API key
if not os.environ.get('ANTHROPIC_API_KEY'):
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        # Try to load .env manually
        env_file = Path(__file__).parent / '.env'
        if env_file.exists():
            with open(env_file) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        os.environ[key.strip()] = value.strip()

PORT = 3000

class TestHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        """Serve static files"""
        if self.path == '/':
            self.path = '/public/index.html'
        elif self.path.startswith('/css/') or self.path.startswith('/js/'):
            self.path = '/public' + self.path
        else:
            self.path = '/public' + self.path

        return http.server.SimpleHTTPRequestHandler.do_GET(self)

    def do_POST(self):
        """Handle API requests"""
        if self.path == '/api/monitor':
            # Import the handler from api/monitor.py
            from api.monitor import handler

            # Create a mock handler instance
            api_handler = handler(self.request, self.client_address, self.server)
            api_handler.headers = self.headers
            api_handler.rfile = self.rfile
            api_handler.wfile = self.wfile
            api_handler.send_response = self.send_response
            api_handler.send_header = self.send_header
            api_handler.end_headers = self.end_headers

            # Call the POST handler
            api_handler.do_POST()
        else:
            self.send_error(404)

    def do_OPTIONS(self):
        """Handle CORS preflight"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()


if __name__ == '__main__':
    os.chdir(Path(__file__).parent)

    print("""
╔══════════════════════════════════════════════════════════╗
║     🚀 ETF Monitor - Per-ETF Architecture Test          ║
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
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n\n👋 Server stopped!")
