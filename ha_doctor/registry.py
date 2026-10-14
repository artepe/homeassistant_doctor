"""Authenticated Home Assistant WebSocket entity registry protocol (optional dependency)."""
from __future__ import annotations

from urllib.parse import urlsplit, urlunsplit
import json
import ssl
from .client import DoctorConnectionError


class HARegistry:
    def __init__(self, client, *, socket_factory=None):
        self.client = client
        self._factory = socket_factory
        self.socket = None
        self.request_id = 0

    def __enter__(self):
        if self._factory is None:
            try:
                from websocket import create_connection
            except ImportError:
                raise DoctorConnectionError(
                    'Sensor Cleanup requires websocket-client. Install: python3 -m pip install ".[cleanup]"'
                ) from None
            self._factory = create_connection
        p = urlsplit(self.client.url)
        ws_url = urlunsplit(("wss" if p.scheme == "https" else "ws", p.netloc,
                             p.path.rstrip("/") + "/api/websocket", "", ""))
        try:
            self.socket = self._factory(
                ws_url, timeout=self.client.timeout, origin=f"{p.scheme}://{p.netloc}",
                redirect_limit=0,  # never send token to a WebSocket redirect target
                sslopt={"cert_reqs": ssl.CERT_REQUIRED, "check_hostname": True},
            )
            first = self._receive()
            if first.get("type") != "auth_required":
                raise DoctorConnectionError("Unexpected Home Assistant WebSocket handshake")
            self.socket.send(json.dumps({"type": "auth", "access_token": self.client.token}))
            auth = self._receive()
            if auth.get("type") != "auth_ok":
                raise DoctorConnectionError("Home Assistant WebSocket authentication failed")
            return self
        except DoctorConnectionError:
            self.__exit__(None, None, None)
            raise
        except Exception as err:
            self.__exit__(None, None, None)
            raise DoctorConnectionError(f"WebSocket unavailable ({type(err).__name__}); check URL and connectivity") from None

    def __exit__(self, exc_type, exc, tb):
        if self.socket is not None:
            try:
                self.socket.close()
            except Exception:
                pass
            self.socket = None

    def _receive(self):
        result = self.socket.recv()
        if not isinstance(result, str) or len(result) > 16_000_000:
            raise DoctorConnectionError("Invalid or oversized WebSocket reply")
        msg = json.loads(result)
        if not isinstance(msg, dict):
            raise DoctorConnectionError("Unexpected WebSocket response")
        return msg

    def request(self, kind: str, **payload):
        if self.socket is None:
            raise DoctorConnectionError("WebSocket connection is closed")
        self.request_id += 1
        req_id = self.request_id
        try:
            self.socket.send(json.dumps({"id": req_id, "type": kind, **payload}))
            for _ in range(30):
                response = self._receive()
                if response.get("type") != "result" or response.get("id") != req_id:
                    continue  # ignore unrelated events
                if not response.get("success"):
                    code = response.get("error", {}).get("code", "unknown")
                    # Do not expose upstream error body because it could contain private data.
                    raise DoctorConnectionError(f"Home Assistant rejected {kind} ({code})")
                return response.get("result")
            raise DoctorConnectionError("No matching WebSocket API response")
        except DoctorConnectionError:
            raise
        except Exception as err:
            raise DoctorConnectionError(f"WebSocket command failed ({type(err).__name__})") from None

    def list_entities(self):
        data = self.request("config/entity_registry/list")
        if not isinstance(data, list):
            raise DoctorConnectionError("Unexpected entity registry list")
        return data

    def remove(self, entity_id):
        self.request("config/entity_registry/remove", entity_id=entity_id)
