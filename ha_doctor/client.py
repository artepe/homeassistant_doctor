"""Dependency-free REST API client used by read-only diagnostics and cleanup scans."""

import json
import ssl
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener, HTTPSHandler


class DoctorConnectionError(Exception):
    """Expected connection failure with a token-free explanation."""


class NoRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # Never forward Authorization to a redirected origin.
        return None


class HAClient:
    def __init__(self, url: str, token: str, timeout: int = 12):
        url = url.strip().rstrip("/")
        parts = urlsplit(url)
        if (parts.scheme not in {"http", "https"} or not parts.netloc
                or parts.username or parts.password or parts.query or parts.fragment):
            raise ValueError("HA_URL must be an http(s) base URL without credentials or query parameters")
        if not token.strip():
            raise ValueError("Set HA_TOKEN to a Home Assistant long-lived access token")
        self.url = url[:-4] if url.endswith("/api") else url
        self.token = token.strip()
        self.timeout = timeout
        self._opener = build_opener(NoRedirects(), HTTPSHandler(context=ssl.create_default_context()))

    def get(self, path: str, *, text: bool = False):
        if not path.startswith("/") or "?" in path or "#" in path:
            raise ValueError("Invalid API endpoint")
        req = Request(
            self.url + "/api" + path,
            headers={"Authorization": "Bearer " + self.token, "Accept": "application/json"},
            method="GET",
        )
        try:
            with self._opener.open(req, timeout=self.timeout) as res:
                # Refuse unexpectedly large responses; keep memory and HTML reports safe.
                data = res.read(3_000_001)
                if len(data) > 3_000_000:
                    raise DoctorConnectionError("Home Assistant returned an oversized response")
                return data.decode("utf-8", errors="replace") if text else json.loads(data)
        except HTTPError as err:
            if err.code == 401:
                raise DoctorConnectionError("Authentication failed (HTTP 401). Check HA_TOKEN") from None
            if err.code == 403:
                raise DoctorConnectionError("Access denied (HTTP 403). Check token permissions") from None
            if 300 <= err.code < 400:
                raise DoctorConnectionError(f"Redirect refused (HTTP {err.code}); use the final HA_URL directly") from None
            raise DoctorConnectionError(f"Home Assistant endpoint returned HTTP {err.code}") from None
        except (URLError, TimeoutError, OSError) as err:
            # Do not include URL or exception text, which may contain credentials.
            raise DoctorConnectionError(f"Cannot reach Home Assistant ({type(err).__name__}). Check URL, network and TLS") from None
        except (ValueError, UnicodeError) as err:
            raise DoctorConnectionError(f"Invalid API response ({type(err).__name__})") from None

    def states(self):
        result = self.get("/states")
        if not isinstance(result, list):
            raise DoctorConnectionError("Unexpected /api/states format")
        return result

    def config(self):
        result = self.get("/config")
        return result if isinstance(result, dict) else {}

    def errors(self):
        return self.get("/error_log", text=True)
