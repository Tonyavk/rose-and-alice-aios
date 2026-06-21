"""
Reporting — Google Ads Monthly Collector

Pulls campaign-level metrics from Google Ads for each client configured
in config/reporting-clients.yaml for a given month.

Tables: google_ads_monthly
Usage:
    python scripts/reporting/collect_google_ads.py              # Last month
    python scripts/reporting/collect_google_ads.py --period 2026-04
"""

import sys
import argparse
from datetime import datetime, timezone
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(WORKSPACE_ROOT / "scripts"))
sys.path.insert(0, str(WORKSPACE_ROOT / "scripts" / "reporting"))

from dotenv import load_dotenv
load_dotenv(WORKSPACE_ROOT / ".env", override=True)

from config import load_clients, last_month_period, period_dates, get_creds


def _build_ads_client(creds):
    from google.ads.googleads.client import GoogleAdsClient
    cfg = {
        "developer_token": creds["google_ads_developer_token"],
        "client_id": creds["google_ads_client_id"],
        "client_secret": creds["google_ads_client_secret"],
        "refresh_token": creds["google_ads_refresh_token"],
        "login_customer_id": creds["google_ads_mcc_id"],
        "use_proto_plus": True,
    }
    return GoogleAdsClient.load_from_dict(cfg)


def _fetch_campaigns(ads_client, customer_id, start_date, end_date, level="campaign"):
    """Pull metrics for a customer over a date range, at campaign or ad-group level."""
    if level == "ad_group":
        select = """
            campaign.id,
            campaign.name,
            campaign.advertising_channel_type,
            ad_group.id,
            ad_group.name,"""
        from_clause = "ad_group"
        status_filter = "ad_group.status IN ('ENABLED', 'PAUSED')"
    else:
        select = """
            campaign.id,
            campaign.name,
            campaign.advertising_channel_type,"""
        from_clause = "campaign"
        status_filter = "campaign.status IN ('ENABLED', 'PAUSED')"

    query = f"""
        SELECT{select}
            metrics.impressions,
            metrics.clicks,
            metrics.cost_micros,
            metrics.ctr,
            metrics.average_cpc,
            metrics.conversions,
            metrics.all_conversions,
            metrics.conversions_from_interactions_rate,
            metrics.all_conversions_value
        FROM {from_clause}
        WHERE segments.date BETWEEN '{start_date}' AND '{end_date}'
            AND {status_filter}
            AND metrics.impressions > 0
        ORDER BY metrics.cost_micros DESC
    """
    request = ads_client.get_type("SearchGoogleAdsRequest")
    request.customer_id = str(customer_id).replace("-", "")
    request.query = query

    campaigns = []
    for row in ads_client.get_service("GoogleAdsService").search(request=request):
        cost = row.metrics.cost_micros / 1_000_000
        avg_cpc = row.metrics.average_cpc / 1_000_000
        conv_value = row.metrics.all_conversions_value
        roas = round(conv_value / cost, 2) if cost > 0 else 0

        campaigns.append({
            "campaign_id": str(row.campaign.id),
            "campaign_name": row.campaign.name,
            "campaign_type": row.campaign.advertising_channel_type.name,
            "ad_group_id": str(row.ad_group.id) if level == "ad_group" else "",
            "ad_group_name": row.ad_group.name if level == "ad_group" else "",
            "reporting_level": level,
            "impressions": row.metrics.impressions,
            "clicks": row.metrics.clicks,
            "cost": round(cost, 2),
            "ctr": round(row.metrics.ctr * 100, 2),
            "avg_cpc": round(avg_cpc, 2),
            "conversions": round(row.metrics.conversions, 2),
            "all_conversions": round(row.metrics.all_conversions, 2),
            "conv_rate": round(row.metrics.conversions_from_interactions_rate * 100, 2),
            "conv_value": round(conv_value, 2),
            "roas": roas,
        })

    return campaigns


def collect(period=None):
    """
    Collect Google Ads monthly data for all configured clients.

    Returns:
        {"status": "success", "period": ..., "data": {slug: [campaigns]}, "errors": [...]}
    """
    creds = get_creds()
    required = [
        "google_ads_developer_token", "google_ads_mcc_id",
        "google_ads_client_id", "google_ads_client_secret", "google_ads_refresh_token",
    ]
    missing = [k for k in required if not creds[k]]
    if missing:
        return {"status": "skipped", "reason": f"Missing credentials: {', '.join(missing)}"}

    if period is None:
        period = last_month_period()

    start_date, end_date = period_dates(period)

    try:
        ads_client = _build_ads_client(creds)
    except Exception as e:
        return {"status": "error", "reason": f"Failed to create Google Ads client: {e}"}

    clients = [c for c in load_clients() if "google_ads" in c.get("platforms", {})]
    results = {}
    errors = []

    for client in clients:
        slug = client["slug"]
        customer_id = client["platforms"]["google_ads"]["customer_id"]
        # Brand and shopping reports break down by ad group; others stay at campaign level
        level = "ad_group" if client.get("report_type") in ("brand", "shopping") else "campaign"
        try:
            campaigns = _fetch_campaigns(ads_client, customer_id, start_date, end_date, level)
            results[slug] = campaigns
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


