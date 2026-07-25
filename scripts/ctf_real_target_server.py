#!/usr/bin/env python3
"""
Servidor de Desafio CTF Real em Python Nativo (http.server - Zero Dependências Externas)
"""
import sys
import json
import base64
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REAL_FLAG = "FLAG{OZZ_MNHI_3.5_REAL_HTTP_SOLVE_2026}"

class CTFRequestHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # Silencia logs no stdout para manter saída limpa

    def do_GET(self):
        parsed_url = urlparse(self.path)
        path = parsed_url.path
        query = parse_qs(parsed_url.query)

        if path == "/":
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.send_header("X-Powered-By", "Ozz-Challenge-Server/1.0")
            self.end_headers()
            html = """
            <!DOCTYPE html>
            <html>
            <head><title>Blackout Corp - Portal Restrito</title></head>
            <body>
                <h1>Blackout Corp — Sistema Restrito</h1>
                <p>Acesso restrito a colaboradores autorizados.</p>
                <!-- Dica: Verifique o arquivo /robots.txt -->
            </body>
            </html>
            """
            self.wfile.write(html.encode("utf-8"))

        elif path == "/robots.txt":
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            robots = "User-agent: *\nDisallow: /vault/evidence.b64\nDisallow: /api/v1/flag_vault\n"
            self.wfile.write(robots.encode("utf-8"))

        elif path == "/vault/evidence.b64":
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            secret_payload = "ARTEFATO_FORENSE: EXIF_METADATA: FLAG_LOCATION=/api/v1/flag_vault?key=master_access_2026"
            encoded = base64.b64encode(secret_payload.encode()).decode()
            self.wfile.write(encoded.encode("utf-8"))

        elif path == "/api/v1/flag_vault":
            key = query.get("key", [""])[0]
            if key == "master_access_2026":
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                resp = {"status": "AUTHORIZED", "flag": REAL_FLAG, "system_level": "ROOT_ACCESS"}
                self.wfile.write(json.dumps(resp).encode("utf-8"))
            else:
                self.send_response(403)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                resp = {"status": "DENIED", "error": "Invalid Key"}
                self.wfile.write(json.dumps(resp).encode("utf-8"))

        else:
            self.send_response(404)
            self.end_headers()

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 5005
    server = HTTPServer(("127.0.0.1", port), CTFRequestHandler)
    print(f"🚀 Servidor CTF Alvo rodando em http://127.0.0.1:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
