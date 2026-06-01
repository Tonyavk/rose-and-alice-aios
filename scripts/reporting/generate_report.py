"""
Reporting — Report Generator

Reads monthly ad data from the database, calls Claude for a narrative summary,
renders an HTML report, and optionally converts to PDF via WeasyPrint.

Usage:
    python scripts/reporting/generate_report.py --period 2026-04 --client vivea-skincare
    python scripts/reporting/generate_report.py --period 2026-04 --client vivea-skincare --html-only
"""

import sys
import base64
import argparse
from datetime import datetime, timezone
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(WORKSPACE_ROOT / "scripts"))
sys.path.insert(0, str(WORKSPACE_ROOT / "scripts" / "reporting"))

from dotenv import load_dotenv
load_dotenv(WORKSPACE_ROOT / ".env", override=True)

import re
from jinja2 import Template
import anthropic

from config import (
    get_client_by_slug, last_month_period, period_dates, period_label, get_creds
)
from db import get_connection, query_all
from collect_campaign_types import load as load_campaign_types

LOGOS_DIR = WORKSPACE_ROOT / "config" / "client-logos"
OUTPUT_BASE = WORKSPACE_ROOT / "outputs" / "client-reports"

# ---------------------------------------------------------------------------
# HTML template
# ---------------------------------------------------------------------------

