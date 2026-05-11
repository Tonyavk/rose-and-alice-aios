"""
DataOS — Google Analytics (GA4) Authentication Setup (run once)

Walks you through connecting your Google Analytics account.
Stores tokens in credentials/ga4_tokens.json for daily use.

Usage:
    python scripts/ga4_auth.py
"""

import json
import os
import secrets
import urllib.parse
import webbrowser
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests
from dotenv import load_dotenv

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(WORKSPACE_ROOT / ".env")

CLIENT_FILE  = WORKSPACE_ROOT / "credentials" / "ga4_oauth_client.json"
TOKENS_PATH  = WORKSPACE_ROOT / "credentials" / "ga4_tokens.json"
REDIRECT_URI = "http://localhost"
SCOPES       = "https://www.googleapis.com/auth/analytics.readonly"

TOKEN_URL    = "https://oauth2.googleapis.com/token"
AUTH_URL     = "https://accounts.google.com/o/oauth2/v2/auth"


def load_client():
    data = json.loads(CLIENT_FILE.read_text())
    creds = data.get("installed") or data.get("web")
    return creds["client_id"], creds["client_secret"]


def get_auth_url(client_id, state):
    params = {
        "client_id":     client_id,
        "redirect_uri":  REDIRECT_URI,
        "response_type": "code",
        "scope":         SCOPES,
        "access_type":   "offline",
        "prompt":        "consent",
        "state":         state,
    }
    return AUTH_URL + "?" + urllib.parse.urlencode(params)


def exchange_code(client_id, client_secret, code):
    r = requests.post(TOKEN_URL, data={
        "code":          code,
        "client_id":     client_id,
        "client_secret": client_secret,
        "redirect_uri":  REDIRECT_URI,
        "grant_type":    "authorization_code",
    }, timeout=15)
    r.raise_for_status()
    return r.json()


def save_tokens(token_data, client_id, client_secret):
    expires_at = (
        datetime.now(timezone.utc) + timedelta(seconds=token_data.get("expires_in", 3600))
    ).isoformat()
    payload = {
        "access_token":  token_data["access_token"],
        "refresh_token": token_data["refresh_token"],
        "expires_at":    expires_at,
        "client_id":     client_id,
        "client_secret": client_secret,
    }
    TOKENS_PATH.write_text(json.dumps(payload, indent=2))
    print(f"Tokens saved to: {TOKENS_PATH}")


def main():
    if not CLIENT_FILE.exists():
        print("ERROR: credentials/ga4_oauth_client.json not found")
        return

    client_id, client_secret = load_client()
    state = secrets.token_urlsafe(16)
    url   = get_auth_url(client_id, state)

    print("\n=== Google Analytics Authentication Setup ===\n")
    print("Opening Google login in your browser...")
    print("Sign in with the Google account that owns your GA4 property.\n")
    webbrowser.open(url)

    print("Step 2: After approving access you'll land on a page that can't connect.")
    print("        That's normal. Copy the full URL from the address bar and paste it below.\n")

    raw = input("Paste the full URL here:\n> ").strip()

    parsed = urllib.parse.urlparse(raw)
    params = urllib.parse.parse_qs(parsed.query)

    if "code" not in params:
        print("\nERROR: No authorisation code found in that URL.")
        print("Make sure you copied the full URL from the address bar after approving access.")
        return

    code = params["code"][0]
    print("\nExchanging code for tokens...")

    try:
        token_data = exchange_code(client_id, client_secret, code)
    except Exception as e:
        print(f"ERROR: {e}")
        return

    if "refresh_token" not in token_data:
        print("ERROR: No refresh token received. Try running the script again.")
        return

    save_tokens(token_data, client_id, client_secret)
    print("\nSuccess! Google Analytics is connected.")
    print("You can now run: python scripts/collect.py --sources google_analytics")


if __name__ == "__main__":
    main()
