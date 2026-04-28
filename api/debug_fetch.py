"""Temporary debug endpoint: fetch a URL with the same headers the monitor uses
and return diagnostics so we can see what the Vercel Lambda actually receives."""
import json
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

import requests

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Encoding": "gzip, deflate",
    "Accept-Language": "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7",
    "Referer": "https://www.google.com/",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "cross-site",
    "Upgrade-Insecure-Requests": "1",
}


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        params = parse_qs(urlparse(self.path).query)
        url = (params.get("url") or [""])[0]
        out = {"url": url}
        if not url:
            out["error"] = "missing ?url= parameter"
        else:
            try:
                r = requests.get(url, headers=HEADERS, timeout=10, allow_redirects=True)
                out["status"] = r.status_code
                out["final_url"] = r.url
                out["headers"] = {
                    "content-type": r.headers.get("Content-Type"),
                    "content-encoding": r.headers.get("Content-Encoding"),
                    "content-length": r.headers.get("Content-Length"),
                    "server": r.headers.get("Server"),
                    "cf-ray": r.headers.get("CF-Ray"),
                    "x-akamai-request-id": r.headers.get("X-Akamai-Request-ID"),
                    "set-cookie": r.headers.get("Set-Cookie"),
                }
                out["text_len"] = len(r.text)
                out["raw_first_200"] = r.content[:200].hex()
                out["text_first_500"] = r.text[:500]
                out["text_has_isin"] = "LU3098954871" in r.text
                out["text_has_ter_keyword"] = any(
                    k in r.text for k in ("TER", "Gesamtkost", "laufende Kosten")
                )
            except Exception as e:
                out["error"] = f"{type(e).__name__}: {e}"

        body = json.dumps(out, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
