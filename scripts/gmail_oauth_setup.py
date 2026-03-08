"""
Gmail OAuth2 setup — self-contained local server flow.
Spins up a temporary HTTP server on :8888 to capture the callback automatically.
No copy-pasting required.

Usage:
    python3 scripts/gmail_oauth_setup.py
"""

import json
import os
import sys
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
load_dotenv()

# ── Config ────────────────────────────────────────────────────────────────────
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.modify",
]

REDIRECT_PORT  = 8888
REDIRECT_URI   = f"http://localhost:{REDIRECT_PORT}/callback"
MEMORY_DIR     = Path(os.getenv("MEMORY_DIR", "./memory"))
TOKEN_PATH     = MEMORY_DIR / "gmail_token.json"
CLIENT_SECRET  = MEMORY_DIR / "client_secret.json"

# ── OAuth flow factory ────────────────────────────────────────────────────────
def create_flow():
    from google_auth_oauthlib.flow import Flow

    if CLIENT_SECRET.exists():
        print(f"Using credentials from {CLIENT_SECRET}")
        return Flow.from_client_secrets_file(
            str(CLIENT_SECRET), scopes=SCOPES, redirect_uri=REDIRECT_URI
        )

    client_id     = os.getenv("GMAIL_CLIENT_ID", "")
    client_secret = os.getenv("GMAIL_CLIENT_SECRET", "")
    if not client_id or not client_secret:
        print("ERROR: Set GMAIL_CLIENT_ID + GMAIL_CLIENT_SECRET in .env")
        print("       or place client_secret.json in memory/")
        sys.exit(1)

    return Flow.from_client_config(
        {
            "web": {
                "client_id": client_id,
                "client_secret": client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [REDIRECT_URI],
            }
        },
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI,
    )


# ── Local callback server ─────────────────────────────────────────────────────
class _Handler(BaseHTTPRequestHandler):
    code  = None
    error = None

    def log_message(self, *args):
        pass  # silence default HTTP log

    def do_GET(self):
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)

        if params.get("error"):
            _Handler.error = params["error"][0]
            body = b"<h2>Authorization denied. You can close this tab.</h2>"
        elif params.get("code"):
            _Handler.code = params["code"][0]
            body = (
                b"<h2 style='font-family:sans-serif;color:green'>"
                b"Authorization successful! You can close this tab.</h2>"
            )
        else:
            body = b"<h2>Waiting...</h2>"

        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(body)


def _wait_for_code(timeout: int = 120) -> str:
    """Start a local HTTP server and block until the OAuth code arrives."""
    server = HTTPServer(("127.0.0.1", REDIRECT_PORT), _Handler)
    server.allow_reuse_address = True
    server.timeout = timeout

    print(f"  Listening on http://localhost:{REDIRECT_PORT}/callback ...")

    deadline = timeout
    while _Handler.code is None and _Handler.error is None and deadline > 0:
        server.handle_request()
        deadline -= 1

    server.server_close()

    if _Handler.error:
        print(f"\nERROR from Google: {_Handler.error}")
        sys.exit(1)
    if _Handler.code is None:
        print("\nTimed out waiting for authorization.")
        sys.exit(1)

    return _Handler.code


# ── Token exchange ────────────────────────────────────────────────────────────
def exchange_and_save(code: str):
    flow = create_flow()
    flow.fetch_token(code=code)
    creds = flow.credentials

    TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
    token_data = {
        "token":         creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri":     creds.token_uri,
        "client_id":     creds.client_id,
        "client_secret": creds.client_secret,
        "scopes":        list(creds.scopes or SCOPES),
    }
    TOKEN_PATH.write_text(json.dumps(token_data, indent=2), encoding="utf-8")
    print(f"\n  Token saved → {TOKEN_PATH.resolve()}")


# ── Open browser (WSL2-aware) ─────────────────────────────────────────────────
def open_browser(url: str):
    """Open URL in Windows browser from WSL2, fallback to webbrowser."""
    opened = False

    # WSL2: use Windows cmd.exe to open browser
    try:
        import subprocess
        result = subprocess.run(
            ["cmd.exe", "/c", "start", url],
            capture_output=True, timeout=5
        )
        if result.returncode == 0:
            opened = True
    except Exception:
        pass

    # Fallback: PowerShell
    if not opened:
        try:
            import subprocess
            subprocess.run(
                ["powershell.exe", "-Command", f"Start-Process '{url}'"],
                capture_output=True, timeout=5
            )
            opened = True
        except Exception:
            pass

    # Fallback: standard webbrowser
    if not opened:
        try:
            webbrowser.open(url)
            opened = True
        except Exception:
            pass

    return opened


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    # Handle --code flag (manual fallback)
    if len(sys.argv) >= 3 and sys.argv[1] == "--code":
        print("Exchanging provided code...")
        exchange_and_save(sys.argv[2])
        print("Gmail OAuth2 setup complete.")
        return

    # --callback URL flag (copy-paste fallback)
    if len(sys.argv) >= 3 and sys.argv[1] == "--callback":
        parsed = urlparse(sys.argv[2])
        params = parse_qs(parsed.query)
        code = params.get("code", [None])[0]
        if not code:
            print("ERROR: Could not extract 'code' from the callback URL.")
            sys.exit(1)
        exchange_and_save(code)
        print("Gmail OAuth2 setup complete.")
        return

    # ── Normal flow: auto server ──────────────────────────────────────────────
    flow = create_flow()
    auth_url, _ = flow.authorization_url(
        access_type="offline",
        prompt="consent",
    )

    print("\n" + "=" * 60)
    print("  Gmail OAuth2 Setup")
    print("=" * 60)
    print("\nOpening your browser for Google authorization...")
    print(f"\nIf the browser does NOT open automatically, open this URL manually:\n")
    print(f"  {auth_url}\n")

    # Open browser
    open_browser(auth_url)

    print("After you click Allow in the browser, authorization")
    print("completes automatically.\n")

    # Capture code via local server
    code = _wait_for_code(timeout=120)

    print("  Code received. Exchanging for tokens...")
    exchange_and_save(code)

    print("\n" + "=" * 60)
    print("  Gmail OAuth2 setup complete!")
    print("  The watcher will use the new token on next poll.")
    print("=" * 60 + "\n")

    # Force immediate watcher restart to pick up new token
    try:
        import subprocess
        subprocess.run(
            ["pkill", "-f", "watchers.src.main"],
            capture_output=True
        )
        subprocess.Popen(
            ["python3", "-m", "watchers.src.main"],
            cwd=str(Path(__file__).resolve().parent.parent),
            stdout=open("logs/watchers.log", "a"),
            stderr=subprocess.STDOUT,
        )
        print("  Watcher restarted with fresh credentials.")
    except Exception as e:
        print(f"  (Restart watcher manually: python3 -m watchers.src.main)")


if __name__ == "__main__":
    main()
