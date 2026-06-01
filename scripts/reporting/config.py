"""
Reporting — Config and Credential Loader

Loads reporting-clients.yaml and provides credential helpers
and period calculation utilities used across all reporting scripts.
"""

import os
import sys
import yaml
from datetime import date, timedelta
from calendar import monthrange
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent

# Ensure scripts/ is on path for db imports
sys.path.insert(0, str(WORKSPACE_ROOT / "scripts"))

from dotenv import load_dotenv
load_dotenv(WORKSPACE_ROOT / ".env", override=True)


def load_clients():
    """Load all clients from config/reporting-clients.yaml."""
    path = WORKSPACE_ROOT / "config" / "reporting-clients.yaml"
    with open(path) as f:
        return yaml.safe_load(f)["clients"]


def get_client_by_slug(slug):
    """Return a single client dict by slug, or None."""
    return next((c for c in load_clients() if c["slug"] == slug), None)


def last_month_period():
    """Return the previous month as 'YYYY-MM'."""
    first = date.today().replace(day=1)
    last = first - timedelta(days=1)
    return last.strftime("%Y-%m")


def period_dates(period):
    """Return (start_date, end_date) as 'YYYY-MM-DD' strings for a 'YYYY-MM' period."""
    year, month = map(int, period.split("-"))
    _, last_day = monthrange(year, month)
    return f"{year}-{month:02d}-01", f"{year}-{month:02d}-{last_day:02d}"


def period_label(period):
    """Human-readable month label: '2026-04' → 'April 2026'."""
    year, month = map(int, period.split("-"))
    names = [
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December",
    ]
    return f"{names[month - 1]} {year}"


def get_creds():
    """Return all relevant API credentials from environment."""
    return {
        "google_ads_developer_token": os.getenv("GOOGLE_ADS_DEVELOPER_TOKEN", "").strip(),
        "google_ads_mcc_id": os.getenv("GOOGLE_ADS_MCC_ID", "").strip().replace("-", ""),
        "google_ads_client_id": os.getenv("GOOGLE_ADS_CLIENT_ID", "").strip(),
        "google_ads_client_secret": os.getenv("GOOGLE_ADS_CLIENT_SECRET", "").strip(),
        "google_ads_refresh_token": os.getenv("GOOGLE_ADS_REFRESH_TOKEN", "").strip(),
        "meta_access_token": os.getenv("META_ACCESS_TOKEN", "").strip(),
        "anthropic_api_key": os.getenv("ANTHROPIC_API_KEY", "").strip(),
    }
