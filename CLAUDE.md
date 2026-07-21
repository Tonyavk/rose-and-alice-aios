# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## What This Is

This is **Tonya Knight's AIOS workspace** for Rose and Alice Creative — a New Zealand-based digital marketing business. This workspace is an AI Operating System built to help Tonya reduce manual workload, improve delivery efficiency, and grow revenue without hiring.

**This file (CLAUDE.md) is the foundation.** It is automatically loaded at the start of every session. Keep it current — it is the single source of truth for how Claude should understand and operate within this workspace.

> From the AAA Accelerator — the #1 AI business launch & AIOS program. [aaaaccelerator.com](https://aaaaccelerator.com)

---

## The Claude-User Relationship

Claude operates as an **agent assistant** with access to the workspace folders, context files, commands, and outputs. The relationship is:

- **User**: Tonya Knight, founder of Rose and Alice Creative. Defines goals around marketing delivery, efficiency, and business growth. Directs work through commands and direct requests.
- **Claude**: Reads context, understands Tonya's objectives, executes commands, produces outputs, and maintains workspace consistency.

Claude should always orient itself through `/prime` at session start, then act with full awareness of who Tonya is, what she's trying to achieve, and how this workspace supports that.

**Tone guidance:** Tonya values concise, direct, practical communication. No fluff. No unnecessary explanations. Results-focused outputs only.

---

## AIOS Mission

You are helping a business owner build an **AI Operating System (AIOS)** — an autonomous intelligence layer wrapped around their entire business. Everything in this workspace serves that goal.

### The Problem: The Operator Trap
Most business owners are stuck working IN their business — firefighting, admin, managing people, checking dashboards, sitting in meetings just to stay informed. 80% of bandwidth goes to "must-dos." Nothing left for growth, strategy, or the life they actually wanted. The old model says hire more people, buy more tools, work more hours. AIOS says the answer is less — less manual work, less people needed, less time in operations. More bandwidth for the work that matters.

### The Solution: Five Layers
The AIOS gives it back — one layer at a time:
1. **Context** — Your AI understands the business (strategy, team, processes, history)
2. **Data** — Your AI sees the numbers in real-time (collectors pull from your actual data sources daily)
3. **Intelligence** — Your AI watches everything (meetings, messages, signals) and synthesizes into a daily brief
4. **Automate** — Audit every task, score each one, automate them away one by one. Each task automated = bandwidth recovered.
5. **Build** — Freed bandwidth applied to growth, new initiatives, or life. Work ON the business, not IN it.

### Five Principles
1. **Just Ask** — If you can describe it in plain English, Claude can build it. Don't self-censor. Ask for the impossible.
2. **Talk, Don't Type** — Voice-first. Hold FN, speak for 60 seconds, let Claude format it. 3x faster than typing.
3. **Layers, Not Leaps** — One layer at a time. Each independently valuable. Through gradual exposure, you become technical without even trying.
4. **Build for Scale & Security** — Human-in-the-loop by default. Your data stays local. Plan before you build.
5. **Borrow Before You Build** — 80% modules, 20% custom. Check the library before building from scratch.

### Three KPIs
These are how you know your AIOS is working:
- **Away-From-Desk Autonomy** — Hours per day you can step away and nothing falls apart. Target: business runs while you sleep.
- **Task Automation %** — Percentage of recurring tasks automated. Use the Task Audit (`context/task-audit.md`) as your scoreboard.
- **Revenue Per Employee** — Total revenue ÷ team members. Not bigger companies — leaner, faster, more profitable ones.

### How You Should Help
- Be patient. Assume the user is non-technical unless told otherwise.
- Explain what you're doing in plain English BEFORE doing it.
- Celebrate wins — every module installed, every task automated is real progress toward freedom.
- When suggesting solutions, check existing modules and the community first (Borrow Before You Build).
- Keep the three KPIs in mind — every automation should move at least one KPI.
- Never dump error logs or technical jargon. Find the problem, explain it simply, fix it.

---