REPORT_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{{ client_name }} — {{ period_label }}</title>
  <style>
    @page { size: A4; margin: 12mm 0; }
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body {
      font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
      color: #1a1a1a;
      background: #ffffff;
      font-size: 13px;
      line-height: 1.5;
    }

    /* ── Header ── */
    .header {
      padding: 24px 40px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      border-bottom: 3px solid #1a1a1a;
    }
    .logo-wrap { height: 80px; display: flex; align-items: center; }
    .logo-wrap img { max-height: 80px; max-width: 240px; object-fit: contain; }
    .logo-placeholder {
      font-size: 20px;
      font-weight: 800;
      letter-spacing: -0.5px;
      color: #1a1a1a;
    }
    .report-meta { text-align: right; }
    .report-meta h1 { font-size: 20px; font-weight: 700; letter-spacing: -0.3px; }
    .report-meta .period { font-size: 12px; color: #666; margin-top: 3px; }
    .report-meta .prepared { font-size: 10px; color: #999; margin-top: 2px; }

    /* ── Hero metrics ── */
    .hero {
      display: grid;
      grid-template-columns: repeat({{ hero_cols }}, 1fr);
      gap: 0;
      border-bottom: 2px solid #1a1a1a;
    }
    .metric {
      padding: 22px 28px;
      border-right: 1px solid #e8e8e8;
    }
    .metric:last-child { border-right: none; }
    .metric-value {
      font-size: 30px;
      font-weight: 800;
      letter-spacing: -1px;
      color: #1a1a1a;
      line-height: 1;
    }
    .metric-label {
      font-size: 10px;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.8px;
      color: #888;
      margin-top: 6px;
    }
    .metric-sub {
      font-size: 10px;
      color: #aaa;
      margin-top: 2px;
    }

    /* ── Platform sections ── */
    .section {
      padding: 18px 40px;
      border-bottom: 1px solid #ebebeb;
    }
    .section-header {
      display: flex;
      align-items: baseline;
      justify-content: space-between;
      margin-bottom: 10px;
    }
    .section-title {
      font-size: 15px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.6px;
    }
    .section-summary {
      font-size: 12px;
      color: #888;
    }

    table {
      width: 100%;
      border-collapse: collapse;
      font-size: 11px;
    }
    thead tr {
      background: #1a1a1a;
      color: #fff;
    }
    th {
      padding: 7px 8px;
      text-align: left;
      font-weight: 600;
      font-size: 10px;
      text-transform: uppercase;
      letter-spacing: 0.4px;
      white-space: nowrap;
    }
    th.num { text-align: right; }
    td {
      padding: 7px 8px;
      border-bottom: 1px solid #f0f0f0;
      color: #333;
    }
    td:first-child { white-space: nowrap; }
    td.num { text-align: right; font-variant-numeric: tabular-nums; white-space: nowrap; }
    tbody tr:hover td { background: #fafafa; }
    tbody tr:last-child td { border-bottom: none; }
    .no-data { padding: 24px 0; color: #aaa; font-style: italic; font-size: 12px; }


    /* ── Narrative ── */
    .narrative {
      background: #1a1a1a;
      color: #f0f0f0;
      padding: 20px 40px;
    }
    .narrative h2 {
      font-size: 10px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 1px;
      color: #888;
      margin-bottom: 10px;
    }
    .narrative p {
      font-size: 11px;
      line-height: 1.65;
      margin-bottom: 10px;
      color: #e0e0e0;
    }
    .narrative p:last-child { margin-bottom: 0; }

    /* ── Footer ── */
    .footer {
      padding: 14px 40px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      font-size: 10px;
      color: #bbb;
      border-top: 1px solid #ebebeb;
    }
    .footer strong { color: #888; }
  </style>
</head>
<body>

  <!-- Header -->
  <div class="header">
    <div class="logo-wrap">
      {% if logo_b64 %}
        <img src="data:image/png;base64,{{ logo_b64 }}" alt="{{ client_name }}">
      {% else %}
        <div class="logo-placeholder">{{ client_name }}</div>
      {% endif %}
    </div>
    <div class="report-meta">
      <h1>Monthly Performance Report</h1>
      <div class="period">{{ period_label }}</div>
      <div class="prepared">Prepared by Rose and Alice Creative</div>
    </div>
  </div>

  <!-- Hero metrics -->
  <div class="hero">
    {% for m in hero_metrics %}
    <div class="metric">
      <div class="metric-value">{{ m.value }}</div>
      <div class="metric-label">{{ m.label }}</div>
      {% if m.sub %}<div class="metric-sub">{{ m.sub }}</div>{% endif %}
    </div>
    {% endfor %}
  </div>

  <!-- Google Ads section -->
  {% if google_campaigns %}
  <div class="section">
    <div class="section-header">
      <div class="section-title">Google Ads</div>
      <div class="section-summary">
        {{ google_totals.impressions | format_int }} impressions &nbsp;·&nbsp;
        {{ google_totals.clicks | format_int }} clicks &nbsp;·&nbsp;
        ${{ google_totals.cost | format_2dp }}
      </div>
    </div>
    <table>
      <thead>
        <tr>
          <th>Campaign</th>
          <th class="num">Impressions</th>
          <th class="num">Clicks</th>
          <th class="num">CTR</th>
          <th class="num">Avg CPC</th>
          <th class="num">Cost</th>
          <th class="num">Conv.</th>
          <th class="num">All Conv.</th>
          <th class="num">AOV</th>
          <th class="num">ROAS</th>
        </tr>
      </thead>
      <tbody>
        {% for c in google_campaigns %}
        <tr>
          <td>{{ c.campaign_name }}</td>
          <td class="num">{{ c.impressions | format_int }}</td>
          <td class="num">{{ c.clicks | format_int }}</td>
          <td class="num">{{ c.ctr }}%</td>
          <td class="num">${{ c.avg_cpc | format_2dp }}</td>
          <td class="num">${{ c.cost | format_2dp }}</td>
          <td class="num">{{ c.conversions | format_conv }}</td>
          <td class="num">{{ c.all_conversions | format_conv }}</td>
          <td class="num">{% if c.aov %}${{ c.aov | format_2dp }}{% else %}—{% endif %}</td>
          <td class="num">{% if c.roas > 0 %}{{ c.roas }}x{% else %}—{% endif %}</td>
        </tr>
        {% endfor %}
      </tbody>
    </table>
  </div>
  {% endif %}

  <!-- Meta Ads section -->
  {% if meta_campaigns %}
  <div class="section">
    <div class="section-header">
      <div class="section-title">Meta Ads</div>
      <div class="section-summary">
        {{ meta_totals.impressions | format_int }} impressions &nbsp;·&nbsp;
        {{ meta_totals.clicks | format_int }} clicks &nbsp;·&nbsp;
        ${{ meta_totals.spend | format_2dp }}
      </div>
    </div>
    <table>
      <thead>
        <tr>
          <th>Campaign</th>
          <th class="num">Impressions</th>
          <th class="num">Clicks</th>
          <th class="num">CTR</th>
          <th class="num">CPC</th>
          <th class="num">Spend</th>
          <th class="num">Results</th>
          <th class="num">AOV</th>
          <th class="num">ROAS</th>
        </tr>
      </thead>
      <tbody>
        {% set ns = namespace(last_campaign='') %}
        {% for c in meta_campaigns %}
        {% if c.adset_name and c.campaign_name != ns.last_campaign %}
        {% set ns.last_campaign = c.campaign_name %}
        <tr style="background:#f5f5f5;">
          <td colspan="9" style="font-weight:700;font-size:11px;padding:6px 8px;border-bottom:1px solid #ddd;">
            {{ c.campaign_name }}
          </td>
        </tr>
        {% endif %}
        <tr>
          <td style="{% if c.adset_name %}padding-left:20px;{% endif %}">
            {{ c.adset_name if c.adset_name else c.campaign_name }}
          </td>
          <td class="num">{{ c.impressions | format_int }}</td>
          <td class="num">{{ c.clicks | format_int }}</td>
          <td class="num">{{ c.ctr }}%</td>
          <td class="num">${{ c.cpc | format_2dp }}</td>
          <td class="num">${{ c.spend | format_2dp }}</td>
          <td class="num">
            {% if c.results > 0 %}{{ c.results }} {{ c.result_type }}{% else %}—{% endif %}
          </td>
          <td class="num">{% if c.aov %}${{ c.aov | format_2dp }}{% else %}—{% endif %}</td>
          <td class="num">{% if c.roas > 0 %}{{ c.roas }}x{% else %}—{% endif %}</td>
        </tr>
        {% endfor %}
      </tbody>
    </table>
  </div>
  {% endif %}

  {% if not google_campaigns and not meta_campaigns %}
  <div class="section">
    <p class="no-data">No campaign data available for this period.</p>
  </div>
  {% endif %}

  <!-- Narrative -->
  {% if narrative %}
  <div class="narrative">
    <h2>Performance Summary</h2>
    {% for para in narrative_paragraphs %}
    <p>{{ para | safe }}</p>
    {% endfor %}
  </div>
  {% endif %}

  <!-- Footer -->
  <div class="footer">
    <div><strong>Rose and Alice Creative</strong> &nbsp;·&nbsp; roseandalicecreative.co.nz</div>
    <div>{{ period_label }} &nbsp;·&nbsp; Generated {{ generated_date }}</div>
  </div>

</body>
</html>"""


# ---------------------------------------------------------------------------
# Data helpers
# ---------------------------------------------------------------------------

def _load_logo_b64(client_slug):
    """Load client logo as base64 string, or return None."""
    for ext in ("png", "jpg", "jpeg", "svg"):
        path = LOGOS_DIR / f"{client_slug}.{ext}"
        if path.exists():
            data = path.read_bytes()
            return base64.b64encode(data).decode()
    return None


def _load_google_data(conn, client_slug, period):
    return query_all(
        conn,
        "SELECT * FROM google_ads_monthly WHERE client_slug = ? AND period = ? "
        "ORDER BY cost DESC",
        (client_slug, period),
    )


def _load_meta_data(conn, client_slug, period):
    return query_all(
        conn,
        "SELECT * FROM meta_campaign_monthly WHERE client_slug = ? AND period = ? "
        "ORDER BY spend DESC",
        (client_slug, period),
    )


def _totals(rows, spend_key):
    return {
        "impressions": sum(r["impressions"] for r in rows),
        "clicks": sum(r["clicks"] for r in rows),
        spend_key: sum(r[spend_key] for r in rows),
    }


def _build_hero_metrics(google_rows, meta_rows):
    """Build the top hero metrics row from combined data."""
    total_spend = sum(r["cost"] for r in google_rows) + sum(r["spend"] for r in meta_rows)
    total_impr = sum(r["impressions"] for r in google_rows) + sum(r["impressions"] for r in meta_rows)
    total_clicks = sum(r["clicks"] for r in google_rows) + sum(r["clicks"] for r in meta_rows)

    overall_ctr = round(total_clicks / total_impr * 100, 2) if total_impr > 0 else 0

    g_conv = sum(r.get("all_conversions") or r.get("conversions") or 0 for r in google_rows)
    m_results = sum(r["results"] for r in meta_rows)

    metrics = []

    # Conversions first
    if g_conv > 0 or m_results > 0:
        metrics.append({
            "value": f"{int(g_conv + m_results)}",
            "label": "Conversions / Results",
            "sub": None,
        })

    metrics.append({"value": f"{total_impr:,}", "label": "Impressions", "sub": None})
    metrics.append({"value": f"{total_clicks:,}", "label": "Clicks", "sub": f"{overall_ctr}% CTR"})
    metrics.append({"value": f"${total_spend:,.0f}", "label": "Total Spend", "sub": "All platforms"})

    # Only show ROAS hero metric when we have real Meta purchase value data
    purchase_value = sum(r.get("purchase_value", 0) or 0 for r in meta_rows)
    if purchase_value > 0 and total_spend > 0:
        roas = round(purchase_value / total_spend, 2)
        metrics.append({"value": f"{roas}x", "label": "ROAS", "sub": "Blended"})

    return metrics


# ---------------------------------------------------------------------------
# Claude narrative
# ---------------------------------------------------------------------------

def _build_narrative_prompt(client, period, google_rows, meta_rows, campaign_types=None):
    pl = period_label(period)
    campaign_types = campaign_types or {}

    # Campaign intent context
    meta_types   = campaign_types.get("meta", "")
    google_types = campaign_types.get("google", "")
    intent_lines = []
    if meta_types:
        intent_lines.append(f"  Meta campaign types: {meta_types}")
    if google_types:
        intent_lines.append(f"  Google campaign types: {google_types}")
    intent_block = (
        "Campaign intent:\n" + "\n".join(intent_lines) + "\n"
        if intent_lines else ""
    )

    g_summary = ""
    if google_rows:
        total_cost   = sum(r["cost"] for r in google_rows)
        total_impr   = sum(r["impressions"] for r in google_rows)
        total_clicks = sum(r["clicks"] for r in google_rows)
        total_conv   = sum(r.get("all_conversions") or r.get("conversions") or 0 for r in google_rows)
        g_summary = (
            f"Google Ads — {len(google_rows)} campaigns, "
            f"{total_impr:,} impressions, {total_clicks:,} clicks, "
            f"${total_cost:,.2f} spend, {total_conv:.1f} all conversions\n"
        )
        for r in google_rows:
            all_conv = r.get("all_conversions") or r.get("conversions") or 0
            g_summary += (
                f"  • {r['campaign_name']}: {r['impressions']:,} impr, "
                f"{r['clicks']:,} clicks, ${r['cost']:,.2f}, "
                f"{r['ctr']}% CTR, ${r['avg_cpc']} CPC, {all_conv:.1f} all conv\n"
            )

    m_summary = ""
    if meta_rows:
        total_spend  = sum(r["spend"] for r in meta_rows)
        total_impr   = sum(r["impressions"] for r in meta_rows)
        total_clicks = sum(r["clicks"] for r in meta_rows)
        m_summary = (
            f"Meta Ads — {len(meta_rows)} campaigns, "
            f"{total_impr:,} impressions, {total_clicks:,} clicks, "
            f"${total_spend:,.2f} spend\n"
        )
        for r in meta_rows:
            label = r.get("adset_name") or r["campaign_name"]
            parent = f" [{r['campaign_name']}]" if r.get("adset_name") else ""
            m_summary += (
                f"  • {label}{parent}: {r['impressions']:,} impr, "
                f"{r['clicks']:,} clicks, ${r['spend']:,.2f}, "
                f"{r['ctr']}% CTR"
            )
            if r["results"] > 0:
                m_summary += f", {r['results']} {r['result_type']}"
            m_summary += "\n"

    return f"""You are Tonya Knight, owner of Rose and Alice Creative, a New Zealand digital marketing agency. You are writing the performance summary section of a monthly report to send directly to your client. Write in your own voice — confident, clear, and client-friendly.

Client: {client['name']}
Industry: {client.get('industry', 'N/A')}
Campaign objective: {client.get('campaign_objective', 'N/A')}
Reporting period: {pl}
{intent_block}
Performance data:
{g_summary}{m_summary}

STRICT RULES — follow exactly:
- Use ONLY the exact campaign names and ad set names from the data above. Do not rename, relabel, reinterpret, or invent any campaign names.
- Cover EVERY campaign and ad set listed in the data — do not skip any.
- Do not mention any campaign, location, or result that does not appear in the data.
- Use the campaign intent context to understand the PURPOSE of each campaign, but do not let it lead you to mention things not in the data.

Write a 3-paragraph performance summary:

Paragraph 1 — Combined overview and platform breakdown: Total combined impressions, clicks, and spend across all platforms. Then break down what each platform contributed. Name each campaign/ad set specifically using its exact name from the data.

Paragraph 2 — Key highlights and plain-English metric translation: Cover the most important results across ALL campaigns and ad sets in the data. For Google Ads, use the all conversions figure. Translate metrics into plain English (e.g. "roughly 1 in 29 people who saw the ad clicked through"). Be honest about any underperformer.

Paragraph 3 — Recommendations: 2-3 specific actions for next month grounded in what the data actually shows. First person ("I'll", "I'd recommend", "we should").

Tone: Direct, warm, professional. Written as Tonya speaking to her client. No jargon without explanation. No bullet points — flowing paragraphs only. Keep each paragraph to 3 sentences maximum."""


def _get_narrative(client, period, google_rows, meta_rows, api_key, campaign_types=None):
    """Call Claude to generate the report narrative, with retry on overload."""
    if not api_key:
        return None

    import time
    prompt = _build_narrative_prompt(client, period, google_rows, meta_rows, campaign_types)
    ai_client = anthropic.Anthropic(api_key=api_key)

    for attempt in range(3):
        try:
            msg = ai_client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=550,
                messages=[{"role": "user", "content": prompt}],
            )
            return msg.content[0].text.strip()
        except anthropic.APIStatusError as e:
            if e.status_code == 529 and attempt < 2:
                wait = 15 * (attempt + 1)
                print(f"  Claude API busy, retrying in {wait}s...", file=sys.stderr)
                time.sleep(wait)
            else:
                print(f"  Warning: Claude narrative failed — {e}", file=sys.stderr)
                return None
        except Exception as e:
            print(f"  Warning: Claude narrative failed — {e}", file=sys.stderr)
            return None


# ---------------------------------------------------------------------------
# Jinja2 filters
# ---------------------------------------------------------------------------

def _make_template():
    from jinja2 import Environment

    env = Environment()
    env.filters["format_int"] = lambda v: f"{int(v or 0):,}"
    env.filters["format_2dp"] = lambda v: f"{float(v or 0):,.2f}"
    env.filters["format_conv"] = lambda v: f"{float(v or 0):.1f}" if float(v or 0) > 0 else "—"

    return env.from_string(REPORT_TEMPLATE)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate(client_slug, period=None, html_only=False, conn=None, use_saved_summary=False):
    """
    Generate a report for one client.

    Returns the path to the generated file (PDF or HTML).
    """
    if period is None:
        period = last_month_period()

    client = get_client_by_slug(client_slug)
    if not client:
        raise ValueError(f"Client '{client_slug}' not found in reporting-clients.yaml")

    creds = get_creds()
    close_conn = False
    if conn is None:
        conn = get_connection()
        close_conn = True

    try:
        google_rows = _load_google_data(conn, client_slug, period)
        meta_rows = _load_meta_data(conn, client_slug, period)
    finally:
        if close_conn:
            conn.close()

    # Determine output paths early (needed for saved summary logic)
    out_dir = OUTPUT_BASE / period
    out_dir.mkdir(parents=True, exist_ok=True)
    summary_path = out_dir / f"{client_slug}-summary.txt"

    # Get narrative — from saved file or Claude
    if use_saved_summary and summary_path.exists():
        narrative = summary_path.read_text(encoding="utf-8").strip()
        print(f"  Using saved summary: {summary_path}", file=sys.stderr)
    else:
        all_campaign_types = load_campaign_types()
        client_campaign_types = all_campaign_types.get(client_slug, {})
        narrative = _get_narrative(client, period, google_rows, meta_rows, creds["anthropic_api_key"], client_campaign_types)
        if narrative:
            summary_path.write_text(narrative, encoding="utf-8")
            print(f"  Summary saved for review: {summary_path}", file=sys.stderr)

    # Clean markdown from narrative for HTML rendering
    if narrative:
        # Remove heading lines (##, #, etc.)
        narrative = re.sub(r"^#+\s+.*\n?", "", narrative, flags=re.MULTILINE)
        # Convert **bold** to <strong>
        narrative = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", narrative)
        narrative = narrative.strip()
    logo_b64 = _load_logo_b64(client_slug)
    hero_metrics = _build_hero_metrics(google_rows, meta_rows)

    google_totals = _totals(google_rows, "cost") if google_rows else None
    meta_totals = _totals(meta_rows, "spend") if meta_rows else None

    # Augment rows with computed AOV
    google_campaigns = []
    for r in google_rows:
        row = dict(r)
        conv_val = float(row.get("conv_value") or 0)
        convs = float(row.get("conversions") or 0)
        row["aov"] = round(conv_val / convs, 2) if conv_val > 0 and convs > 0 else None
        google_campaigns.append(row)

    meta_campaigns = []
    for r in meta_rows:
        row = dict(r)
        pv = float(row.get("purchase_value") or 0)
        results = float(row.get("results") or 0)
        row["aov"] = round(pv / results, 2) if pv > 0 and results > 0 else None
        meta_campaigns.append(row)

    # Combined totals for breakdown section
    combined_totals = None
    if google_totals or meta_totals:
        combined_totals = {
            "impressions": (google_totals["impressions"] if google_totals else 0)
                           + (meta_totals["impressions"] if meta_totals else 0),
            "clicks": (google_totals["clicks"] if google_totals else 0)
                      + (meta_totals["clicks"] if meta_totals else 0),
            "spend": (google_totals["cost"] if google_totals else 0)
                     + (meta_totals["spend"] if meta_totals else 0),
        }

    context = {
        "client_name": client["name"],
        "period_label": period_label(period),
        "logo_b64": logo_b64,
        "hero_metrics": hero_metrics,
        "hero_cols": len(hero_metrics),
        "google_campaigns": google_campaigns,
        "google_totals": google_totals,
        "meta_campaigns": meta_campaigns,
        "meta_totals": meta_totals,
        "narrative": narrative,
        "narrative_paragraphs": narrative.split("\n\n") if narrative else [],
        "generated_date": datetime.now().strftime("%d %B %Y"),
    }

    html = _make_template().render(**context)

    html_path = out_dir / f"{client_slug}.html"
    html_path.write_text(html, encoding="utf-8")

    if html_only:
        return html_path

    # Attempt PDF via headless Chrome, fall back to HTML
    pdf_path = out_dir / f"{client_slug}.pdf"
    chrome_paths = [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
        "/usr/bin/google-chrome",
        "/usr/bin/chromium-browser",
    ]
    chrome = next((p for p in chrome_paths if Path(p).exists()), None)

    if chrome:
        import subprocess
        try:
            result = subprocess.run(
                [
                    chrome,
                    "--headless=new",
                    "--disable-gpu",
                    "--no-sandbox",
                    "--run-all-compositor-stages-before-draw",
                    f"--print-to-pdf={pdf_path}",
                    "--no-pdf-header-footer",
                    str(html_path),
                ],
                capture_output=True,
                timeout=30,
            )
            if pdf_path.exists():
                return pdf_path
        except Exception as e:
            print(f"  Chrome PDF failed ({e}) — HTML report saved instead", file=sys.stderr)
    else:
        print("  No PDF renderer found — HTML report saved. Open in Chrome → Print → Save as PDF",
              file=sys.stderr)

    return html_path


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate a client report")
    parser.add_argument("--period", default=None, help="YYYY-MM (default: last month)")
    parser.add_argument("--client", required=True, help="Client slug from reporting-clients.yaml")
    parser.add_argument("--html-only", action="store_true", help="Skip PDF, save HTML only")
    args = parser.parse_args()

    print(f"Generating report for {args.client} ({args.period or last_month_period()})...")
    try:
        path = generate(args.client, period=args.period, html_only=args.html_only)
        print(f"Report saved: {path}")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
