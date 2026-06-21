"""
Reporting — Meta Ads Monthly Collector

Pulls campaign-level insights from the Meta Marketing API for each client
configured in config/reporting-clients.yaml for a given month.

Tables: meta_campaign_monthly
Usage:
    python scripts/reporting/collect_meta.py              # Last month
    python scripts/reporting/collect_meta.py --period 2026-04
"""

import sys
import argparse
import requests
from datetime import datetime, timezone
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(WORKSPACE_ROOT / "scripts"))
sys.path.insert(0, str(WORKSPACE_ROOT / "scripts" / "reporting"))

from dotenv import load_dotenv
load_dotenv(WORKSPACE_ROOT / ".env", override=True)

from config import load_clients, last_month_period, period_dates, get_creds

META_API_BASE = "https://graph.facebook.com/v19.0"

# Conversion action types to extract from the 'actions' field
PURCHASE_ACTIONS = {
    "offsite_conversion.fb_pixel_purchase",
    "purchase",
    "omni_purchase",
}
LEAD_ACTIONS = {
    "lead",
    "offsite_conversion.fb_pixel_lead",
    "onsite_conversion.lead_grouped",
}


def _fetch_insights(account_id, access_token, start_date, end_date, level="campaign"):
    """Pull campaign insights from the Meta Marketing API."""
    url = f"{META_API_BASE}/act_{account_id}/insights"
    fields = "campaign_id,campaign_name,reach,impressions,clicks,spend,ctr,cpc,actions,action_values"
    if level == "adset":
        fields = "campaign_id,campaign_name,adset_id,adset_name," + fields.split(",", 2)[2]
    params = {
        "access_token": access_token,
        "level": level,
        "fields": fields,
        "time_range": f'{{"since":"{start_date}","until":"{end_date}"}}',
        "limit": 500,
    }

    r = requests.get(url, params=params, timeout=30)
    r.raise_for_status()
    raw = r.json()

    campaigns = []
    for row in raw.get("data", []):
        spend = float(row.get("spend", 0) or 0)
        reach = int(row.get("reach", 0) or 0)
        impressions = int(row.get("impressions", 0) or 0)
        clicks = int(row.get("clicks", 0) or 0)
        ctr = float(row.get("ctr", 0) or 0)
        cpc = float(row.get("cpc", 0) or 0)

        actions = row.get("actions", []) or []
        action_values = row.get("action_values", []) or []

        purchases = sum(
            float(a["value"]) for a in actions if a["action_type"] in PURCHASE_ACTIONS
        )
        leads = sum(
            float(a["value"]) for a in actions if a["action_type"] in LEAD_ACTIONS
        )
        landing_page_views = sum(
            float(a["value"]) for a in actions if a["action_type"] == "landing_page_view"
        )
        purchase_value = sum(
            float(a["value"]) for a in action_values if a["action_type"] in PURCHASE_ACTIONS
        )

        if purchases > 0:
            results = purchases
            result_type = "purchases"
        elif leads > 0:
            results = leads
            result_type = "leads"
        else:
            results = 0
            result_type = "other"

        roas = round(purchase_value / spend, 2) if spend > 0 and purchase_value > 0 else 0

        entry = {
            "campaign_id":   row.get("campaign_id", ""),
            "campaign_name": row.get("campaign_name", ""),
            "adset_id":      row.get("adset_id", ""),
            "adset_name":    row.get("adset_name", ""),
            "reach":         reach,
            "impressions":   impressions,
            "clicks":        clicks,
            "spend":         round(spend, 2),
            "ctr":           round(ctr, 2),
            "cpc":           round(cpc, 2),
            "results":       int(results),
            "landing_page_views": int(landing_page_views),
            "result_type":   result_type,
            "purchase_value": round(purchase_value, 2),
            "roas":          roas,
        }
        campaigns.append(entry)

    return campaigns


