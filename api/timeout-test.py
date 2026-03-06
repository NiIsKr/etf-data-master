"""
Vercel Timeout Test
Tests if we have 10s or 60s timeout on Free Plan
"""
import json
import time
from http.server import BaseHTTPRequestHandler


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Sleep for various durations to test timeout"""
        try:
            # Get sleep duration from query parameter (default 30s)
            query = self.path.split('?')[1] if '?' in self.path else ''
            params = dict(param.split('=') for param in query.split('&') if '=' in param)
            sleep_seconds = int(params.get('sleep', 30))

            # Sleep
            start = time.time()
            time.sleep(sleep_seconds)
            end = time.time()

            # Response
            response = {
                'success': True,
                'requested_sleep': sleep_seconds,
                'actual_duration': round(end - start, 2),
                'message': f'Successfully waited {sleep_seconds} seconds! Vercel timeout is >{sleep_seconds}s'
            }

            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode('utf-8'))

        except Exception as e:
            error = {
                'success': False,
                'error': str(e)
            }
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(error).encode('utf-8'))

    def do_OPTIONS(self):
        """Handle CORS preflight"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
