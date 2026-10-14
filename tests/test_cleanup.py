"""Safety and WebSocket contract tests for opt-in registry cleanup."""
import json
import os
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import Mock, patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from http.server import HTTPServer
from urllib.parse import urlencode

from ha_doctor.cleanup import find_candidates, choose_still_problematic, backup_selection
from ha_doctor.cleanup_ui import make_handler, list_page, execute_plan
from ha_doctor.client import HAClient, DoctorConnectionError
from ha_doctor.registry import HARegistry


def fixture():
    entries = [
        {"entity_id": "sensor.good", "platform": "mqtt", "unique_id": "u1"},
        {"entity_id": "sensor.zero", "platform": "mqtt", "unique_id": "u2"},
        {"entity_id": "binary_sensor.off", "platform": "mqtt", "unique_id": "u3"},
        {"entity_id": "sensor.missing", "platform": "local", "unique_id": "u4"},
        {"entity_id": "sensor.empty", "platform": "local", "unique_id": "u5"},
        {"entity_id": "sensor.unknown", "platform": "local", "unique_id": "u6"},
        {"entity_id": "sensor.unavailable", "platform": "local", "unique_id": "u7"},
        {"entity_id": "sensor.disabled", "disabled_by": "user", "platform": "mqtt", "unique_id": "u8"},
        {"entity_id": "switch.bad", "platform": "test", "unique_id": "u9"},
    ]
    states = [
        {"entity_id": "sensor.good", "state": "22"},
        {"entity_id": "sensor.zero", "state": "0"},
        {"entity_id": "binary_sensor.off", "state": "off"},
        {"entity_id": "sensor.empty", "state": ""},
        {"entity_id": "sensor.unknown", "state": "unknown"},
        {"entity_id": "sensor.unavailable", "state": "unavailable"},
        {"entity_id": "switch.bad", "state": "unavailable"},
        {"entity_id": "sensor.orphan_state_only", "state": "unavailable"},
    ]
    return entries, states


class ScannerTests(unittest.TestCase):
    def test_only_flagged_registry_sensors(self):
        entries, states = fixture()
        found = find_candidates(entries, states)
        self.assertEqual({x.entity_id: x.reason for x in found}, {
            "sensor.missing": "missing", "sensor.empty": "empty",
            "sensor.unknown": "unknown", "sensor.unavailable": "unavailable",
        })

    def test_revalidation_skips_changed_identity_and_recovered(self):
        entries, states = fixture()
        picked = find_candidates(entries, states)
        recovered = [{**s, "state": "18"} if s["entity_id"] == "sensor.unavailable" else s for s in states]
        changed = [{**e, "unique_id": "different"} if e["entity_id"] == "sensor.empty" else e for e in entries]
        safe, skipped = choose_still_problematic(picked, find_candidates(changed, recovered))
        self.assertEqual({c.entity_id for c in safe}, {"sensor.missing", "sensor.unknown"})
        self.assertEqual(set(skipped), {"sensor.unavailable", "sensor.empty"})

    def test_backup_creates_private_metadata_snapshot(self):
        entries, states = fixture()
        with tempfile.TemporaryDirectory() as folder:
            file = backup_selection(find_candidates(entries, states), directory=folder)
            data = json.loads(file.read_text(encoding="utf-8"))
            self.assertEqual(data["count"], 4)
            self.assertIn("NOT an importable", data["warning"])
            self.assertEqual(file.stat().st_mode & 0o777, 0o600)
            self.assertNotIn("access_token", file.read_text())

    def test_html_escapes_untrusted_registry_text_and_unchecked_inputs(self):
        entries, states = fixture()
        entries[3]["name"] = "<img src=x onerror=alert(1)>"
        html = list_page(find_candidates(entries, states), "safecsrf")
        self.assertIn("&lt;img src=x", html)
        self.assertNotIn("<img src=x", html)
        self.assertNotIn("checked", html.split("<input type='checkbox'")[1].split(">", 1)[0])


class FakeSocket:
    def __init__(self, replies):
        self.replies = list(replies)
        self.outgoing = []
        self.closed = False

    def recv(self):
        return json.dumps(self.replies.pop(0))

    def send(self, data):
        self.outgoing.append(json.loads(data))

    def close(self):
        self.closed = True


