"""Localhost-only, two-step HTML UI for manually removing selected sensor entries."""
from __future__ import annotations

from collections import Counter
from html import escape
from http.server import BaseHTTPRequestHandler, HTTPServer
from secrets import token_urlsafe
import time
from urllib.parse import parse_qs
import webbrowser

from .cleanup import backup_selection, choose_still_problematic, find_candidates
from .client import DoctorConnectionError
from .registry import HARegistry

CSS = """<style>
:root{color-scheme:dark}*{box-sizing:border-box}body{background:#0b1220;color:#e9edf5;font:15px system-ui,Arial,sans-serif;margin:0}
main{max-width:1120px;margin:36px auto;padding:0 20px 75px}h1{font-size:31px;letter-spacing:-.6px}h2{font-size:21px}
a{color:#94c4ff}p{line-height:1.6;color:#c0cbe0}.muted{color:#98a8c1}.panel{background:#151f32;border:1px solid #304058;border-radius:15px;padding:22px;margin:20px 0}
.warn{border-left:4px solid #f5b041;padding:12px;background:#322b22}.good{border-left:4px solid #55ce93;padding:12px;background:#1a3230}
.badge{border-radius:10px;font-size:12px;padding:4px 9px;background:#334966}.count{display:inline-block;border-radius:15px;background:#29416a;padding:9px 15px;margin:5px 8px 8px 0}
input[type=search],input[type=text]{padding:10px;background:#0c1729;color:white;border:1px solid #52617c;border-radius:8px;max-width:100%;width:350px}
button{border:0;border-radius:10px;padding:11px 17px;background:#77b4ff;color:#0d192a;font-weight:700;cursor:pointer;margin:4px 7px 4px 0}
button.secondary{background:#2f4562;color:#eef3fa}button.danger{background:#ff9b93;color:#371d1e}
.tablewrap{overflow-x:auto}table{border-collapse:collapse;width:100%;font-size:13px}th,td{padding:12px;border-bottom:1px solid #34445c;text-align:left}th{color:#b3c3db}tr:hover{background:#1d2c43}code{word-break:break-word}
#counts{color:#b6c5dd;margin:12px 0}label{cursor:pointer}.controls{display:flex;align-items:center;gap:9px;flex-wrap:wrap}.note{font-size:13px}
</style>"""


def page(title, body):
    return ("<!doctype html><html lang='en'><head><meta charset='utf-8'>"
            "<meta name='viewport' content='width=device-width, initial-scale=1'>"
            f"<title>{escape(title)}</title>{CSS}</head><body><main>{body}</main></body></html>")


def get_scan(client):
    states = client.states()
    with HARegistry(client) as ws:
        registry = ws.list_entities()
    return find_candidates(registry, states)