def collect(period=None):
    """
    Collect Meta Ads monthly data for all configured clients.

    Returns:
        {"status": "success", "period": ..., "data": {slug: [campaigns]}, "errors": [...]}
    """
    creds = get_creds()
    if not creds["meta_access_token"]:
        return {"status": "skipped", "reason": "Missing META_ACCESS_TOKEN in .env"}

    if period is None:
        period = last_month_period()

    start_date, end_date = period_dates(period)
    clients = [c for c in load_clients() if "meta" in c.get("platforms", {})]

    results = {}
    errors = []

    from collect_campaign_types import load as load_campaign_types
    campaign_types = load_campaign_types()

    for client in clients:
        slug = client["slug"]
        account_id = client["platforms"]["meta"]["account_id"]
        level = campaign_types.get(slug, {}).get("meta_level", "campaign")
        # Brand reports always report at ad-set level
        if client.get("report_type") == "brand":
            level = "adset"
        try:
            campaigns = _fetch_insights(account_id, creds["meta_access_token"], start_date, end_date, level)
            results[slug] = {"data": campaigns, "level": level}
        except Exception as e:
            errors.append(f"{slug}: {e}")

    return {
        "status": "success",
        "period": period,
        "start_date": start_date,
        "end_date": end_date,
        "data": results,
        "errors": errors,
    }


def write(conn, result, period):
    """Write collected Meta data to the database (campaign or adset level)."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS meta_campaign_monthly (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            period TEXT NOT NULL,
            client_slug TEXT NOT NULL,
            campaign_id TEXT,
            campaign_name TEXT,
            adset_id TEXT,
            adset_name TEXT,
            reach INTEGER,
            impressions INTEGER,
            clicks INTEGER,
            spend REAL,
            ctr REAL,
            cpc REAL,
            results INTEGER,
            landing_page_views INTEGER,
            result_type TEXT,
            purchase_value REAL,
            roas REAL,
            reporting_level TEXT DEFAULT 'campaign',
            collected_at TEXT,
            UNIQUE(period, client_slug, campaign_id, adset_id)
        )
    """)
    # Migrate existing tables
    for col, typedef in [
        ("adset_id", "TEXT"),
        ("adset_name", "TEXT"),
        ("reach", "INTEGER"),
        ("landing_page_views", "INTEGER"),
        ("reporting_level", "TEXT DEFAULT 'campaign'"),
    ]:
        try:
            conn.execute(f"ALTER TABLE meta_campaign_monthly ADD COLUMN {col} {typedef}")
        except Exception:
            pass

    if result.get("status") != "success":
        conn.commit()
        return 0

    collected_at = datetime.now(timezone.utc).isoformat()
    records = 0

    for slug, client_result in result["data"].items():
        campaigns = client_result["data"]
        level     = client_result["level"]
        # Clear prior rows for this client/period so a level switch
        # (campaign ↔ adset) can't leave stale, double-counted rows behind.
        conn.execute(
            "DELETE FROM meta_campaign_monthly WHERE period = ? AND client_slug = ?",
            (period, slug),
        )
        for c in campaigns:
            conn.execute(
                "INSERT OR REPLACE INTO meta_campaign_monthly "
                "(period, client_slug, campaign_id, campaign_name, adset_id, adset_name, "
                "reach, impressions, clicks, spend, ctr, cpc, results, landing_page_views, result_type, "
                "purchase_value, roas, reporting_level, collected_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (period, slug, c["campaign_id"], c["campaign_name"],
                 c.get("adset_id", ""), c.get("adset_name", ""),
                 c.get("reach", 0), c["impressions"], c["clicks"], c["spend"], c["ctr"],
                 c["cpc"], c["results"], c.get("landing_page_views", 0), c["result_type"],
                 c["purchase_value"], c["roas"], level, collected_at),
            )
            records += 1

    conn.commit()
    return records


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Collect Meta Ads monthly data")
    parser.add_argument("--period", default=None, help="YYYY-MM (default: last month)")
    args = parser.parse_args()

    result = collect(args.period)
    if result["status"] == "success":
        for slug, campaigns in result["data"].items():
            total_spend = sum(c["spend"] for c in campaigns)
            total_impr = sum(c["impressions"] for c in campaigns)
            total_clicks = sum(c["clicks"] for c in campaigns)
            print(f"\n{slug}  ({len(campaigns)} campaigns | {total_impr:,} impr | "
                  f"{total_clicks:,} clicks | ${total_spend:,.2f})")
            for c in campaigns:
                print(f"  {c['campaign_name']:<40} "
                      f"{c['impressions']:>8,} impr  {c['clicks']:>6,} clicks  ${c['spend']:>8,.2f}")
        if result.get("errors"):
            print(f"\nErrors: {result['errors']}")
    else:
        print(f"{result['status']}: {result.get('reason', '')}")
