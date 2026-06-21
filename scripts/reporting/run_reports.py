"""
Reporting — Monthly Report Orchestrator

Collects ad data for the given period, stores it in the database,
and generates a report for each configured client.

Usage:
    python scripts/reporting/run_reports.py                     # Last month, all clients
    python scripts/reporting/run_reports.py --period 2026-04    # Specific month
    python scripts/reporting/run_reports.py --client vivea-skincare  # One client only
    python scripts/reporting/run_reports.py --html-only         # Skip PDF conversion
    python scripts/reporting/run_reports.py --no-collect        # Skip data pull (use DB)
"""

import sys
import argparse
from datetime import datetime, timezone
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(WORKSPACE_ROOT / "scripts"))
sys.path.insert(0, str(WORKSPACE_ROOT / "scripts" / "reporting"))

from dotenv import load_dotenv
load_dotenv(WORKSPACE_ROOT / ".env")

from config import load_clients, last_month_period, period_label
from db import init_db, log_collection

import collect_google_ads
import collect_meta
import generate_report as gen


def run(period=None, client_slug=None, html_only=False, no_collect=False, finalize=False,
        report_type=None):
    if period is None:
        period = last_month_period()

    pl = period_label(period)
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    print(f"\n{'='*60}")
    print(f"  Monthly Reporting — {pl}")
    print(f"  {timestamp}")
    print(f"{'='*60}\n")

    conn = init_db()

    # ── Step 1: Collect data ──────────────────────────────────────────────
    if not no_collect:
        print("Collecting Google Ads data...")
        g_result = collect_google_ads.collect(period)
        if g_result["status"] == "success":
            records = collect_google_ads.write(conn, g_result, period)
            log_collection(conn, "google_ads_monthly", "success", records)
            print(f"  Google Ads: {records} campaign records written")
            if g_result.get("errors"):
                for e in g_result["errors"]:
                    print(f"  Warning: {e}")
        else:
            print(f"  Google Ads skipped: {g_result.get('reason', '')}")

        print("Collecting Meta Ads data...")
        m_result = collect_meta.collect(period)
        if m_result["status"] == "success":
            records = collect_meta.write(conn, m_result, period)
            log_collection(conn, "meta_campaign_monthly", "success", records)
            print(f"  Meta Ads: {records} campaign records written")
            if m_result.get("errors"):
                for e in m_result["errors"]:
                    print(f"  Warning: {e}")
        else:
            print(f"  Meta Ads skipped: {m_result.get('reason', '')}")
    else:
        print("Skipping data collection (--no-collect)")

    print()

    # ── Step 2: Generate reports ──────────────────────────────────────────
    clients = load_clients()
    if client_slug:
        clients = [c for c in clients if c["slug"] == client_slug]
        if not clients:
            print(f"Error: client '{client_slug}' not found in reporting-clients.yaml")
            conn.close()
            sys.exit(1)
    if report_type:
        clients = [c for c in clients if c.get("report_type") == report_type]
        if not clients:
            print(f"Error: no clients with report_type '{report_type}' in reporting-clients.yaml")
            conn.close()
            sys.exit(1)

    generated = []
    failed = []

    for client in clients:
        slug = client["slug"]
        print(f"Generating report: {client['name']}...")
        try:
            path = gen.generate(slug, period=period, html_only=html_only, conn=conn,
                                use_saved_summary=finalize)
            print(f"  Saved: {path}")
            generated.append((client["name"], path))
        except Exception as e:
            print(f"  Error: {e}")
            failed.append((client["name"], str(e)))

    conn.close()

    # ── Summary ───────────────────────────────────────────────────────────
    print(f"\n{'─'*60}")
    print(f"Done — {pl}")
    print(f"  {len(generated)} report(s) generated, {len(failed)} failed\n")

    for name, path in generated:
        print(f"  ✓  {name}")
        print(f"     {path}")

    if failed:
        print()
        for name, reason in failed:
            print(f"  ✗  {name}: {reason}")

    print()
    out_dir = WORKSPACE_ROOT / "outputs" / "client-reports" / period
    print(f"Reports folder: {out_dir}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate monthly client reports")
    parser.add_argument("--period", default=None, help="YYYY-MM (default: last month)")
    parser.add_argument("--client", default=None, help="Single client slug (default: all)")
    parser.add_argument("--html-only", action="store_true", help="Save HTML only, skip PDF")
    parser.add_argument("--no-collect", action="store_true", help="Skip data pull, use existing DB data")
    parser.add_argument("--finalize", action="store_true",
                        help="Use saved summary .txt instead of calling Claude — for after you've edited the narrative")
    parser.add_argument("--report-type", default=None, choices=["shopping", "brand"],
                        help="Only run clients of this type (shopping or brand)")
    args = parser.parse_args()

    run(
        period=args.period,
        client_slug=args.client,
        html_only=args.html_only,
        no_collect=args.no_collect,
        finalize=args.finalize,
        report_type=args.report_type,
    )
