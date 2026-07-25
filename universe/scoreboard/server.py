"""
Scoreboard — Flag tracker para o universo sintético
Roda em http://localhost:9090
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import time
import os

FLAGS = {
    "flag{web_master_2026}": {"target": "TARGET-01", "points": 100, "found": False, "found_by": "", "time": ""},
    "flag{ssh_ghost_2026}": {"target": "TARGET-02", "points": 100, "found": False, "found_by": "", "time": ""},
    "flag{api_breaker_2026}": {"target": "TARGET-03", "points": 100, "found": False, "found_by": "", "time": ""},
    "flag{deep_vault_2026}": {"target": "TARGET-04", "points": 200, "found": False, "found_by": "", "time": ""},
    "flag{halctf_king_2026}": {"target": "TARGET-04", "points": 500, "found": False, "found_by": "", "time": ""},
}

SUBMISSIONS = []

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>🏴 Ozz Universe — Scoreboard</title>
    <style>
        body { background: #0a0a0a; color: #00ff00; font-family: 'Courier New', monospace; padding: 40px; }
        h1 { text-align: center; font-size: 2em; text-shadow: 0 0 10px #00ff00; }
        .score { font-size: 3em; text-align: center; margin: 20px; color: #0f0; }
        table { width: 100%; border-collapse: collapse; margin: 20px 0; }
        th, td { border: 1px solid #003300; padding: 12px; text-align: left; }
        th { background: #001a00; color: #00ff00; }
        .found { color: #00ff00; font-weight: bold; }
        .not-found { color: #666; }
        .mega { color: #ff0; font-size: 1.2em; }
        .log { background: #0a0a0a; border: 1px solid #003300; padding: 15px; margin-top: 20px; max-height: 300px; overflow-y: auto; }
        .log-entry { margin: 5px 0; font-size: 0.9em; }
        .submit { text-align: center; margin: 30px; }
        .submit input { background: #001a00; color: #00ff00; border: 1px solid #003300; padding: 10px; font-family: monospace; width: 400px; }
        .submit button { background: #003300; color: #00ff00; border: 1px solid #00ff00; padding: 10px 20px; cursor: pointer; font-family: monospace; }
        .submit button:hover { background: #00ff00; color: #000; }
        @keyframes pulse { 0% { opacity: 1; } 50% { opacity: 0.5; } 100% { opacity: 1; } }
        .pulse { animation: pulse 2s infinite; }
    </style>
</head>
<body>
    <h1>🏴 OZZ UNIVERSE — HALctf SYNTHETIC ENV 🏴</h1>
    <div class="score">SCORE: {score}/1000</div>
    <div style="text-align:center">Flags: {flags_found}/5</div>

    <h2>🚩 FLAGS</h2>
    <table>
        <tr><th>Flag</th><th>Target</th><th>Points</th><th>Status</th><th>Found By</th><th>Time</th></tr>
        {flag_rows}
    </table>

    <h2>📡 SUBMISSION LOG</h2>
    <div class="log">
        {log_entries}
    </div>

    <div class="submit">
        <form action="/submit" method="POST">
            <input type="text" name="flag" placeholder="Submit a flag...">
            <input type="text" name="agent" placeholder="Agent name" value="Ozz">
            <button type="submit">SUBMIT FLAG</button>
        </form>
    </div>

    <div style="text-align:center; margin-top:40px; color:#333;">
        <p>Targets: 10.0.0.10 (Web) | 10.0.0.20 (SSH/SMB) | 10.0.0.30 (API) | 10.0.0.40 (MySQL)</p>
        <p>Time: {time}</p>
    </div>
</body>
</html>
"""

class ScoreboardHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/api/flags':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(FLAGS, indent=2).encode())
        elif self.path == '/api/submissions':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(SUBMISSIONS, indent=2).encode())
        else:
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.end_headers()
            self.wfile.write(self._render().encode())

    def do_POST(self):
        if self.path == '/submit':
            length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(length).decode()
            params = dict(p.split('=') for p in body.split('&') if '=' in p)
            flag = params.get('flag', '').replace('%7B', '{').replace('%7D', '}').replace('+', ' ')
            agent = params.get('agent', 'Unknown').replace('+', ' ')

            success = False
            if flag in FLAGS and not FLAGS[flag]['found']:
                FLAGS[flag]['found'] = True
                FLAGS[flag]['found_by'] = agent
                FLAGS[flag]['time'] = time.strftime('%H:%M:%S')
                SUBMISSIONS.append({"flag": flag, "agent": agent, "time": time.strftime('%H:%M:%S'), "status": "✅ ACCEPTED"})
                success = True
            elif flag in FLAGS and FLAGS[flag]['found']:
                SUBMISSIONS.append({"flag": flag, "agent": agent, "time": time.strftime('%H:%M:%S'), "status": "⚠️ ALREADY FOUND"})
            else:
                SUBMISSIONS.append({"flag": flag, "agent": agent, "time": time.strftime('%H:%M:%S'), "status": "❌ WRONG"})

            self.send_response(303)
            self.send_header('Location', '/')
            self.end_headers()

    def _render(self):
        score = sum(f['points'] for f in FLAGS.values() if f['found'])
        flags_found = sum(1 for f in FLAGS.values() if f['found'])

        rows = []
        for flag, info in FLAGS.items():
            status = '<span class="found">✅ FOUND</span>' if info['found'] else '<span class="not-found">🔒 LOCKED</span>'
            if info['points'] >= 500 and info['found']:
                status = '<span class="mega">👑 CAPTURED</span>'
            elif info['points'] >= 500:
                status = '<span class="mega pulse">👑 MEGA FLAG</span>'
            rows.append(f"<tr><td><code>{flag}</code></td><td>{info['target']}</td><td>{info['points']}</td><td>{status}</td><td>{info['found_by']}</td><td>{info['time']}</td></tr>")

        logs = []
        for s in reversed(SUBMISSIONS[-20:]):
            logs.append(f'<div class="log-entry">[{s["time"]}] {s["agent"]}: {s["flag"]} → {s["status"]}</div>')

        return HTML_TEMPLATE.format(
            score=score,
            flags_found=flags_found,
            flag_rows='\n'.join(rows),
            log_entries='\n'.join(logs) if logs else '<div class="log-entry">No submissions yet...</div>',
            time=time.strftime('%Y-%m-%d %H:%M:%S'),
        )

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 9090))
    print(f"🏴 Scoreboard running on http://0.0.0.0:{port}")
    HTTPServer(('0.0.0.0', port), ScoreboardHandler).serve_forever()
