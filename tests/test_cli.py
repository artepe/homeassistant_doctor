import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from ha_doctor.cli import main
from ha_doctor.client import HAClient


class ClientTests(unittest.TestCase):
    def test_rejects_urls_with_credentials(self):
        with self.assertRaises(ValueError):
            HAClient("http://user:secret@localhost:8123", "abc")

    def test_rejects_non_http(self):
        with self.assertRaises(ValueError):
            HAClient("file:///etc/passwd", "abc")

    def test_empty_token(self):
        with self.assertRaises(ValueError):
            HAClient("https://example.com", "")

    def test_no_redirects(self):
        c = HAClient("http://localhost:8123", "abc")
        h = next(h for h in c._opener.handlers if h.__class__.__name__ == 'NoRedirects')
        self.assertIsNone(h.redirect_request(None, None, 302, "redirect", {}, "https://bad.example"))


class CliTests(unittest.TestCase):
    def test_demo_creates_html_and_json_without_token(self):
        with tempfile.TemporaryDirectory() as td:
            html = str(Path(td) / "report.html")
            js = str(Path(td) / "report.json")
            with patch.dict(os.environ, {"HA_TOKEN": ""}):
                code = main(["--demo", "--html", html, "--json", js])
            self.assertEqual(code, 1)  # demo contains an intentional critical outage
            self.assertIn("HA Doctor", Path(html).read_text())
            self.assertIn("simultaneous_outage", [f["code"] for f in json.loads(Path(js).read_text())["findings"]])

class HttpProtocolTests(unittest.TestCase):
    def test_read_only_http_endpoints(self):
        import threading
        from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
        from ha_doctor.client import DoctorConnectionError
        hits = []
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                hits.append((self.command, self.path, self.headers.get('Authorization')))
                if self.path == '/api/states':
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    self.wfile.write(b'[{"entity_id":"sensor.a","state":"1"}]')
                elif self.path == '/api/config':
                    self.send_response(401)
                    self.end_headers()
                elif self.path == '/api/error_log':
                    self.send_response(302)
                    self.send_header('Location', 'http://localhost:9/do-not-leak-token')
                    self.end_headers()
                else:
                    self.send_response(404)
                    self.end_headers()
            def log_message(self, *args):
                pass
        srv = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=srv.serve_forever, daemon=True)
        thread.start()
        try:
            client = HAClient(f'http://127.0.0.1:{srv.server_address[1]}', 'testtoken')
            self.assertEqual(len(client.states()), 1)
            with self.assertRaisesRegex(DoctorConnectionError, 'HTTP 401'):
                client.config()
            with self.assertRaisesRegex(DoctorConnectionError, 'Redirect refused'):
                client.errors()
            self.assertEqual([x[1] for x in hits], ['/api/states','/api/config','/api/error_log'])
            self.assertTrue(all(x[0] == 'GET' and x[2] == 'Bearer testtoken' for x in hits))
        finally:
            srv.shutdown()
            srv.server_close()

if __name__ == "__main__":
    unittest.main()