## Workspace Structure

```
.
├── CLAUDE.md                # This file — core context, always loaded
├── .env                     # API keys and credentials (gitignored, never commit)
├── .claude/
│   └── commands/            # Slash commands Claude can execute
│       ├── prime.md         # /prime — session initialization
│       ├── install.md       # /install — install an AIOS module
│       ├── create-plan.md   # /create-plan — create implementation plans
│       ├── implement.md     # /implement — execute plans
│       └── share.md         # /share — package systems for sharing
├── context/                 # Background context about the user and business
│   ├── business-info.md     # What the business does
│   ├── personal-info.md     # Who you are, your role
│   ├── strategy.md          # Current priorities and goals
│   ├── current-data.md      # Key metrics and current state
│   └── import/              # Drop documents here for Claude to analyze
├── module-installs/         # AIOS modules — drop module folders here, install with /install
├── plans/                   # Implementation plans created by /create-plan
├── outputs/                 # Work products and deliverables
├── reference/               # Templates, examples, reusable patterns
├── scripts/                 # Automation scripts (added by modules)
└── shares/                  # Packaged systems for sharing (created by /share)
```

**Key directories:**

| Directory          | Purpose                                                                                |
| ------------------ | -------------------------------------------------------------------------------------- |
| `context/`         | Who you are, your business, current priorities, strategies. Read by `/prime`.           |
| `context/import/`  | Drop any docs here (business plans, ChatGPT exports, etc.) for Claude to analyze.      |
| `module-installs/` | AIOS modules go here. Install them with `/install module-installs/{module-name}`.      |
| `plans/`           | Detailed implementation plans. Created by `/create-plan`, executed by `/implement`.    |
| `outputs/`         | Deliverables, analyses, reports, and work products.                                    |
| `reference/`       | Helpful docs, templates and patterns to assist in various workflows.                   |
| `scripts/`         | Automation scripts — added by modules as you install them.                             |
| `shares/`          | Packaged systems for sharing. Created by `/share`, ready to hand off.                  |

---

## Commands

### /install [module-path]

**Purpose:** Install an AIOS module into this workspace.

Point it at a module folder in `module-installs/` and Claude walks you through the guided setup. Each module adds a new capability to your AIOS.

Example: `/install module-installs/context-os`

### /prime

**Purpose:** Initialize a new session with full context awareness.

Run this at the start of every session. Claude will:

1. Read CLAUDE.md and context files
2. Summarize understanding of the user, workspace, and goals
3. Confirm readiness to assist

### /create-plan [request]

**Purpose:** Create a detailed implementation plan before making changes.

Use when adding new functionality, commands, scripts, or making structural changes. Produces a thorough plan document in `plans/` that captures context, rationale, and step-by-step tasks.

Example: `/create-plan add a competitor analysis command`

### /implement [plan-path]

**Purpose:** Execute a plan created by /create-plan.

Reads the plan, executes each step in order, validates the work, and updates the plan status.

Example: `/implement plans/2026-01-28-competitor-analysis-command.md`

### /explore [idea]

**Purpose:** Interactive feature discovery. Takes an idea and walks you through shaping it into a clear, scoped concept ready to build.

Runs through 5 stages: Discovery → Research → Shape → Scope → Output. Produces a feature doc in `plans/` ready for `/implement`.

### /brainstorm [topic]

**Purpose:** Workspace scanner and opportunity finder. Scans your tasks, processes, and current setup to find manual work that could be automated.

Ranks opportunities by impact and feasibility, deep-dives the top picks, and points you to `/explore` or `/implement` for the next step. Run without arguments to scan everything, or with a topic to focus on a specific area.

### /share [system or feature]

**Purpose:** Package a system or feature from your workspace for sharing.

Deep-dives the code first to fully understand it, then produces a self-contained, beginner-friendly package with a Claude-guided installer (INSTALL.md + README.md + scripts). The recipient gives the folder to Claude Code and says "read INSTALL.md and set this up" — Claude walks them through everything step by step. Runs a 6-stage interactive flow: Research → Scope → Frame → Write → Validate → Deliver. Outputs to `shares/`.

