"""
Reporting — Monthly Staging Run

Runs on the 1st of each month (via launchd: com.aios.monthly-reports).
Collects last month's ad data and generates DRAFT reports for every client —
HTML + editable summary .txt + draft PDF — into outputs/client-reports/YYYY-MM/,
then emails Tonya that they are staged for review.

It does NOT finalise. Tonya reviews the HTML, edits the summary .txt files for
any wording changes, then runs the finalise step herself:

    python scripts/reporting/run_reports.py --no-collect --finalize --period YYYY-MM --client <slug>

Run manually:
    .venv/bin/python scripts/reporting/monthly_run.py
    .venv/bin/python scripts/reporting/monthly_run.py --email-test   # send a test email only
"""

import os
import sys
import ssl
import smtplib
import argparse
from email.message import EmailMessage
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(WORKSPACE_ROOT / "scripts"))
sys.path.insert(0, str(WORKSPACE_ROOT / "scripts" / "reporting"))

from dotenv import load_dotenv
load_dotenv(WORKSPACE_ROOT / ".env", override=True)

from config import last_month_period, period_label
import run_reports


def _send_email(subject, body):
    """Send a plain-text email via SMTP using credentials from .env. Returns True on success."""
    host = os.getenv("SMTP_HOST", "smtp.gmail.com").strip()
    port = int(os.getenv("SMTP_PORT", "587") or "587")
    user = os.getenv("SMTP_USER", "").strip()
    password = os.getenv("SMTP_APP_PASSWORD", "").strip()
    to_addr = (os.getenv("REPORT_NOTIFY_TO", "").strip() or user)

    if not (user and password and to_addr):
        print("  Email skipped — set SMTP_USER and SMTP_APP_PASSWORD in .env", file=sys.stderr)
        return False

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = user
    msg["To"] = to_addr
    msg.set_content(body)

    try:
        # Use certifi's CA bundle — macOS Python builds often can't find system roots
        try:
            import certifi
            ctx = ssl.create_default_context(cafile=certifi.where())
        except ImportError:
            ctx = ssl.create_default_context()
        with smtplib.SMTP(host, port, timeout=30) as server:
            server.starttls(context=ctx)
            server.login(user, password)
            server.send_message(msg)
        print(f"  Notification emailed to {to_addr}")
        return True
    except Exception as e:
        print(f"  Email failed: {e}", file=sys.stderr)
        return False


def _build_body(period, pl, out_dir):
    pdfs = sorted(out_dir.glob("*.pdf")) if out_dir.exists() else []
    listing = "\n".join(f"  - {p.stem}" for p in pdfs) or "  (none found — check the run log)"
    return (
        f"Hi Tonya,\n\n"
        f"Your {pl} client reports have been generated and are staged for review.\n\n"
        f"Location:\n{out_dir}\n\n"
        f"{len(pdfs)} report(s) ready:\n{listing}\n\n"
        f"Next steps:\n"
        f"1. Open each client's HTML or PDF to review.\n"
        f"2. Edit the matching '<slug>-<type>-summary.txt' file for any wording changes.\n"
        f"3. Finalise the PDF once you're happy:\n"
        f"   python scripts/reporting/run_reports.py --no-collect --finalize "
        f"--period {period} --client <slug>\n\n"
        f"Nothing has been sent to clients — these are drafts for your review.\n\n"
        f"- AIOS\n"
    )


def main():
    parser = argparse.ArgumentParser(description="Monthly report staging run + email notification")
    parser.add_argument("--email-test", action="store_true",
                        help="Send a test notification email only (no collection or generation)")
    args = parser.parse_args()

    period = last_month_period()
    pl = period_label(period)
    out_dir = WORKSPACE_ROOT / "outputs" / "client-reports" / period

    if args.email_test:
        body = (f"This is a test of the monthly reports notification.\n\n"
                f"If you received this, the email setup is working. The real run fires on the "
                f"1st of each month at 12:00pm and will list your staged {pl} reports.\n\n- AIOS\n")
        ok = _send_email(f"Test — client reports notification", body)
        sys.exit(0 if ok else 1)

    print(f"Monthly staging run for {pl} ...")
    run_reports.run(period=period)          # collect + generate drafts, all clients, no finalise

    body = _build_body(period, pl, out_dir)
    print("\n" + body)
    _send_email(f"Client reports ready for review — {pl}", body)


if __name__ == "__main__":
    main()
