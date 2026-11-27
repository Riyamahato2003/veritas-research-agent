"""HTTP boundary for the existing Veritas engine. No credentials returned to clients."""
from http.server import BaseHTTPRequestHandler
import hmac
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from veritas.agent import run

FAULTS = {'none', 'timeout', 'transient', 'outage', 'malformed', 'injection', 'noise'}
MAX_BODY = 4096


def capabilities():
    paid = bool(os.getenv('BRAVE_API_KEY') or os.getenv('OPENAI_API_KEY'))
    code = bool(os.getenv('VERITAS_LIVE_ACCESS_CODE'))
    public = os.getenv('VERITAS_ALLOW_PUBLIC_LIVE', '').lower() == 'true'
    return {'demo': True, 'live': paid and (code or public),
            'access_code_required': code, 'providers': {'github': True, 'wiki': True,
            'web': bool(os.getenv('BRAVE_API_KEY')), 'model': bool(os.getenv('OPENAI_API_KEY'))}}


def request_report(data):
    if not isinstance(data, dict):
        return 400, {'error': 'Expected a JSON object.'}
    q, mode, fault = data.get('question'), data.get('mode', 'demo'), data.get('fault', 'none')
    if not isinstance(q, str) or not 3 <= len(q.strip()) <= 600:
        return 400, {'error': 'Enter a research question of 3–600 characters.'}
    if mode not in ('demo', 'live') or not isinstance(fault, str) or fault not in FAULTS:
        return 400, {'error': 'Invalid research mode or failure scenario.'}
    if mode == 'live':
        if fault != 'none':
            return 400, {'error': 'Fault simulation is available in demo mode only.'}
        caps = capabilities()
        if not caps['live']:
            return 403, {'error': 'Live research is not enabled. Demo mode remains available.'}
        expected = os.getenv('VERITAS_LIVE_ACCESS_CODE', '')
        supplied = data.get('access_code', '')
        if expected and (not isinstance(supplied, str) or not hmac.compare_digest(supplied.encode(), expected.encode())):
            return 403, {'error': 'A valid live research access code is required.'}
    use_model = data.get('use_model', True)
    if not isinstance(use_model, bool):
        return 400, {'error': 'use_model must be a boolean.'}
    try:
        return 200, run(q, mode, fault, use_model).to_dict()
    except ValueError as exc:
        return 400, {'error': str(exc)}
    except Exception:
        # Never return provider responses, credentials, or stack traces to the browser.
        return 500, {'error': 'Research could not complete. Try again or use demo mode.'}


class handler(BaseHTTPRequestHandler):
    def send_json(self, status, payload):
        body = json.dumps(payload, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        self.send_json(200, capabilities())

    def do_POST(self):
        if self.headers.get('Content-Type', '').split(';')[0].strip().lower() != 'application/json':
            return self.send_json(415, {'error': 'Use application/json.'})
        try:
            length = int(self.headers.get('Content-Length', '0'))
        except ValueError:
            return self.send_json(400, {'error': 'Invalid request length.'})
        if not 0 < length <= MAX_BODY:
            return self.send_json(413, {'error': 'Request body is empty or too large.'})
        try:
            data = json.loads(self.rfile.read(length))
        except (ValueError, UnicodeError):
            return self.send_json(400, {'error': 'Malformed JSON.'})
        status, result = request_report(data)
        self.send_json(status, result)