Example: `/share the daily brief system`

---

## Installed Systems

### DataOS — Live Data Pipeline
- Database: `data/data.db` (SQLite)
- Collectors: Xero, Google Sheets (clients), Mailchimp, GA4
- Schedule: Daily at 6am via `~/Library/LaunchAgents/com.aios.data-collect.plist`
- Key metrics auto-generated to `context/group/key-metrics.md` after each run
- Run manually: `python3 scripts/collect.py`

### ProductivityOS — GTD Task Management
- Files: `gtd/` (dashboard, inbox, projects, next-actions, waiting-for, someday-maybe, areas)
- Commands: `/process` (empty inbox), `/review` (weekly review)
- Contexts: @me, @claude, @calls, @team, @errands, @think, @record
- Refresh dashboard: `python3 scripts/refresh_dashboard.py`
- Capture to inbox: `python3 scripts/inbox_writer.py "task text"`

### IntelOS — Meeting & Slack Intelligence
- Database: `data/data.db` (same DB — tables: `meetings`, `slack_messages`, `staff_registry`)
- Scripts: `scripts/intel/`
- Meeting recorder: **Fireflies connected** (July 2026) — `FIREFLIES_API_KEY` in `.env`, transcripts land in the `meetings` table via `collect_all.py`
- Slack: not connected yet
- Search meetings: `python3 -c "import sys; sys.path.insert(0,'scripts/intel'); from db import get_connection, search_meetings; conn=get_connection(); print(search_meetings(conn,'keyword'))"`
- Run collection: `python3 scripts/intel/collect_all.py`

### Daily Brief — Morning Intelligence Report
- Preset: Solo Operator (short, punchy — 3 sections)
- Schedule: Daily at 8am via `~/Library/LaunchAgents/com.aios.daily-brief.plist`
- Delivery: Telegram (pending live test when Telegram bot is confirmed)
- Briefs saved to: `outputs/daily-brief/{date}.md`
- Funnel map: `context/funnel.md`
- Run manually: `python3 scripts/daily_brief.py`
- Dry run (no send): `python3 scripts/daily_brief.py --test`

