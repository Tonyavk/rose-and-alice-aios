"""
DataOS — Xero Collector

Pulls invoice and revenue data from Xero daily.
Tracks: revenue MTD, last month revenue, outstanding invoices.

Requires:
    credentials/xero_tokens.json — run xero_auth.py once to create this
    XERO_CLIENT_ID, XERO_CLIENT_SECRET — in .env

Tables created: xero_daily, xero_invoices
"""

import json
import os
import sqlite3
from datetime import datetime, timezone, timedelta, date
from pathlib import Path

import requests
from dotenv import load_dotenv

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(WORKSPACE_ROOT / ".env")

TOKENS_PATH   = WORKSPACE_ROOT / "credentials" / "xero_tokens.json"
CLIENT_ID     = os.getenv("XERO_CLIENT_ID", "").strip()
CLIENT_SECRET = os.getenv("XERO_CLIENT_SECRET", "").strip()
TOKEN_URL     = "https://identity.xero.com/connect/token"
API_BASE      = "https://api.xero.com/api.xro/2.0"


# --- Token management ---

def load_tokens():
    if not TOKENS_PATH.exists():
        return None
    return json.loads(TOKENS_PATH.read_text())


def save_tokens(tokens):
    TOKENS_PATH.write_text(json.dumps(tokens, indent=2))


def refresh_if_needed(tokens):
    expires_at = datetime.fromisoformat(tokens["expires_at"])
    now = datetime.now(timezone.utc)
    if expires_at - now > timedelta(minutes=5):
        return tokens  # still valid

    r = requests.post(TOKEN_URL, data={
        "grant_type":    "refresh_token",
        "refresh_token": tokens["refresh_token"],
        "client_id":     CLIENT_ID,
        "client_secret": CLIENT_SECRET,
    }, timeout=15)
    r.raise_for_status()
    data = r.json()

    tokens["access_token"]  = data["access_token"]
    tokens["refresh_token"] = data["refresh_token"]
    tokens["expires_at"] = (
        datetime.now(timezone.utc) + timedelta(seconds=data["expires_in"])
    ).isoformat()
    save_tokens(tokens)
    return tokens


def api_get(path, tokens, params=None):
    headers = {
        "Authorization": f"Bearer {tokens['access_token']}",
        "Xero-Tenant-Id": tokens["tenant_id"],
        "Accept": "application/json",
    }
    r = requests.get(f"{API_BASE}{path}", headers=headers, params=params, timeout=30)
    r.raise_for_status()
    return r.json()


# --- Data collection ---

def fetch_invoices(tokens, from_date, to_date):
    """Fetch ACCREC (sales) invoices between two dates."""
    params = {
        "where": f'Type=="ACCREC" AND Date>=DateTime({from_date.year},{from_date.month},{from_date.day}) AND Date<=DateTime({to_date.year},{to_date.month},{to_date.day})',
        "order": "Date DESC",
        "pageSize": 100,
    }
    data = api_get("/Invoices", tokens, params)
    return data.get("Invoices", [])


