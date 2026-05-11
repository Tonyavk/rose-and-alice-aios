"""
DataOS — Key Metrics Generator

Reads the database and generates a human-readable key-metrics.md file.
This file is loaded by your /prime command so your AI always has fresh data.

Automatically discovers which tables exist and generates sections for each.
Claude will customize this file during installation to match your data sources.

Usage:
    python scripts/generate_metrics.py
"""

import sqlite3
from datetime import datetime
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = WORKSPACE_ROOT / "data" / "data.db"
OUTPUT_PATH = WORKSPACE_ROOT / "context" / "group" / "key-metrics.md"


# --- Formatting helpers ---

def fmt_number(value, prefix="", suffix=""):
    """Format a number with commas. Returns 'No data' if None."""
    if value is None:
        return "No data"
    if isinstance(value, float):
        return f"{prefix}{value:,.0f}{suffix}"
    return f"{prefix}{value:,}{suffix}"


def fmt_currency(value, symbol="$"):
    """Format currency value with symbol and commas."""
    if value is None:
        return "No data"
    return f"{symbol}{value:,.0f}"


def fmt_pct(value):
    """Format a percentage to 1 decimal place."""
    if value is None:
        return "No data"
    return f"{value:.1f}%"


def query_one(conn, sql):
    """Query helper — returns first row as dict or None."""
    try:
        row = conn.execute(sql).fetchone()
        return dict(row) if row else None
    except Exception:
        return None


def query_all(conn, sql):
    """Query helper — returns all rows as list of dicts."""
    try:
        return [dict(r) for r in conn.execute(sql).fetchall()]
    except Exception:
        return []


def table_exists(conn, name):
    """Check if a table exists."""
    r = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (name,)
    ).fetchone()
    return r is not None


# ============================================================
# SECTION GENERATORS
# Each function returns a list of markdown lines for its section.
# Claude will add custom section functions here during installation.
# ============================================================


def section_fx_rates(conn):
    """FX rates — the starter collector (always available)."""
    if not table_exists(conn, "fx_rates"):
        return []
    lines = []
    lines.append("## Exchange Rates")
    lines.append("| Currency | Rate (from USD) | As Of |")
    lines.append("|----------|----------------|-------|")
    rows = query_all(conn, """
        SELECT date, currency, rate FROM fx_rates
        WHERE date = (SELECT MAX(date) FROM fx_rates)
        ORDER BY currency
    """)
    for r in rows:
        lines.append(f"| {r['currency']} | {r['rate']:.4f} | {r['date']} |")
    lines.append("")
    return lines


# --- CUSTOMIZATION ZONE ---

def section_ga4(conn):
    """Google Analytics — website traffic snapshot."""
    if not table_exists(conn, "ga4_daily"):
        return []
    row = query_one(conn, "SELECT * FROM ga4_daily ORDER BY date DESC LIMIT 1")
    if not row:
        return []
    lines = ["## Website Traffic (Google Analytics)"]
    lines.append("| Metric | Value | As Of |")
    lines.append("|--------|-------|-------|")
    lines.append(f"| Sessions | {fmt_number(row['sessions'])} | {row['date']} |")
    lines.append(f"| Users | {fmt_number(row['total_users'])} | {row['date']} |")
    lines.append(f"| New users | {fmt_number(row['new_users'])} | {row['date']} |")
    lines.append(f"| Page views | {fmt_number(row['page_views'])} | {row['date']} |")
    if row['engagement_rate'] is not None:
        lines.append(f"| Engagement rate | {fmt_pct(row['engagement_rate'] * 100)} | {row['date']} |")
    lines.append("")

    sources = query_all(conn, f"""
        SELECT source, medium, sessions, users FROM ga4_sources
        WHERE date = '{row['date']}'
        ORDER BY sessions DESC LIMIT 8
    """)
    if sources:
        lines.append("### Top Traffic Sources")
        lines.append("| Source | Medium | Sessions | Users |")
        lines.append("|--------|--------|----------|-------|")
        for s in sources:
            lines.append(f"| {s['source']} | {s['medium']} | {fmt_number(s['sessions'])} | {fmt_number(s['users'])} |")
        lines.append("")

    return lines


def section_xero(conn):
    """Xero revenue — MTD, last month, outstanding invoices."""
    if not table_exists(conn, "xero_daily"):
        return []
    row = query_one(conn, "SELECT * FROM xero_daily ORDER BY date DESC LIMIT 1")
    if not row:
        return []
    lines = ["## Revenue (Xero)"]
    lines.append("| Metric | Value | As Of |")
    lines.append("|--------|-------|-------|")
    lines.append(f"| Revenue this month (paid) | NZD {row['revenue_mtd']:,.0f} | {row['date']} |")
    lines.append(f"| Revenue last month | NZD {row['revenue_last_month']:,.0f} | {row['date']} |")
    lines.append(f"| Outstanding invoices | NZD {row['outstanding_amount']:,.0f} ({row['outstanding_count']} invoices) | {row['date']} |")
    lines.append(f"| Invoices paid MTD | {row['paid_count_mtd']} | {row['date']} |")
    lines.append("")
    return lines


