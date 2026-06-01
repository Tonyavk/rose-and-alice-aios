"""
Reporting — Campaign Types Reader

Reads Meta and Google campaign type descriptions from the ads Google Sheet
(same sheet that holds account IDs). Matches rows to client slugs and returns
a dict used by the report generator to give Claude campaign intent context.

Returns: {slug: {"meta": "Lead Gen, Retargeting", "google": "Search - Lead Gen"}, ...}
"""

import re
import csv
import unicodedata
import io
import sys
import requests
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(WORKSPACE_ROOT / "scripts" / "reporting"))

# Ads Google Sheet ID (the one with account IDs + campaign types)
ADS_SHEET_ID = "1CdxFIKqaWu5jXY_Pk6iB3sYKA44ichRl6FmHSVBz4yE"


def _normalize(name: str) -> str:
    """Lowercase, strip accents, remove all non-alphanumeric chars for fuzzy matching."""
    nfkd = unicodedata.normalize("NFKD", str(name))
    ascii_str = nfkd.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]", "", ascii_str.lower())


def load(sheet_id: str = ADS_SHEET_ID) -> dict:
    """
    Fetch the ads sheet and return campaign types keyed by client slug.
    Silently returns an empty dict if the sheet is unavailable.
    """
    from config import load_clients

    # Fetch sheet as CSV (public sheet, no auth needed)
    try:
        resp = requests.get(
            f"https://docs.google.com/spreadsheets/d/{sheet_id}/export",
            params={"format": "csv", "gid": "0"},
            timeout=15,
            allow_redirects=True,
        )
        if not resp.ok:
            print(f"  Warning: Campaign types sheet unavailable (HTTP {resp.status_code})")
            return {}
        content = resp.content.decode("utf-8")
    except Exception as e:
        print(f"  Warning: Could not fetch campaign types sheet — {e}")
        return {}

    # Parse CSV properly (handles commas inside quoted fields)
    reader = csv.reader(io.StringIO(content))
    rows = list(reader)
    if len(rows) < 2:
        return {}

    # Build lookup: normalized_company_name → {meta, google, meta_level}
    sheet_lookup = {}
    for row in rows[1:]:  # skip header
        if not row:
            continue
        company       = row[0].strip() if len(row) > 0 else ""
        meta_types    = row[4].strip() if len(row) > 4 else ""
        google_types  = row[5].strip() if len(row) > 5 else ""
        meta_level    = row[6].strip().lower() if len(row) > 6 else ""
        if company:
            sheet_lookup[_normalize(company)] = {
                "meta":       meta_types,
                "google":     google_types,
                "meta_level": "adset" if meta_level == "adset" else "campaign",
            }

    # Match sheet rows to YAML client slugs
    result = {}
    for client in load_clients():
        key = _normalize(client["name"])
        if key in sheet_lookup:
            entry = sheet_lookup[key]
            if entry["meta"] or entry["google"] or entry["meta_level"] == "adset":
                result[client["slug"]] = entry

    return result


if __name__ == "__main__":
    data = load()
    if data:
        print(f"Campaign types loaded for {len(data)} client(s):")
        for slug, types in data.items():
            print(f"  {slug}")
            if types["meta"]:
                print(f"    Meta:   {types['meta']}")
            if types["google"]:
                print(f"    Google: {types['google']}")
    else:
        print("No campaign types found — check the sheet has columns E and F filled in.")
