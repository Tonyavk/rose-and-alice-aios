"""
DataOS — Mailchimp Collector

Tracks newsletter list metrics: subscribers, open rates, campaign performance.

Tables created: mailchimp_snapshot, mailchimp_campaigns
"""

import os
import requests
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")


def collect():
    api_key = os.getenv("MAILCHIMP_API_KEY", "").strip()
    server = os.getenv("MAILCHIMP_SERVER", "").strip()

    if not api_key or not server:
        return {"source": "mailchimp", "status": "skipped",
                "reason": "Missing MAILCHIMP_API_KEY or MAILCHIMP_SERVER"}

    auth = ("anystring", api_key)
    base = f"https://{server}.api.mailchimp.com/3.0"

    try:
        # Get all lists/audiences
        r = requests.get(f"{base}/lists?count=10", auth=auth, timeout=15)
        r.raise_for_status()
        lists = r.json().get("lists", [])

        audiences = []
        for lst in lists:
            stats = lst.get("stats", {})
            audiences.append({
                "id": lst["id"],
                "name": lst["name"],
                "member_count": lst.get("stats", {}).get("member_count", 0),
                "unsubscribe_count": stats.get("unsubscribe_count", 0),
                "open_rate": round(stats.get("open_rate", 0), 2),
                "click_rate": round(stats.get("click_rate", 0), 2),
                "campaign_count": stats.get("campaign_count", 0),
            })

        # Get recent campaigns (last 5)
        r2 = requests.get(
            f"{base}/campaigns?count=5&status=sent&sort_field=send_time&sort_dir=DESC",
            auth=auth, timeout=15
        )
        r2.raise_for_status()
        raw_campaigns = r2.json().get("campaigns", [])

        campaigns = []
        for c in raw_campaigns:
            settings = c.get("settings", {})
            report = c.get("report_summary", {})
            campaigns.append({
                "id": c["id"],
                "subject": settings.get("subject_line", ""),
                "send_time": c.get("send_time", ""),
                "emails_sent": c.get("emails_sent", 0),
                "open_rate": round(report.get("open_rate", 0) * 100, 2),
                "click_rate": round(report.get("click_rate", 0) * 100, 2),
                "opens": report.get("opens", 0),
                "clicks": report.get("clicks", 0),
            })

        return {
            "source": "mailchimp",
            "status": "success",
            "data": {
                "audiences": audiences,
                "campaigns": campaigns,
                "total_subscribers": sum(a["member_count"] for a in audiences),
            }
        }

    except Exception as e:
        return {"source": "mailchimp", "status": "error", "reason": str(e)}


def write(conn, result, date):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS mailchimp_snapshot (
            date TEXT NOT NULL,
            audience_name TEXT NOT NULL,
            member_count INTEGER,
            unsubscribe_count INTEGER,
            open_rate REAL,
            click_rate REAL,
            campaign_count INTEGER,
            collected_at TEXT,
            PRIMARY KEY (date, audience_name)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS mailchimp_campaigns (
            date TEXT NOT NULL,
            campaign_id TEXT NOT NULL,
            subject TEXT,
            send_time TEXT,
            emails_sent INTEGER,
            open_rate REAL,
            click_rate REAL,
            opens INTEGER,
            clicks INTEGER,
            collected_at TEXT,
            PRIMARY KEY (date, campaign_id)
        )
    """)

    if result.get("status") != "success":
        conn.commit()
        return 0

    data = result["data"]
    collected_at = datetime.now(timezone.utc).isoformat()
    records = 0

    for audience in data["audiences"]:
        conn.execute(
            "INSERT OR REPLACE INTO mailchimp_snapshot "
            "(date, audience_name, member_count, unsubscribe_count, open_rate, click_rate, campaign_count, collected_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (date, audience["name"], audience["member_count"], audience["unsubscribe_count"],
             audience["open_rate"], audience["click_rate"], audience["campaign_count"], collected_at)
        )
        records += 1

    for c in data["campaigns"]:
        conn.execute(
            "INSERT OR REPLACE INTO mailchimp_campaigns "
            "(date, campaign_id, subject, send_time, emails_sent, open_rate, click_rate, opens, clicks, collected_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (date, c["id"], c["subject"], c["send_time"], c["emails_sent"],
             c["open_rate"], c["click_rate"], c["opens"], c["clicks"], collected_at)
        )
        records += 1

    conn.commit()
    return records


if __name__ == "__main__":
    result = collect()
    if result["status"] == "success":
        d = result["data"]
        print(f"Mailchimp connected!")
        print(f"  Total subscribers: {d['total_subscribers']}")
        for a in d["audiences"]:
            print(f"  List '{a['name']}': {a['member_count']} subscribers, {a['open_rate']}% open rate")
        print(f"  Recent campaigns: {len(d['campaigns'])}")
        for c in d["campaigns"][:3]:
            print(f"    - {c['subject'][:50]} ({c['open_rate']}% open)")
    else:
        print(f"{result['status']}: {result.get('reason', '')}")