def _create_table(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS google_ads_monthly (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            period TEXT NOT NULL,
            client_slug TEXT NOT NULL,
            campaign_id TEXT,
            campaign_name TEXT,
            campaign_type TEXT,
            ad_group_id TEXT,
            ad_group_name TEXT,
            impressions INTEGER,
            clicks INTEGER,
            cost REAL,
            ctr REAL,
            avg_cpc REAL,
            conversions REAL,
            all_conversions REAL,
            conv_rate REAL,
            conv_value REAL,
            roas REAL,
            reporting_level TEXT DEFAULT 'campaign',
            collected_at TEXT,
            UNIQUE(period, client_slug, campaign_id, ad_group_id)
        )
    """)


def _ensure_schema(conn):
    """Create the table, migrating older versions that lack ad-group support.

    The unique key changed from (period, client_slug, campaign_id) to include
    ad_group_id, so the table is rebuilt — existing rows are preserved.
    """
    row = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='google_ads_monthly'"
    ).fetchone()
    if row and "ad_group_id" not in (row[0] or ""):
        old_cols = [r[1] for r in conn.execute("PRAGMA table_info(google_ads_monthly)").fetchall()]
        conn.execute("ALTER TABLE google_ads_monthly RENAME TO google_ads_monthly_old")
        _create_table(conn)
        new_cols = [r[1] for r in conn.execute("PRAGMA table_info(google_ads_monthly)").fetchall()]
        common = [c for c in old_cols if c in new_cols and c != "id"]
        collist = ", ".join(common)
        conn.execute(
            f"INSERT INTO google_ads_monthly ({collist}) SELECT {collist} FROM google_ads_monthly_old"
        )
        conn.execute("DROP TABLE google_ads_monthly_old")
    else:
        _create_table(conn)


def write(conn, result, period):
    """Write collected Google Ads data to the database."""
    _ensure_schema(conn)

    if result.get("status") != "success":
        conn.commit()
        return 0

    collected_at = datetime.now(timezone.utc).isoformat()
    records = 0

    for slug, campaigns in result["data"].items():
        # Clear any prior rows for this client/period so a level switch
        # (campaign ↔ ad_group) can't leave stale, double-counted rows behind.
        conn.execute(
            "DELETE FROM google_ads_monthly WHERE period = ? AND client_slug = ?",
            (period, slug),
        )
        for c in campaigns:
            conn.execute(
                "INSERT OR REPLACE INTO google_ads_monthly "
                "(period, client_slug, campaign_id, campaign_name, campaign_type, "
                "ad_group_id, ad_group_name, impressions, clicks, "
                "cost, ctr, avg_cpc, conversions, all_conversions, conv_rate, conv_value, roas, "
                "reporting_level, collected_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (period, slug, c["campaign_id"], c["campaign_name"], c.get("campaign_type"),
                 c.get("ad_group_id", ""), c.get("ad_group_name", ""),
                 c["impressions"], c["clicks"], c["cost"], c["ctr"],
                 c["avg_cpc"], c["conversions"], c.get("all_conversions"),
                 c["conv_rate"], c["conv_value"], c["roas"],
                 c.get("reporting_level", "campaign"), collected_at),
            )
            records += 1

    conn.commit()
    return records


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Collect Google Ads monthly data")
    parser.add_argument("--period", default=None, help="YYYY-MM (default: last month)")
    args = parser.parse_args()

    result = collect(args.period)
    if result["status"] == "success":
        for slug, campaigns in result["data"].items():
            total_cost = sum(c["cost"] for c in campaigns)
            total_impr = sum(c["impressions"] for c in campaigns)
            total_clicks = sum(c["clicks"] for c in campaigns)
            print(f"\n{slug}  ({len(campaigns)} campaigns | {total_impr:,} impr | "
                  f"{total_clicks:,} clicks | ${total_cost:,.2f})")
            for c in campaigns:
                print(f"  {c['campaign_name']:<40} "
                      f"{c['impressions']:>8,} impr  {c['clicks']:>6,} clicks  ${c['cost']:>8,.2f}")
        if result.get("errors"):
            print(f"\nErrors: {result['errors']}")
    else:
        print(f"{result['status']}: {result.get('reason', '')}")
