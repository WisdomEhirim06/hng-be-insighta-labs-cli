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

# Load secret environment variables
load_dotenv()

CREDENTIALS_PATH = os.path.expanduser("~/.insighta/credentials.json")
BACKEND_URL = os.getenv("INSIGHTA_BACKEND_URL", "https://hng14-be-intelligence-query.vercel.app")
CLIENT_ID = os.getenv("GITHUB_CLIENT_ID")

def save_credentials(data):
    os.makedirs(os.path.dirname(CREDENTIALS_PATH), exist_ok=True)
    with open(CREDENTIALS_PATH, "w") as f:
        json.dump(data, f)

def load_credentials():
    if os.path.exists(CREDENTIALS_PATH):
        with open(CREDENTIALS_PATH, "r") as f:
            return json.load(f)
    return None

def generate_pkce():
    code_verifier = secrets.token_urlsafe(64)
    code_challenge = base64.urlsafe_b64encode(
        hashlib.sha256(code_verifier.encode()).digest()
    ).decode().replace("=", "")
    return code_verifier, code_challenge

class CallbackHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        return  # Suppress logs

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(b"""
            <html><body style="font-family:sans-serif;text-align:center;padding:50px">
            <h1 style="color:green">&#10003; Login Successful!</h1>
            <p>You are now authenticated. You can close this window and return to your terminal.</p>
            </body></html>
        """)

        query = urlparse(self.path).query
        params = parse_qs(query)

        # Backend redirects back with tokens directly
        self.server.tokens = {
            "access_token": params.get("access_token", [None])[0],
            "refresh_token": params.get("refresh_token", [None])[0],
            "username": params.get("username", [None])[0],
            "role": params.get("role", [None])[0],
        }
        self.server.state = params.get("state", [None])[0]

def run_callback_server(port=8080):
    server = HTTPServer(("localhost", port), CallbackHandler)
    server.tokens = None
    server.state = None
    server.handle_request()
    return server.tokens, server.state

async def login():
    # CLI PKCE flow:
    # 1. We embed "cli:" prefix in state so the backend knows to redirect back to us
    # 2. GitHub redirects to the registered Vercel backend URL
    # 3. Backend sees "cli:" state and redirects to our local server with tokens
    raw_state = secrets.token_urlsafe(16)
    state = f"cli:{raw_state}"
    code_verifier, code_challenge = generate_pkce()

    # Do NOT include redirect_uri — use the registered Vercel callback
    # Do NOT include code_challenge — the backend does the exchange (not the CLI),
    # so the verifier cannot be passed through. State-based CSRF protection is used instead.
    auth_url = (
        f"https://github.com/login/oauth/authorize?client_id={CLIENT_ID}"
        f"&state={state}&scope=read:user%20user:email"
    )

    print(f"Opening browser for GitHub login...")
    print(f"Waiting for authentication...")
    webbrowser.open(auth_url)

    # Wait for backend to redirect back to our local server with tokens
    tokens, received_state = run_callback_server(8080)

    if not tokens:
        print("Error: Did not receive tokens from backend.")
        return None

    if received_state != state:
        print("Error: State mismatch — possible CSRF attack.")
        return None

    save_credentials(tokens)
    return tokens

def logout():
    if os.path.exists(CREDENTIALS_PATH):
        os.remove(CREDENTIALS_PATH)
    print("Logged out successfully.")

async def get_valid_token():
    creds = load_credentials()
    if not creds:
        return None
    
    # Check if token is expired (access tokens expire in 3 minutes)
    # For now, let's just try to use it and refresh if it fails 401
    # or implement a simple time check if we stored 'expires_at'
    return creds.get("access_token")

async def refresh_tokens_cli():
    creds = load_credentials()
    if not creds or "refresh_token" not in creds:
        return None
    
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{BACKEND_URL}/auth/refresh",
            json={"refresh_token": creds["refresh_token"]}
        )
        if resp.status_code == 200:
            new_creds = resp.json()
            save_credentials(new_creds)
            return new_creds["access_token"]
    return None