def list_page(candidates, csrf):
    counts = Counter(c.reason for c in candidates)
    stats = "".join(f"<span class='count'>{escape(name.title())}: <b>{counts[name]}</b></span>" for name in ("missing", "empty", "unknown", "unavailable"))
    rows = []
    for c in candidates:
        rows.append(
            "<tr class='item'><td><input type='checkbox' name='entity' value='" + escape(c.entity_id, quote=True) + "'></td>"
            f"<td><code>{escape(c.entity_id)}</code></td><td>{escape(c.name)}</td>"
            f"<td><span class='badge'>{escape(c.reason)}</span></td><td>{escape(c.platform)}</td></tr>"
        )
    form = ("<form method='post' action='/preview'><input type='hidden' name='csrf' value='" + escape(csrf) + "'>"
            "<div class='controls'><input aria-label='Filter sensors' id='search' type='search' placeholder='Filter by entity, status or platform'>"
            "<button type='button' class='secondary' onclick='checkAll(true)'>Select all visible</button>"
            "<button type='button' class='secondary' onclick='checkAll(false)'>Clear selection</button></div>"
            "<p id='counts'>0 selected</p><div class='tablewrap'><table><thead><tr>"
            "<th>Select</th><th>Entity ID</th><th>Name</th><th>Issue</th><th>Integration</th>"
            "</tr></thead><tbody>" + "".join(rows) + "</tbody></table></div>"
            "<p><button type='submit'>Preview selected for removal →</button></p></form>")
    js = """<script>
const s=document.getElementById('search'), rows=[...document.querySelectorAll('tr.item')];
function update(){let n=0;for(const r of rows){r.hidden=!r.textContent.toLowerCase().includes(s.value.toLowerCase());if(r.querySelector('input').checked)n++;}document.getElementById('counts').textContent=n+' selected / '+rows.length+' flagged';}
function checkAll(checked){for(const r of rows){if(!r.hidden)r.querySelector('input').checked=checked;}update();}
s.addEventListener('input',update);document.querySelectorAll('input[name=entity]').forEach(e=>e.addEventListener('change',update));update();
</script>"""
    return page("HA Doctor | Sensor Cleanup", "<h1>🩺 HA Doctor · Sensor Cleanup</h1>"
        "<p>Local-only sensor registry cleanup · All checkboxes start unselected</p>"
        "<div class='panel warn'><b>Warning: these are suspected issues, not proof that a sensor is broken.</b>"
        "<p>Unknown, unavailable and missing states can be temporary after a reboot or network outage. "
        "Removing a registry entry can break automations and dashboards, and an active integration may recreate it. "
        "Make a full Home Assistant backup before proceeding. No historical recorder data is purged.</p></div>"
        f"<div class='panel'><h2>{len(candidates)} flagged registered sensors</h2>{stats}" +
        "<p class='note'>Only sensor.* and binary_sensor.* entries that are not intentionally disabled are included. "
        "A valid 0 / off / on state is never considered empty. Sensors without registry entries cannot be removed here.</p>"
        + form + "</div>" + js)


def preview_page(selected, skipped, csrf, nonce):
    rows = "".join(f"<li><code>{escape(c.entity_id)}</code> — {escape(c.reason)} ({escape(c.platform)})</li>" for c in selected)
    skip = "".join(f"<li><code>{escape(e)}</code></li>" for e in skipped)
    n = len(selected)
    return page("HA Doctor | Confirm removal", "<h1>Review proposed removals</h1>"
        f"<div class='panel warn'><strong>{n} sensor(s) selected for actual registry deletion.</strong>"
        "<p>This deletes only entity registry records. No full HA backup is created by HA Doctor. "
        "An audit snapshot of the selected metadata is saved locally first, but cannot restore the HA registry automatically.</p>"
        f"<ul>{rows}</ul></div>" + (f"<div class='panel'><h2>Skipped because state changed / invalid</h2><ul>{skip}</ul></div>" if skipped else "") +
        ("<form method='post' action='/apply' class='panel'>"
         f"<input type='hidden' name='csrf' value='{escape(csrf)}'>"
         f"<input type='hidden' name='nonce' value='{escape(nonce)}'>"
         f"<p>To confirm, type <code>DELETE {n}</code> exactly:</p>"
         "<input autocomplete='off' type='text' name='confirmation' required>"
         "<p><button type='submit' class='danger'>Delete selected registry entries</button>"
         "<a href='/'>Cancel and rescan</a></p></form>" if n else "<a href='/'>Back to rescan</a>"))


def results_page(deleted, skipped, errors, backup):
    fmt = lambda ids: "".join("<li><code>" + escape(i) + "</code></li>" for i in ids)
    return page("HA Doctor | Cleanup results", "<h1>Cleanup completed</h1>"
        f"<div class='panel good'><h2>{len(deleted)} removed · {len(skipped)} skipped · {len(errors)} failed</h2>"
        f"<p>Metadata audit snapshot: <code>{escape(str(backup))}</code></p>"
        "<p>This snapshot is NOT a restorable Home Assistant backup.</p></div>"
        f"<div class='panel'><h2>Removed</h2><ul>{fmt(deleted)}</ul>"
        f"<h2>Skipped (healthy, gone, or changed identity)</h2><ul>{fmt(skipped)}</ul>"
        f"<h2>Failed</h2><ul>{fmt(errors)}</ul></div>"
        "<p><a href='/'>Run another scan</a></p>")


