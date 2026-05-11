"""
DataOS — Client & Leads Tracker Collector (Google Sheets)

Reads Tonya's client tracking spreadsheet.
Columns A-F: Active clients (name, report sent, invoiced, chatbot email, quotes)
Columns G-H: Prospects/leads (name, notes)

Tables created: client_snapshot, client_list, leads_list
"""

import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
except ImportError:
    raise ImportError("Run: pip install google-api-python-client google-auth")

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
CREDS_PATH = WORKSPACE_ROOT / "credentials" / "google-service-account.json"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]

# Column positions (0-indexed)
COL_CLIENT  = 0
COL_STATUS  = 1
COL_REPORT  = 2
COL_INVOICE = 3
COL_CHATBOT = 4
COL_QUOTES  = 5
COL_LEAD    = 6
COL_NOTES   = 7


def is_checked(value):
    """TRUE/ticked checkbox or non-empty meaningful value."""
    if not value:
        return False
    return str(value).strip().upper() in ("TRUE", "YES", "✓", "X", "1")


def get(row, idx, default=""):
    return row[idx].strip() if len(row) > idx and row[idx] else default


def collect():
    sheet_id = os.getenv("GOOGLE_SHEET_ID", "").strip()
    tab = os.getenv("GOOGLE_SHEET_TAB", "Sheet1").strip()

    if not sheet_id:
        return {"source": "clients", "status": "skipped", "reason": "Missing GOOGLE_SHEET_ID"}
    if not CREDS_PATH.exists():
        return {"source": "clients", "status": "skipped", "reason": "Missing google-service-account.json"}

    try:
        creds = service_account.Credentials.from_service_account_file(
            str(CREDS_PATH), scopes=SCOPES
        )
        service = build("sheets", "v4", credentials=creds)
        result = service.spreadsheets().values().get(
            spreadsheetId=sheet_id,
            range=tab,
            valueRenderOption="UNFORMATTED_VALUE"
        ).execute()
        rows = result.get("values", [])
    except Exception as e:
        return {"source": "clients", "status": "error", "reason": str(e)}

    if len(rows) < 2:
        return {"source": "clients", "status": "skipped", "reason": "Sheet appears empty"}

    clients = []
    leads = []

    for row in rows[1:]:  # skip header
        # Active clients (columns A-F)
        name = get(row, COL_CLIENT)
        if name and name.lower() != "client name":
            clients.append({
                "name": name,
                "status": get(row, COL_STATUS),
                "report_sent": is_checked(get(row, COL_REPORT)),
                "invoiced": is_checked(get(row, COL_INVOICE)),
                "chatbot_email": is_checked(get(row, COL_CHATBOT)),
                "quotes": is_checked(get(row, COL_QUOTES)),
            })

        # Prospects/leads (columns G-H)
        lead_name = get(row, COL_LEAD)
        lead_notes = get(row, COL_NOTES)
        if lead_name:
            leads.append({"name": lead_name, "notes": lead_notes})

    return {
        "source": "clients",
        "status": "success",
        "data": {
            "clients": clients,
            "leads": leads,
            "total_clients": len(clients),
            "invoiced_count": sum(1 for c in clients if c["invoiced"]),
            "report_sent_count": sum(1 for c in clients if c["report_sent"]),
            "quotes_count": sum(1 for c in clients if c["quotes"]),
            "chatbot_count": sum(1 for c in clients if c["chatbot_email"]),
            "total_leads": len(leads),
        }
    }


def write(conn, result, date):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS client_snapshot (
            date TEXT NOT NULL PRIMARY KEY,
            total_clients INTEGER,
            invoiced_count INTEGER,
            report_sent_count INTEGER,
            quotes_count INTEGER,
            chatbot_count INTEGER,
            total_leads INTEGER,
            collected_at TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS client_list (
            date TEXT NOT NULL,
            client_name TEXT NOT NULL,
            status TEXT,
            report_sent INTEGER DEFAULT 0,
            invoiced INTEGER DEFAULT 0,
            chatbot_email INTEGER DEFAULT 0,
            quotes INTEGER DEFAULT 0,
            collected_at TEXT,
            PRIMARY KEY (date, client_name)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS leads_list (
            date TEXT NOT NULL,
            lead_name TEXT NOT NULL,
            notes TEXT,
            collected_at TEXT,
            PRIMARY KEY (date, lead_name)
        )
    """)

    if result.get("status") != "success":
        conn.commit()
        return 0

    data = result["data"]
    collected_at = datetime.now(timezone.utc).isoformat()

    conn.execute(
        "INSERT OR REPLACE INTO client_snapshot "
        "(date, total_clients, invoiced_count, report_sent_count, quotes_count, chatbot_count, total_leads, collected_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (date, data["total_clients"], data["invoiced_count"], data["report_sent_count"],
         data["quotes_count"], data["chatbot_count"], data["total_leads"], collected_at)
    )

    for c in data["clients"]:
        conn.execute(
            "INSERT OR REPLACE INTO client_list "
            "(date, client_name, status, report_sent, invoiced, chatbot_email, quotes, collected_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (date, c["name"], c["status"], int(c["report_sent"]),
             int(c["invoiced"]), int(c["chatbot_email"]), int(c["quotes"]), collected_at)
        )

    for lead in data["leads"]:
        conn.execute(
            "INSERT OR REPLACE INTO leads_list (date, lead_name, notes, collected_at) VALUES (?, ?, ?, ?)",
            (date, lead["name"], lead["notes"], collected_at)
        )

    conn.commit()
    return 1 + len(data["clients"]) + len(data["leads"])


if __name__ == "__main__":
    result = collect()
    if result["status"] == "success":
        d = result["data"]
        print(f"Sheet connected!")
        print(f"  Active clients: {d['total_clients']}")
        print(f"  Invoiced this period: {d['invoiced_count']}")
        print(f"  Reports sent: {d['report_sent_count']}")
        print(f"  Quotes sent: {d['quotes_count']}")
        print(f"  Prospects/leads: {d['total_leads']}")
    else:
        print(f"{result['status']}: {result.get('reason', '')}")