def section_clients(conn):
    """Client tracker — active clients, invoicing status, leads pipeline."""
    if not table_exists(conn, "client_snapshot"):
        return []
    snap = query_one(conn, "SELECT * FROM client_snapshot ORDER BY date DESC LIMIT 1")
    if not snap:
        return []
    lines = ["## Clients & Pipeline"]
    lines.append(f"| Metric | Value | As Of |")
    lines.append(f"|--------|-------|-------|")
    lines.append(f"| Active clients | {fmt_number(snap['total_clients'])} | {snap['date']} |")
    lines.append(f"| Invoiced this period | {fmt_number(snap['invoiced_count'])} | {snap['date']} |")
    lines.append(f"| Reports sent | {fmt_number(snap['report_sent_count'])} | {snap['date']} |")
    lines.append(f"| Quotes out | {fmt_number(snap['quotes_count'])} | {snap['date']} |")
    lines.append(f"| Leads in pipeline | {fmt_number(snap['total_leads'])} | {snap['date']} |")
    lines.append("")

    # Show client list
    clients = query_all(conn, f"""
        SELECT client_name, status, report_sent, invoiced, quotes
        FROM client_list
        WHERE date = '{snap['date']}'
        ORDER BY client_name
    """)
    if clients:
        lines.append("### Active Clients")
        lines.append("| Client | Report Sent | Invoiced | Quote Out |")
        lines.append("|--------|-------------|----------|-----------|")
        for c in clients:
            report = "Yes" if c["report_sent"] else "—"
            invoiced = "Yes" if c["invoiced"] else "—"
            quotes = "Yes" if c["quotes"] else "—"
            lines.append(f"| {c['client_name']} | {report} | {invoiced} | {quotes} |")
        lines.append("")

    # Show leads
    leads = query_all(conn, f"""
        SELECT lead_name, notes FROM leads_list
        WHERE date = '{snap['date']}'
        ORDER BY lead_name
    """)
    if leads:
        lines.append("### Leads Pipeline")
        lines.append("| Lead | Notes |")
        lines.append("|------|-------|")
        for lead in leads:
            notes = lead["notes"] or "—"
            lines.append(f"| {lead['lead_name']} | {notes} |")
        lines.append("")

    return lines


def section_mailchimp(conn):
    """Mailchimp email marketing — subscribers, open rates, recent campaigns."""
    if not table_exists(conn, "mailchimp_snapshot"):
        return []
    rows = query_all(conn, """
        SELECT * FROM mailchimp_snapshot
        WHERE date = (SELECT MAX(date) FROM mailchimp_snapshot)
    """)
    if not rows:
        return []
    lines = ["## Email Marketing (Mailchimp)"]
    lines.append("| Audience | Subscribers | Open Rate | Click Rate | As Of |")
    lines.append("|----------|-------------|-----------|------------|-------|")
    for r in rows:
        lines.append(
            f"| {r['audience_name']} | {fmt_number(r['member_count'])} "
            f"| {fmt_pct(r['open_rate'])} | {fmt_pct(r['click_rate'])} | {r['date']} |"
        )
    lines.append("")

    campaigns = query_all(conn, """
        SELECT subject, send_time, emails_sent, open_rate, click_rate
        FROM mailchimp_campaigns
        ORDER BY send_time DESC LIMIT 5
    """)
    if campaigns:
        lines.append("### Recent Campaigns")
        lines.append("| Subject | Sent | Open Rate | Click Rate |")
        lines.append("|---------|------|-----------|------------|")
        for c in campaigns:
            send_date = c["send_time"][:10] if c["send_time"] else "—"
            lines.append(
                f"| {c['subject']} | {send_date} | {fmt_pct(c['open_rate'])} | {fmt_pct(c['click_rate'])} |"
            )
        lines.append("")

    return lines


# ============================================================
# MAIN GENERATOR
# ============================================================

# Register all section functions here. Claude adds new ones during install.
SECTIONS = [
    section_xero,
    section_ga4,
    section_clients,
    section_mailchimp,
    section_fx_rates,
]


def generate(conn):
    """Generate the key-metrics markdown content."""
    today = datetime.now().strftime("%Y-%m-%d")
    lines = [
        "# Key Metrics",
        "",
        f"> Auto-generated from database. Last updated: {today}",
        f"> Source: `data/data.db` | Regenerate: `python scripts/generate_metrics.py`",
        "",
    ]

    # Run all registered section generators
    for section_fn in SECTIONS:
        try:
            section_lines = section_fn(conn)
            if section_lines:
                lines.extend(section_lines)
        except Exception as e:
            lines.append(f"<!-- Error in {section_fn.__name__}: {e} -->")
            lines.append("")

    # Data freshness table (auto-discovers all tables)
    lines.append("## Data Freshness")
    lines.append("| Source | Latest Record | Status |")
    lines.append("|--------|---------------|--------|")

    tables = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' "
        "AND name != 'collection_log' AND name NOT LIKE 'sqlite_%' "
        "ORDER BY name"
    ).fetchall()

    for t in tables:
        name = t["name"]
        try:
            row = conn.execute(f"SELECT MAX(date) as d FROM {name}").fetchone()
            if row and row["d"]:
                lines.append(f"| {name} | {row['d']} | Connected |")
            else:
                lines.append(f"| {name} | — | Empty |")
        except Exception:
            lines.append(f"| {name} | — | No date column |")

    lines.append("")
    return "\n".join(lines)


def main():
    """Generate key-metrics.md from the database."""
    if not DB_PATH.exists():
        print(f"Database not found at {DB_PATH}")
        print("Run collection first: python scripts/collect.py")
        return

    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row

    content = generate(conn)
    conn.close()

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(content)
    print(f"Key metrics written to: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