def execute_plan(client, selected, backup_dir=None):
    """Run right-before-delete revalidation, then audit first, then registry remove."""
    refreshed = get_scan(client)
    safe, skipped = choose_still_problematic(selected, refreshed)
    if not safe:
        return [], skipped, [], None
    # MUST save before writing any registry entries. Abort on filesystem errors.
    backup = backup_selection(safe, directory=backup_dir)
    deleted, errors = [], []
    with HARegistry(client) as ws:
        for candidate in safe:
            try:
                ws.remove(candidate.entity_id)
                deleted.append(candidate.entity_id)
            except DoctorConnectionError:
                errors.append(candidate.entity_id)
    return deleted, skipped, errors, backup


def make_handler(client, csrf, backup_dir=None):
    """Factory for a bound-loopback-only server; CSRF + explicit typed confirmation."""
    class CleanupHandler(BaseHTTPRequestHandler):
        plan = None

        def log_message(self, *args):
            pass  # avoid logging user-supplied paths and entity IDs

        def _valid_host(self):
            return self.headers.get("Host") == f"127.0.0.1:{self.server.server_port}"

        def _respond(self, html, status=200):
            encoded = html.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(encoded)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("Content-Security-Policy", "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; form-action 'self'; base-uri 'none'; frame-ancestors 'none'")
            self.end_headers()
            self.wfile.write(encoded)

        def _error(self, message, status=400):
            self._respond(page("HA Doctor | Error", f"<h1>Request not completed</h1><div class='panel warn'>{escape(message)}</div><a href='/'>Rescan</a>"), status)

        def do_GET(self):
            if not self._valid_host():
                return self._error("Invalid host", 403)
            if self.path != "/":
                return self._error("Not found", 404)
            CleanupHandler.plan = None  # Cancel an earlier pending delete on rescan.
            try:
                return self._respond(list_page(get_scan(client), csrf))
            except (DoctorConnectionError, OSError) as exc:
                return self._error(f"Cannot scan sensors: {exc}", 502)

        def do_POST(self):
            if not self._valid_host() or self.headers.get("Origin") != f"http://127.0.0.1:{self.server.server_port}":
                return self._error("Rejected cross-origin request", 403)
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= 100_000:
                    return self._error("Invalid form size")
                fields = parse_qs(self.rfile.read(length).decode("utf-8"), keep_blank_values=True)
            except (ValueError, UnicodeError):
                return self._error("Invalid request data")
            if fields.get("csrf") != [csrf]:
                return self._error("Invalid request token", 403)
            if self.path == "/preview":
                ids = set(fields.get("entity", []))
                if not ids or len(ids) > 5000:
                    return self._error("Select 1 to 5000 sensor entries")
                try:
                    inventory = get_scan(client)
                except DoctorConnectionError as exc:
                    return self._error(f"Cannot rescan sensors: {exc}", 502)
                selected = [c for c in inventory if c.entity_id in ids]
                skipped = sorted(ids - {c.entity_id for c in selected})
                nonce = token_urlsafe(24)
                CleanupHandler.plan = (nonce, time.monotonic(), selected)
                return self._respond(preview_page(selected, skipped, csrf, nonce))
            if self.path == "/apply":
                plan = CleanupHandler.plan
                CleanupHandler.plan = None  # single-use, even on incorrect confirmation
                if not plan or time.monotonic() - plan[1] > 600 or fields.get("nonce") != [plan[0]]:
                    return self._error("Review expired or invalid; rescan and preview again", 409)
                selected = plan[2]
                if not selected or fields.get("confirmation") != [f"DELETE {len(selected)}"]:
                    return self._error("Deletion not confirmed. Nothing changed.")
                try:
                    deleted, skipped, errors, backup = execute_plan(client, selected, backup_dir)
                except (DoctorConnectionError, OSError) as exc:
                    return self._error(f"Deletion aborted before completion: {exc}", 502)
                return self._respond(results_page(deleted, skipped, errors, backup))
            return self._error("Unknown action", 404)
    return CleanupHandler


def serve_cleanup(client, *, port=0, open_browser=True, backup_dir=None):
    csrf = token_urlsafe(32)
    handler = make_handler(client, csrf, backup_dir=backup_dir)
    server = HTTPServer(("127.0.0.1", port), handler)
    url = f"http://127.0.0.1:{server.server_port}/"
    print(f"HA Doctor Sensor Cleanup (local browser only): {url}\nPress Ctrl+C in Terminal to stop.")
    if open_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0
