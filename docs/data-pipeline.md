# System: DataOS — Data Collection Pipeline

> Collects daily business metrics from Xero, Google Sheets, and Mailchimp into a local SQLite database. Generates key-metrics.md for /prime to load each session.

## Architecture

```
.env + credentials/ --> collect.py (orchestrator)
                            |
          ┌─────────────────┼──────────────────┐
          ▼                 ▼                  ▼
collect_xero.py   collect_clients.py  collect_mailchimp.py
(revenue/invoices) (client tracker)   (email stats)
          └─────────────────┼──────────────────┘
                            ▼
                      data/data.db (SQLite)
                            ▼
                 generate_metrics.py
                            ▼
               context/group/key-metrics.md
```

## Key Files

| File | Purpose |
|------|---------|
| `scripts/collect.py` | Orchestrator — discovers and runs all `collect_*.py` files |
| `scripts/collect_xero.py` | Pulls revenue, invoices, outstanding amounts from Xero |
| `scripts/collect_clients.py` | Reads client tracker & leads from Google Sheets |
| `scripts/collect_mailchimp.py` | Pulls subscriber stats and campaign performance |
| `scripts/collect_google_analytics.py` | Pulls daily sessions, users, page views, traffic sources from GA4 |
| `scripts/collect_fx_rates.py` | Daily NZD/USD and other exchange rates (no auth needed) |
| `scripts/generate_metrics.py` | Reads database → writes `context/group/key-metrics.md` |
| `scripts/db.py` | SQLite connection manager and query helpers |
| `scripts/xero_auth.py` | One-time OAuth setup for Xero (run once, stores tokens) |
| `scripts/ga4_auth.py` | One-time OAuth setup for Google Analytics (run once, stores tokens) |
| `data/data.db` | SQLite database (gitignored) |
| `context/group/key-metrics.md` | Auto-generated metrics file loaded by /prime |
| `credentials/xero_tokens.json` | Xero OAuth tokens (gitignored, refreshed automatically) |
| `config/com.aios.data-collect.plist` | macOS launchd job — runs pipeline at 6am daily |

## How It Works

1. `collect.py` auto-discovers all `collect_*.py` files in `scripts/`
2. Each collector calls an external API and returns `{"status": "success", "data": {...}}`
3. If credentials are missing the collector returns `"status": "skipped"` — pipeline continues
4. Results are written to SQLite tables via each collector's `write()` function
5. After all collectors run, `generate_metrics.py` reads the DB and rewrites `key-metrics.md`
6. launchd runs this at 6am every morning automatically

## Configuration

| Variable | Purpose | Required |
|----------|---------|----------|
| `XERO_CLIENT_ID` | Xero OAuth app client ID | Yes (Xero) |
| `XERO_CLIENT_SECRET` | Xero OAuth app secret | Yes (Xero) |
| `GOOGLE_SHEET_ID` | Client tracker spreadsheet ID | Yes (Google Sheets) |
| `GOOGLE_SHEET_TAB` | Tab name in the spreadsheet | Yes (Google Sheets) |
| `GOOGLE_SERVICE_ACCOUNT_JSON` | Path to service account credentials | Yes (Google Sheets) |
| `MAILCHIMP_API_KEY` | Mailchimp API key | Yes (Mailchimp) |
| `MAILCHIMP_SERVER` | Mailchimp server prefix (e.g. `us21`) | Yes (Mailchimp) |

## Common Operations

**Run all collectors manually:**
```bash
cd /Users/tonyak/Documents/aios-starter-kit
.venv/bin/python scripts/collect.py
```

**Run a single collector:**
```bash
.venv/bin/python scripts/collect.py --sources xero
```

**Regenerate key-metrics.md only:**
```bash
.venv/bin/python scripts/generate_metrics.py
```

**Re-authenticate Xero (if token expires after 60 days unused):**
```bash
.venv/bin/python scripts/xero_auth.py
```

**Check automation logs:**
```bash
cat data/collect.log
```

## Database Tables

| Table | Collector | What it stores |
|-------|-----------|----------------|
| `xero_daily` | xero | Revenue MTD, last month, outstanding invoices |
| `xero_invoices` | xero | Individual invoice records |
| `client_snapshot` | clients | Daily totals: active clients, invoiced, leads |
| `client_list` | clients | Per-client status snapshot |
| `leads_list` | clients | Leads pipeline with notes |
| `mailchimp_snapshot` | mailchimp | Subscriber count, open/click rates |
| `mailchimp_campaigns` | mailchimp | Recent campaign performance |
| `ga4_daily` | google_analytics | Daily sessions, users, page views, engagement |
| `ga4_sources` | google_analytics | Top traffic sources (source/medium breakdown) |
| `fx_rates` | fx_rates | Daily exchange rates |

## Dependencies

- **Depends on:** `.env` credentials, `credentials/` folder (gitignored), Python venv
- **Used by:** `/prime` (loads key-metrics.md), any session that queries `data/data.db`

## History

| Date | Change |
|------|--------|
| 2026-05-11 | Initial install — Xero, Google Sheets (clients), Mailchimp, FX rates |
| 2026-05-11 | Added Google Analytics (GA4) collector via OAuth |
