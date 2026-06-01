"""
Meta Token Refresh
Exchanges the current META_ACCESS_TOKEN for a fresh 60-day token.
Reads from .env, updates it in place, and logs the result.

Run manually:    python3 scripts/refresh_meta_token.py
Scheduled:       Monthly via LaunchAgent (com.aios.meta-token-refresh.plist)
"""

import os
import re
import sys
import requests
from datetime import datetime, timezone
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = WORKSPACE_ROOT / ".env"

sys.path.insert(0, str(WORKSPACE_ROOT / "scripts"))
from dotenv import load_dotenv
load_dotenv(ENV_PATH)


def refresh_token():
    app_id     = os.getenv("META_APP_ID")
    app_secret = os.getenv("META_APP_SECRET")
    old_token  = os.getenv("META_ACCESS_TOKEN")

    if not all([app_id, app_secret, old_token]):
        print("Error: META_APP_ID, META_APP_SECRET or META_ACCESS_TOKEN missing from .env")
        sys.exit(1)

    print("Refreshing Meta access token...")

    resp = requests.get(
        "https://graph.facebook.com/v19.0/oauth/access_token",
        params={
            "grant_type":        "fb_exchange_token",
            "client_id":         app_id,
            "client_secret":     app_secret,
            "fb_exchange_token": old_token,
        },
        timeout=15,
    )

    if not resp.ok:
        print(f"Error: Meta API returned {resp.status_code}")
        print(resp.text)
        sys.exit(1)

    data = resp.json()
    new_token = data.get("access_token")

    if not new_token:
        print(f"Error: No access_token in response: {data}")
        sys.exit(1)

    # Update .env in place — replace the META_ACCESS_TOKEN line
    env_text = ENV_PATH.read_text()
    env_text = re.sub(
        r"^META_ACCESS_TOKEN=.*$",
        f"META_ACCESS_TOKEN={new_token}",
        env_text,
        flags=re.MULTILINE,
    )
    ENV_PATH.write_text(env_text)

    expires_in = data.get("expires_in", "unknown")
    timestamp  = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    print(f"  Token refreshed successfully at {timestamp}")
    print(f"  Expires in: {expires_in} seconds (~{int(expires_in) // 86400} days)" if isinstance(expires_in, int) else f"  Expires in: {expires_in}")


if __name__ == "__main__":
    refresh_token()