def collect():
    if not TOKENS_PATH.exists():
        return {
            "source": "xero", "status": "skipped",
            "reason": "Not authenticated — run: python scripts/xero_auth.py"
        }
    if not CLIENT_ID or not CLIENT_SECRET:
        return {
            "source": "xero", "status": "skipped",
            "reason": "Missing XERO_CLIENT_ID or XERO_CLIENT_SECRET in .env"
        }

    try:
        tokens = load_tokens()
        tokens = refresh_if_needed(tokens)
    except Exception as e:
        return {"source": "xero", "status": "error", "reason": f"Token refresh failed: {e}"}

    try:
        today      = date.today()
        month_start = today.replace(day=1)

        # Last month range
        last_month_end   = month_start - timedelta(days=1)
        last_month_start = last_month_end.replace(day=1)

        # Current month invoices
        current_invoices = fetch_invoices(tokens, month_start, today)

        # Last month invoices
        last_invoices = fetch_invoices(tokens, last_month_start, last_month_end)

        def revenue(invoices, status):
            return sum(
                inv.get("Total", 0)
                for inv in invoices
                if inv.get("Status") == status
            )

        def count(invoices, status):
            return sum(1 for inv in invoices if inv.get("Status") == status)

        revenue_mtd         = revenue(current_invoices, "PAID")
        outstanding_amount  = revenue(current_invoices, "AUTHORISED")
        outstanding_count   = count(current_invoices, "AUTHORISED")
        paid_count_mtd      = count(current_invoices, "PAID")
        revenue_last_month  = revenue(last_invoices, "PAID")

        # Collect individual invoice records (current + last month)
        all_invoices = []
        for inv in current_invoices + last_invoices:
            all_invoices.append({
                "invoice_id":    inv.get("InvoiceID", ""),
                "invoice_number":inv.get("InvoiceNumber", ""),
                "contact":       inv.get("Contact", {}).get("Name", ""),
                "date":          inv.get("DateString", "")[:10] if inv.get("DateString") else "",
                "due_date":      inv.get("DueDateString", "")[:10] if inv.get("DueDateString") else "",
                "status":        inv.get("Status", ""),
                "total":         inv.get("Total", 0),
                "amount_due":    inv.get("AmountDue", 0),
                "amount_paid":   inv.get("AmountPaid", 0),
                "currency":      inv.get("CurrencyCode", "NZD"),
            })

        return {
            "source": "xero",
            "status": "success",
            "data": {
                "tenant_name":       tokens["tenant_name"],
                "revenue_mtd":       revenue_mtd,
                "revenue_last_month":revenue_last_month,
                "outstanding_amount":outstanding_amount,
                "outstanding_count": outstanding_count,
                "paid_count_mtd":    paid_count_mtd,
                "month_start":       str(month_start),
                "invoices":          all_invoices,
            }
        }

    except Exception as e:
        return {"source": "xero", "status": "error", "reason": str(e)}


# --- Database write ---

def write(conn, result, date_str):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS xero_daily (
            date TEXT NOT NULL PRIMARY KEY,
            tenant_name TEXT,
            revenue_mtd REAL,
            revenue_last_month REAL,
            outstanding_amount REAL,
            outstanding_count INTEGER,
            paid_count_mtd INTEGER,
            month_start TEXT,
            collected_at TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS xero_invoices (
            invoice_id TEXT NOT NULL,
            snapshot_date TEXT NOT NULL,
            invoice_number TEXT,
            contact TEXT,
            date TEXT,
            due_date TEXT,
            status TEXT,
            total REAL,
            amount_due REAL,
            amount_paid REAL,
            currency TEXT,
            collected_at TEXT,
            PRIMARY KEY (invoice_id, snapshot_date)
        )
    """)

    if result.get("status") != "success":
        conn.commit()
        return 0

    data = result["data"]
    collected_at = datetime.now(timezone.utc).isoformat()
    records = 0

    conn.execute(
        "INSERT OR REPLACE INTO xero_daily "
        "(date, tenant_name, revenue_mtd, revenue_last_month, outstanding_amount, "
        "outstanding_count, paid_count_mtd, month_start, collected_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (date_str, data["tenant_name"], data["revenue_mtd"], data["revenue_last_month"],
         data["outstanding_amount"], data["outstanding_count"], data["paid_count_mtd"],
         data["month_start"], collected_at)
    )
    records += 1

    for inv in data["invoices"]:
        conn.execute(
            "INSERT OR REPLACE INTO xero_invoices "
            "(invoice_id, snapshot_date, invoice_number, contact, date, due_date, "
            "status, total, amount_due, amount_paid, currency, collected_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (inv["invoice_id"], date_str, inv["invoice_number"], inv["contact"],
             inv["date"], inv["due_date"], inv["status"], inv["total"],
             inv["amount_due"], inv["amount_paid"], inv["currency"], collected_at)
        )
        records += 1

    conn.commit()
    return records


if __name__ == "__main__":
    result = collect()
    if result["status"] == "success":
        d = result["data"]
        print(f"Xero connected! ({d['tenant_name']})")
        print(f"  Revenue this month (paid): NZD {d['revenue_mtd']:,.0f}")
        print(f"  Revenue last month:        NZD {d['revenue_last_month']:,.0f}")
        print(f"  Outstanding invoices:      NZD {d['outstanding_amount']:,.0f} ({d['outstanding_count']} invoices)")
        print(f"  Invoices paid MTD:         {d['paid_count_mtd']}")
    else:
        print(f"{result['status']}: {result.get('reason', '')}")