### ReportingOS — Monthly Client Reports
- Scripts: `scripts/reporting/`
- Client config: `config/reporting-clients.yaml` (add clients here — slug, `report_type`, Meta account ID, Google Ads customer ID; optional `active_only: true` under a client's `google_ads` block limits the report to currently-enabled campaigns, and optional `conversion_category: SUBMIT_LEAD_FORM` makes the All Conv. column count only that goal category — both used for Alden)
- Report types: each client is `report_type: shopping` or `report_type: brand` — filenames carry the type as a suffix so the two kinds never collide
- Logos: `config/client-logos/{slug}.png`
- Output: `outputs/client-reports/YYYY-MM/{slug}-{type}.pdf` (e.g. `vivea-skincare-shopping.pdf`)
- Narrative (editable): `outputs/client-reports/YYYY-MM/{slug}-{type}-summary.txt` — edit this before finalising

**Brand reports** (built out — fit on one page, titled "Digital Marketing Report"):
- Google: pulled at **ad-group level**, shown campaign → ad group; columns Impressions · Clicks · Avg CPC · All Conv. · Cost/Conv. · Cost, plus grand-total row and a plain-English metric key
- Meta: pulled at **ad-set level**, shown campaign → ad set (alphabetical); columns Reach · Landing Page Views · Cost/Landing Page · Amount Spent · Results · Cost/Result, plus grand-total row
- Hero: Website Views (Google clicks + Meta landing page views) · Conversions · Total Spend

**Shopping reports** (built out — same one-page polish, ecommerce focus):
- Google: **ad-group level**; columns Impressions · Clicks · All Conv. · All Conv. Value · Cost/All Conv. · Cost, plus grand-total row and metric key
- Meta: **ad-set level**; columns Reach · Website Purchases · Avg. Purchase Value · Cost/Purchase · Amount Spent, plus grand-total row
- Hero: Purchases · AOV · Total Spend · ROAS
- Grey section-summary lines hidden; summary uses ecommerce framing (revenue/ROAS/purchases)

**Both types:**
- Summary: factual **month-over-month** comparison from the database + a clearly-hedged general industry guide + one positive highlight + two short first-person (Tonya's voice) recommendations — one concrete move, one positive/observational; plain NZ English, no negatives, no sensationalism, no em dashes
- Single-ad-group / single-ad-set campaigns collapse to one row; campaigns with multiple keep the indented grouping
- PMax caveat: Performance Max campaigns have no ad groups, so they drop out of the ad-group Google view

**Workflow (each month):**
1. Run: `python scripts/reporting/run_reports.py --period 2026-05 --client vivea-skincare`
2. Edit the narrative: `outputs/client-reports/2026-05/vivea-skincare-shopping-summary.txt`
3. Finalise PDF: `python scripts/reporting/run_reports.py --no-collect --finalize --client vivea-skincare --period 2026-05`

**Flags:** `--period YYYY-MM` · `--client slug` · `--report-type shopping|brand` (run all clients of one type) · `--no-collect` (skip data pull) · `--finalize` (use saved txt) · `--html-only`

**Credentials:** `GOOGLE_ADS_*` and `META_ACCESS_TOKEN` in `.env` — Meta token expires every ~60 days, regenerate at Meta Business Manager

**Monthly automation:** `com.aios.monthly-reports` (launchd) runs `scripts/reporting/monthly_run.py` on the **1st of each month at 12pm** — collects last month, generates all 12 drafts, and emails Tonya that they're staged for review (does NOT finalise). Email via SMTP (`SMTP_*` / `REPORT_NOTIFY_TO` in `.env`, Gmail/Workspace app password). Test email: `.venv/bin/python scripts/reporting/monthly_run.py --email-test`. Plist source: `config/com.aios.monthly-reports.plist`.

---

## Context Summary

**Business:** Rose and Alice Creative — NZ digital marketing (paid ads, strategy, content, SEO, email, UX)
**Role:** Tonya Knight, founder and sole operator
**Current focus:** Double revenue from $10k/month to $20k/month; reduce manual workload through AI and better systems
**Key metric to watch:** Monthly revenue and active client count
**Biggest constraint:** Growing income without increasing hours or hiring

---

## Getting Started

**First time?** Start here:

1. Run `/install module-installs/context-os` — this builds your context layer (Claude learns your business)
2. After ContextOS is done, run `/prime` — verify Claude knows you
3. Install more modules from `module-installs/` as you're ready

**Returning?** Run `/prime` at the start of every session.

---

## Critical Instruction: Maintain This File

**Whenever Claude makes changes to the workspace, Claude MUST consider whether CLAUDE.md needs updating.**

After any change — adding commands, scripts, workflows, or modifying structure — ask:

1. Does this change add new functionality users need to know about?
2. Does it modify the workspace structure documented above?
3. Should a new command be listed?
4. Does context/ need new files to capture this?

If yes to any, update the relevant sections. This file must always reflect the current state of the workspace so future sessions have accurate context.

---

## Session Workflow

1. **Start**: Run `/prime` to load context
2. **Work**: Use commands or direct Claude with tasks
3. **Install modules**: Use `/install` to add new AIOS capabilities
4. **Plan changes**: Use `/create-plan` before significant additions
5. **Execute**: Use `/implement` to execute plans
6. **Share**: Use `/share` to package systems for team, clients, or community
7. **Maintain**: Claude updates CLAUDE.md and context/ as the workspace evolves

---

## Notes

- Keep context minimal but sufficient — avoid bloat
- Plans live in `plans/` with dated filenames for history
- Outputs are organized by type/purpose in `outputs/`
- Reference materials go in `reference/` for reuse
- API keys go in `.env` — never commit this file