class WebsocketTests(unittest.TestCase):
    def test_auth_registry_listing_and_remove(self):
        sock = FakeSocket([
            {"type": "auth_required"}, {"type": "auth_ok"},
            {"type": "result", "id": 1, "success": True, "result": [{"entity_id": "sensor.foo"}]},
            {"type": "result", "id": 2, "success": True, "result": None},
        ])
        client = HAClient("https://example.com/ha", "secret123")
        with HARegistry(client, socket_factory=lambda *a, **kw: sock) as ws:
            self.assertEqual(ws.list_entities()[0]["entity_id"], "sensor.foo")
            ws.remove("sensor.foo")
        self.assertEqual(sock.outgoing, [
            {"type": "auth", "access_token": "secret123"},
            {"id": 1, "type": "config/entity_registry/list"},
            {"id": 2, "type": "config/entity_registry/remove", "entity_id": "sensor.foo"},
        ])
        self.assertTrue(sock.closed)

    def test_auth_failure_and_admin_denied_do_not_leak_secret(self):
        client = HAClient("http://localhost:8123", "super-secret")
        bad_auth = FakeSocket([{"type": "auth_required"}, {"type": "auth_invalid", "message": "super-secret"}])
        with self.assertRaises(DoctorConnectionError) as cm:
            with HARegistry(client, socket_factory=lambda *a, **kw: bad_auth):
                pass
        self.assertNotIn("super-secret", str(cm.exception))
        denied = FakeSocket([{"type": "auth_required"}, {"type": "auth_ok"},
                            {"type": "result", "id": 1, "success": False, "error": {"code": "unauthorized"}}])
        with HARegistry(client, socket_factory=lambda *a, **kw: denied) as ws:
            with self.assertRaisesRegex(DoctorConnectionError, "unauthorized"):
                ws.remove("sensor.foo")


class CleanupExecutionTests(unittest.TestCase):
    def test_apply_backups_before_first_delete_and_skips_recovered(self):
        entries, states = fixture()
        candidates = find_candidates(entries, states)
        still = [c for c in candidates if c.reason != "empty"]
        operations = []

        class Registry:
            def __init__(self, client):
                pass
            def __enter__(self):
                return self
            def __exit__(self, *args):
                pass
            def remove(self, entity_id):
                operations.append("remove:" + entity_id)

        def backup(cs, directory=None):
            operations.append("backup")
            return Path("/tmp/test-audit.json")

        with patch("ha_doctor.cleanup_ui.get_scan", return_value=still), \
             patch("ha_doctor.cleanup_ui.HARegistry", Registry), \
             patch("ha_doctor.cleanup_ui.backup_selection", side_effect=backup):
            deleted, skipped, failed, audit = execute_plan(Mock(), candidates)
        self.assertEqual(set(skipped), {"sensor.empty"})
        self.assertEqual(set(deleted), {c.entity_id for c in still})
        self.assertFalse(failed)
        self.assertEqual(operations[0], "backup")

    def test_backup_failure_means_zero_registry_writes(self):
        entries, states = fixture()
        c = find_candidates(entries, states)
        with patch("ha_doctor.cleanup_ui.get_scan", return_value=c), \
             patch("ha_doctor.cleanup_ui.backup_selection", side_effect=OSError("disk full")), \
             patch("ha_doctor.cleanup_ui.HARegistry") as registry:
            with self.assertRaises(OSError):
                execute_plan(Mock(), c)
            registry.assert_not_called()


class BrowserSafetyTests(unittest.TestCase):
    def test_browser_requires_preview_and_explicit_second_confirmation(self):
        entries, states = fixture()
        candidates = find_candidates(entries, states)
        csrf = "abcdefgh"
        client = Mock()
        server = HTTPServer(("127.0.0.1", 0), make_handler(client, csrf))
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f"http://127.0.0.1:{server.server_port}"

        def post(path, params, origin=True):
            headers = {"Content-Type": "application/x-www-form-urlencoded"}
            if origin:
                headers["Origin"] = base
            req = Request(base + path, data=urlencode(params, doseq=True).encode(), headers=headers)
            return urlopen(req).read().decode()

        try:
            with patch("ha_doctor.cleanup_ui.get_scan", return_value=candidates), \
                 patch("ha_doctor.cleanup_ui.execute_plan", return_value=([], [], [], None)) as apply:
                html = urlopen(base + "/").read().decode()
                self.assertIn("0 selected", html)
                self.assertIn("sensor.missing", html)
                with self.assertRaises(HTTPError) as cm:
                    post("/apply", {"csrf": csrf, "confirmation": "DELETE 1", "nonce": "fake"})
                self.assertEqual(cm.exception.code, 409)
                preview = post("/preview", {"csrf": csrf, "entity": ["sensor.missing"]})
                self.assertIn("DELETE 1", preview)
                import re
                nonce = re.search(r"name='nonce' value='([^']+)'", preview).group(1)
                with self.assertRaises(HTTPError):
                    post("/apply", {"csrf": csrf, "nonce": nonce, "confirmation": "DELETE 99"})
                apply.assert_not_called()
                preview = post("/preview", {"csrf": csrf, "entity": ["sensor.missing"]})
                nonce = re.search(r"name='nonce' value='([^']+)'", preview).group(1)
                response = post("/apply", {"csrf": csrf, "nonce": nonce, "confirmation": "DELETE 1"})
                self.assertIn("Cleanup completed", response)
                apply.assert_called_once()
                with self.assertRaises(HTTPError) as cm:
                    post("/preview", {"csrf": csrf, "entity": ["sensor.missing"]}, origin=False)
                self.assertEqual(cm.exception.code, 403)
        finally:
            server.shutdown()
            server.server_close()


if __name__ == "__main__":
    unittest.main()
