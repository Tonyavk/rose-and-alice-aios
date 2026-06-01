# Explore: Monthly Client Reporting Agent

**Created:** 2026-05-20
**Status:** Explored
**Origin:** Automatically pull Meta, Google Ads, and LinkedIn campaign data per client and generate monthly reports ready for Tonya to review and send.

---

## Vision

Every month Tonya manually pulls campaign data from multiple ad platforms for up to 19 clients and formats it into reports. This system automates that entirely — on the 1st of each month it pulls data, generates a branded report per client using her existing template, and saves them ready to review and send. Estimated time saving: several hours per month.

## Problem Statement

Tonya manages paid ads across Meta, Google Ads, and LinkedIn for ~19 active clients (not all clients on all platforms). Monthly reporting is done manually — logging into each platform, pulling numbers, formatting a report, converting to PDF, and sending. At scale this is a significant time sink and a prime automation candidate.

## Proposed Solution

### What It Does
On the 1st of each month, automatically:
1. Reads a client config file to know which clients are active and which platforms they're on
2. Pulls the previous month's campaign data from Meta, Google Ads, and/or LinkedIn per client
3. Generates a `.docx` report per client using Tonya's existing template + a Gemini-written narrative
4. Saves all reports to `outputs/client-reports/YYYY-MM/` ready to review

### How It Works
1. `config/reporting-clients.yaml` — master list of clients with their platform account IDs
2. Collectors run per platform: `scripts/reporting/collect_meta.py`, `collect_google_ads.py`, `collect_linkedin.py`
3. Data stored in `data/data.db` (new tables: `meta_campaign_monthly`, `google_ads_monthly`, `linkedin_monthly`)
4. Report generator reads data + template → calls Gemini for narrative → writes `.docx`
5. LaunchAgent triggers on 1st of each month

### What It Produces
- One `.docx` per active client per month in `outputs/client-reports/YYYY-MM/ClientName.docx`
- Tonya opens in Google Docs → reviews → downloads as PDF → sends to client
- No auto-sending — human review step preserved

## Scope

### Minimum Viable Version (Phase 1)
Meta Ads + Google Ads collectors + report generator + scheduler.
Covers the majority of clients. LinkedIn added in Phase 2.

### Full Vision (Phase 2)
LinkedIn Ads collector added. All three platforms fully automated.

### Components

| Component | Description | Effort | Dependencies |
|-----------|-------------|--------|--------------|
| Client config file | `config/reporting-clients.yaml` — maps clients to account IDs + platforms | S | Tonya provides account IDs |
| Meta Ads collector | Pull spend, impressions, clicks, results per client via Marketing API | M | Meta long-lived access token |
| Google Ads collector | Pull same metrics via MCC using Google Ads API | M | Google Ads Developer Token |
| LinkedIn Ads collector | Pull same metrics via LinkedIn Marketing API | M | LinkedIn App credentials |
| Report generator | HTML → PDF per client, Claude API for commentary + summary | M | Template from Tonya, client logos |
| Monthly scheduler | LaunchAgent on 1st of month at 9am | S | All collectors working |

### Out of Scope
- Auto-sending reports to clients (Tonya reviews first)
- Per-client brand colours (consistent black/white + single accent across all reports)
- Real-time or weekly reporting (monthly only for now)

## Technical Considerations

**APIs needed:**
- Meta Marketing API — long-lived access token from Business Manager (~15 min setup)
- Google Ads API — Developer Token submitted, awaiting approval. Existing Google service account extended.
- LinkedIn Marketing API — LinkedIn App + OAuth2 (Phase 2)

**AI model:** Claude API (Anthropic — key already in .env) for plain-English metric commentary, industry benchmark context, and narrative summary. Web search step runs first each month to pull current industry benchmarks before Claude writes the report.

**Report format:** HTML → PDF (not .docx). Gives full visual control to match Tonya's template layout — big hero metrics, platform sections, client logo, summary narrative. Consistent black/white design with single accent colour across all clients.

**Client logos:** Stored in `config/client-logos/{client-name}.png`. Mapped per client in the config file. Tonya supplies logo files once; reports pick them up automatically.

**Output format:** `.docx` via `python-docx` library. Opens in Google Docs natively.

**Gemini:** Already configured. Used to write a 2-3 paragraph narrative per report ("Here's what happened this month, why it happened, and what we recommend").

**Database:** New tables added to existing `data/data.db` — consistent with DataOS pattern.

**Cost:** ~$0.05-0.20/month in Gemini API calls (one call per client per month).

## Connections
- Extends DataOS (same database, same collector pattern)
- Uses existing Gemini API key
- Client list from existing `client_list` table as source of truth
- Output feeds into Tonya's existing client communication workflow

## Before We Can Build — Tonya Needs to Provide
1. **Report template** ✅ — Vivéa quarterly report received, style confirmed
2. **Client platform mapping** — which clients are on which platforms + their account IDs
3. **Google Ads Developer Token** ✅ — submitted, awaiting approval
4. **Meta long-lived access token** — from Business Manager (~15 min setup)
5. **Client logos** — PNG format, one per client, dropped into `config/client-logos/`
6. **LinkedIn App credentials** — when ready for Phase 2

## Next Steps

**When ready to build:**
1. Tonya provides template + client account IDs
2. Apply for Google Ads Developer Token (do this now — takes 1-2 days)
3. Run: `/implement plans/explore-2026-05-20-client-reporting-agent.md`

Start with Phase 1 (Meta + Google Ads). LinkedIn slots in after.
