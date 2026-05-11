"""
DataOS — Xero Authentication Setup (run once)

Walks you through connecting your Xero account.
Stores tokens in credentials/xero_tokens.json for daily use.

Usage:
    python scripts/xero_auth.py
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

TOKENS_PATH = WORKSPACE_ROOT / "credentials" / "xero_tokens.json"
TOKENS_PATH.parent.mkdir(exist_ok=True)

CLIENT_ID     = os.getenv("XERO_CLIENT_ID", "").strip()
CLIENT_SECRET = os.getenv("XERO_CLIENT_SECRET", "").strip()
REDIRECT_URI  = "https://localhost"
SCOPES        = "offline_access accounting.invoices.read accounting.contacts.read accounting.payments.read"

AUTH_URL   = "https://login.xero.com/identity/connect/authorize"
TOKEN_URL  = "https://identity.xero.com/connect/token"
CONNS_URL  = "https://api.xero.com/connections"


def get_auth_url(state):
    params = {
        "response_type": "code",
        "client_id":     CLIENT_ID,
        "redirect_uri":  REDIRECT_URI,
        "scope":         SCOPES,
        "state":         state,
    }
    return AUTH_URL + "?" + urllib.parse.urlencode(params)


def exchange_code(code):
    r = requests.post(TOKEN_URL, data={
        "grant_type":    "authorization_code",
        "code":          code,
        "redirect_uri":  REDIRECT_URI,
        "client_id":     CLIENT_ID,
        "client_secret": CLIENT_SECRET,
    }, timeout=15)
    r.raise_for_status()
    return r.json()


def get_tenant_id(access_token):
    r = requests.get(CONNS_URL, headers={
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
    }, timeout=15)
    r.raise_for_status()
    connections = r.json()
    if not connections:
        raise ValueError("No Xero organisations found — make sure you approved access during login.")
    return connections[0]["tenantId"], connections[0]["tenantName"]


def save_tokens(token_data, tenant_id, tenant_name):
    expires_at = (
        datetime.now(timezone.utc) + timedelta(seconds=token_data["expires_in"])
    ).isoformat()
    payload = {
        "access_token":  token_data["access_token"],
        "refresh_token": token_data["refresh_token"],
        "expires_at":    expires_at,
        "tenant_id":     tenant_id,
        "tenant_name":   tenant_name,
    }
    TOKENS_PATH.write_text(json.dumps(payload, indent=2))
    print(f"Tokens saved to: {TOKENS_PATH}")


def main():
    if not CLIENT_ID or not CLIENT_SECRET:
        print("ERROR: XERO_CLIENT_ID or XERO_CLIENT_SECRET not found in .env")
        return

    print("\n=== Xero Authentication Setup ===\n")

    state = secrets.token_urlsafe(16)
    url   = get_auth_url(state)

    print("Step 1: Opening Xero login in your browser...")
    print(f"        If it doesn't open, copy this URL manually:\n        {url}\n")
    webbrowser.open(url)

    print("Step 2: Log in to Xero and click 'Allow Access'.")
    print("        You'll land on a page that shows a certificate warning —")
    print("        that's normal. Look at the address bar and copy the FULL URL.\n")

    raw = input("Step 3: Paste the full URL from your browser here:\n> ").strip()

    parsed = urllib.parse.urlparse(raw)
    params = urllib.parse.parse_qs(parsed.query)

    if "code" not in params:
        print("\nERROR: Could not find an authorisation code in that URL.")
        print("Make sure you copied the full URL from the address bar after approving access.")
        return

    code = params["code"][0]
    print("\nExchanging code for tokens...")

    try:
        token_data = exchange_code(code)
    except Exception as e:
        print(f"ERROR exchanging code: {e}")
        return

    print("Getting your organisation details...")
    try:
        tenant_id, tenant_name = get_tenant_id(token_data["access_token"])
    except Exception as e:
        print(f"ERROR getting organisation: {e}")
        return

    save_tokens(token_data, tenant_id, tenant_name)

    print(f"\nSuccess! Connected to: {tenant_name}")
    print("You can now run: python scripts/collect.py --sources xero")


if __name__ == "__main__":
    main()
