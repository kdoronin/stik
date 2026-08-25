"""Interactive localhost OAuth setup for Strava."""

from __future__ import annotations

import getpass
import secrets
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from queue import Queue
from urllib.parse import parse_qs, urlparse

from .auth import complete_authorization
from .core import ConfigStore, build_authorization_url

HOST = "127.0.0.1"
PORT = 8111
REDIRECT_URI = f"http://localhost:{PORT}/callback"


def parse_callback(path: str, *, expected_state: str) -> str:
    parsed = urlparse(path)
    params = parse_qs(parsed.query)
    if params.get("state", [None])[0] != expected_state:
        raise ValueError("OAuth state mismatch")
    if params.get("error"):
        raise ValueError(f"Strava authorization failed: {params['error'][0]}")
    code = params.get("code", [None])[0]
    if not code:
        raise ValueError("Strava callback did not contain an authorization code")
    return code


def main() -> None:
    print("Create or open your Strava API app at https://www.strava.com/settings/api")
    print("Set Authorization Callback Domain to: localhost\n")
    client_id = input("Strava Client ID: ").strip()
    client_secret = getpass.getpass("Strava Client Secret: ").strip()
    if not client_id or not client_secret:
        raise SystemExit("Client ID and Client Secret are required")

    state = secrets.token_urlsafe(24)
    result: Queue[tuple[bool, str]] = Queue(maxsize=1)

    class CallbackHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            try:
                code = parse_callback(self.path, expected_state=state)
                result.put((True, code))
                status, body = 200, "Strava connected. You can close this tab."
            except ValueError as exc:
                result.put((False, str(exc)))
                status, body = 400, str(exc)
            payload = body.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, format: str, *args: object) -> None:
            return

    try:
        server = HTTPServer((HOST, PORT), CallbackHandler)
    except OSError as exc:
        raise SystemExit(f"Cannot listen on localhost:{PORT}: {exc}") from exc
    server.timeout = 300
    thread = threading.Thread(target=server.handle_request, daemon=True)
    thread.start()

    auth_url = build_authorization_url(client_id, REDIRECT_URI, state=state)
    print("\nOpening Strava authorization in your browser...")
    print(auth_url)
    webbrowser.open(auth_url)

    thread.join(timeout=305)
    server.server_close()
    if result.empty():
        raise SystemExit("Timed out waiting for Strava authorization")
    success, value = result.get_nowait()
    if not success:
        raise SystemExit(value)

    athlete = complete_authorization(
        store=ConfigStore(),
        client_id=client_id,
        client_secret=client_secret,
        code=value,
    )
    name = " ".join(filter(None, [athlete.get("firstname"), athlete.get("lastname")]))
    print(f"\nConnected to Strava{f' as {name}' if name else ''}.")
    print("Credentials and rotating tokens are stored locally with mode 0600.")


if __name__ == "__main__":
    main()
