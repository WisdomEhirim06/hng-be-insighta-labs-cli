import os
import json
import hashlib
import base64
import secrets
import webbrowser
import httpx
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs
from dotenv import load_dotenv

load_dotenv()

CREDENTIALS_PATH = os.path.expanduser("~/.insighta/credentials.json")
BACKEND_URL = os.getenv("INSIGHTA_BACKEND_URL", "https://hng14-be-intelligence-query.vercel.app")
CLIENT_ID = os.getenv("GITHUB_CLIENT_ID")

# The local redirect URI must match what is registered in the GitHub OAuth app settings.
# The backend callback proxies the code back here for CLI flows.
CLI_REDIRECT_URI = "http://localhost:8080/callback"


def save_credentials(data: dict):
    os.makedirs(os.path.dirname(CREDENTIALS_PATH), exist_ok=True)
    with open(CREDENTIALS_PATH, "w") as f:
        json.dump(data, f)


def load_credentials():
    if os.path.exists(CREDENTIALS_PATH):
        with open(CREDENTIALS_PATH, "r") as f:
            return json.load(f)
    return None


def generate_pkce():
    """Generate a PKCE code_verifier and its SHA-256 derived code_challenge."""
    code_verifier = secrets.token_urlsafe(64)
    code_challenge = base64.urlsafe_b64encode(
        hashlib.sha256(code_verifier.encode()).digest()
    ).decode().replace("=", "")
    return code_verifier, code_challenge


class CallbackHandler(BaseHTTPRequestHandler):
    """Handles the GitHub OAuth redirect back to the CLI's local server.

    The backend proxies the raw `code` and `state` here so the CLI can
    complete the PKCE exchange itself via POST /auth/github/exchange.
    """

    def log_message(self, format, *args):
        return  # suppress default request logs

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(b"""
            <html><body style="font-family:sans-serif;text-align:center;padding:50px">
            <h1 style="color:green">&#10003; Authorization received!</h1>
            <p>Return to your terminal to complete login. You can close this window.</p>
            </body></html>
        """)

        query = urlparse(self.path).query
        params = parse_qs(query)

        # Backend redirects back with ?code=...&state=... for CLI flows
        self.server.code = params.get("code", [None])[0]
        self.server.state = params.get("state", [None])[0]


def run_callback_server(port=8080):
    """Start a one-shot HTTP server to capture the OAuth code from GitHub."""
    server = HTTPServer(("localhost", port), CallbackHandler)
    server.code = None
    server.state = None
    server.handle_request()
    return server.code, server.state


async def login():
    """Full PKCE login flow:

    1. Generate state + PKCE pair.
    2. Open GitHub OAuth with code_challenge in the URL.
    3. Backend proxies the code back to localhost:8080/callback.
    4. CLI captures code, validates state.
    5. CLI sends code + code_verifier to /auth/github/exchange.
    6. Backend exchanges, creates/updates user, returns tokens.
    7. CLI stores tokens locally.
    """
    raw_state = secrets.token_urlsafe(16)
    state = f"cli:{raw_state}"
    code_verifier, code_challenge = generate_pkce()

    # Include code_challenge (S256) so backends/providers that support PKCE can verify it.
    # The redirect_uri is NOT set here — the registered Vercel backend callback handles
    # the GitHub redirect and then proxies the code back to our local server.
    auth_url = (
        f"https://github.com/login/oauth/authorize"
        f"?client_id={CLIENT_ID}"
        f"&state={state}"
        f"&scope=read:user%20user:email"
        f"&code_challenge={code_challenge}"
        f"&code_challenge_method=S256"
    )

    print("Opening browser for GitHub login...")
    print("Waiting for authentication...")
    webbrowser.open(auth_url)

    # Wait for the backend to proxy the code back to our local server
    received_code, received_state = run_callback_server(8080)

    if not received_code:
        print("Error: Did not receive authorization code.")
        return None

    if received_state != state:
        print("Error: State mismatch — possible CSRF attack.")
        return None

    # Exchange the code + code_verifier with the backend
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{BACKEND_URL}/auth/github/exchange",
            json={
                "code": received_code,
                "code_verifier": code_verifier,
            },
        )

    if resp.status_code != 200:
        print(f"Error: Token exchange failed ({resp.status_code}): {resp.text}")
        return None

    tokens = resp.json()
    save_credentials(tokens)
    return tokens


def logout():
    """Invalidate the refresh token server-side and remove local credentials."""
    creds = load_credentials()
    if creds and creds.get("refresh_token"):
        import asyncio

        async def _revoke():
            async with httpx.AsyncClient() as client:
                await client.post(
                    f"{BACKEND_URL}/auth/logout",
                    json={"refresh_token": creds["refresh_token"]},
                )

        asyncio.run(_revoke())

    if os.path.exists(CREDENTIALS_PATH):
        os.remove(CREDENTIALS_PATH)
    print("Logged out successfully.")


async def get_valid_token():
    """Return the stored access token (callers refresh on 401)."""
    creds = load_credentials()
    if not creds:
        return None
    return creds.get("access_token")


async def refresh_tokens_cli():
    """Rotate the refresh token and update local credentials.

    Only the token fields are overwritten so that username and role are preserved.
    """
    creds = load_credentials()
    if not creds or "refresh_token" not in creds:
        return None

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{BACKEND_URL}/auth/refresh",
            json={"refresh_token": creds["refresh_token"]},
        )

    if resp.status_code == 200:
        new_data = resp.json()
        creds["access_token"] = new_data["access_token"]
        creds["refresh_token"] = new_data["refresh_token"]
        save_credentials(creds)
        return creds["access_token"]

    return None
