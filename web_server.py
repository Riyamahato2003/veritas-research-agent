"""Run the web UI locally: python web_server.py (port 8000)."""
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from api.research import handler

class Local(SimpleHTTPRequestHandler):
    send_json = handler.send_json
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(Path(__file__).parent / 'public'), **kwargs)
    def do_GET(self):
        if self.path.split('?')[0] == '/api/research':
            return handler.do_GET(self)
        return super().do_GET()
    def do_POST(self):
        if self.path.split('?')[0] == '/api/research':
            return handler.do_POST(self)
        self.send_error(404)

if __name__ == '__main__':
    print('Veritas: http://localhost:8000')
    ThreadingHTTPServer(('127.0.0.1', 8000), Local).serve_forever()
