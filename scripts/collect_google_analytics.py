"""
DataOS — Google Analytics (GA4) Collector

Collects daily website traffic from GA4 using OAuth credentials.
Pulls yesterday's sessions, users, page views, engagement, and traffic sources.

Requires:
    credentials/ga4_tokens.json — run ga4_auth.py once to create this
    GA4_PROPERTY_ID             — in .env

Tables created: ga4_daily, ga4_sources
"""

import json
import os
import sqlite3
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests
from dotenv import load_dotenv

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(WORKSPACE_ROOT / ".env")

TOKENS_PATH = WORKSPACE_ROOT / "credentials" / "ga4_tokens.json"
TOKEN_URL   = "https://oauth2.googleapis.com/token"


# --- Token management ---

def load_tokens():
    if not TOKENS_PATH.exists():
        return None
    return json.loads(TOKENS_PATH.read_text())


def save_tokens(tokens):
    TOKENS_PATH.write_text(json.dumps(tokens, indent=2))


def refresh_if_needed(tokens):
    expires_at = datetime.fromisoformat(tokens["expires_at"])
    if expires_at - datetime.now(timezone.utc) > timedelta(minutes=5):
        return tokens

    r = requests.post(TOKEN_URL, data={
        "grant_type":    "refresh_token",
        "refresh_token": tokens["refresh_token"],
        "client_id":     tokens["client_id"],
        "client_secret": tokens["client_secret"],
    }, timeout=15)
    r.raise_for_status()
    data = r.json()

    tokens["access_token"] = data["access_token"]
    tokens["expires_at"] = (
        datetime.now(timezone.utc) + timedelta(seconds=data.get("expires_in", 3600))
    ).isoformat()
    save_tokens(tokens)
    return tokens


# --- GA4 API ---

def run_report(access_token, property_id, payload):
    url = f"https://analyticsdata.googleapis.com/v1beta/properties/{property_id}:runReport"
    r = requests.post(url, json=payload, headers={
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }, timeout=30)
    r.raise_for_status()
    return r.json()


# --- Collector ---

def collect():
    if not TOKENS_PATH.exists():
        return {
            "source": "google_analytics", "status": "skipped",
            "reason": "Not authenticated — run: python scripts/ga4_auth.py"
        }

    property_id = os.getenv("GA4_PROPERTY_ID", "").strip()
    if not property_id:
        return {
            "source": "google_analytics", "status": "skipped",
            "reason": "Missing GA4_PROPERTY_ID in .env"
        }

    try:
        tokens = refresh_if_needed(load_tokens())
    except Exception as e:
        return {"source": "google_analytics", "status": "error", "reason": f"Token refresh failed: {e}"}

    yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")

    try:
        # Overview metrics
        overview_resp = run_report(tokens["access_token"], property_id, {
            "dateRanges": [{"startDate": yesterday, "endDate": yesterday}],
            "metrics": [
                {"name": "sessions"},
                {"name": "totalUsers"},
                {"name": "newUsers"},
                {"name": "screenPageViews"},
                {"name": "averageSessionDuration"},
                {"name": "bounceRate"},
                {"name": "engagementRate"},
            ],
        })

        overview = {}
        if overview_resp.get("rows"):
            headers = [h["name"] for h in overview_resp["metricHeaders"]]
            values  = [v["value"] for v in overview_resp["rows"][0]["metricValues"]]
            overview = dict(zip(headers, values))

        # Traffic sources
        sources_resp = run_report(tokens["access_token"], property_id, {
            "dateRanges": [{"startDate": yesterday, "endDate": yesterday}],
            "dimensions": [{"name": "sessionSource"}, {"name": "sessionMedium"}],
            "metrics":    [{"name": "sessions"}, {"name": "totalUsers"}],
            "orderBys":   [{"metric": {"metricName": "sessions"}, "desc": True}],
            "limit": 20,
        })

        sources = []
        for row in sources_resp.get("rows", []):
            sources.append({
                "source":   row["dimensionValues"][0]["value"],
                "medium":   row["dimensionValues"][1]["value"],
                "sessions": row["metricValues"][0]["value"],
                "users":    row["metricValues"][1]["value"],
            })

        return {
            "source": "google_analytics",
            "status": "success",
            "data": {
                "date":        yesterday,
                "property_id": property_id,
                "overview":    overview,
                "sources":     sources,
            }
        }

    except Exception as e:
        return {"source": "google_analytics", "status": "error", "reason": str(e)}


# --- Database write ---

def write(conn, result, date):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ga4_daily (
            date TEXT PRIMARY KEY,
            sessions INTEGER,
            total_users INTEGER,
            new_users INTEGER,
            page_views INTEGER,
            avg_session_duration REAL,
            bounce_rate REAL,
            engagement_rate REAL,
            collected_at TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ga4_sources (
            date TEXT NOT NULL,
            source TEXT NOT NULL,
            medium TEXT NOT NULL,
            sessions INTEGER,
            users INTEGER,
            PRIMARY KEY (date, source, medium)
        )
    """)

    if result.get("status") != "success":
        conn.commit()
        return 0

    data        = result["data"]
    ov          = data["overview"]
    record_date = data["date"]
    collected_at = datetime.now(timezone.utc).isoformat()

    def safe_int(v):
        try: return int(float(v))
        except: return None

    def safe_float(v):
        try: return float(v)
        except: return None

    conn.execute(
        "INSERT OR REPLACE INTO ga4_daily "
        "(date, sessions, total_users, new_users, page_views, "
        "avg_session_duration, bounce_rate, engagement_rate, collected_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (record_date, safe_int(ov.get("sessions")),
         safe_int(ov.get("totalUsers")), safe_int(ov.get("newUsers")),
         safe_int(ov.get("screenPageViews")),
         safe_float(ov.get("averageSessionDuration")),
         safe_float(ov.get("bounceRate")),
         safe_float(ov.get("engagementRate")), collected_at)
    )
    records = 1

    for src in data.get("sources", []):
        conn.execute(
            "INSERT OR REPLACE INTO ga4_sources "
            "(date, source, medium, sessions, users) VALUES (?, ?, ?, ?, ?)",
            (record_date, src["source"], src["medium"],
             safe_int(src["sessions"]), safe_int(src["users"]))
        )
        records += 1

    conn.commit()
    return records


if __name__ == "__main__":
    result = collect()
    if result["status"] == "success":
        ov = result["data"]["overview"]
        print(f"GA4 connected! Data for {result['data']['date']}:")
        print(f"  Sessions:   {ov.get('sessions', 'N/A')}")
        print(f"  Users:      {ov.get('totalUsers', 'N/A')}")
        print(f"  Page views: {ov.get('screenPageViews', 'N/A')}")
        print(f"  Engagement: {float(ov.get('engagementRate', 0))*100:.1f}%")
        print(f"  Sources:    {len(result['data']['sources'])} traffic sources")
    else:
        print(f"{result['status']}: {result.get('reason', '')}")
