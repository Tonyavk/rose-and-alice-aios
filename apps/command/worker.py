"""Claude Agent SDK worker wrapper with Telegram-specific system prompts."""

import logging

from .agent_sdk import (
    PRIME_TELEGRAM_PATH,
    WorkerResult,
)

logger = logging.getLogger(__name__)

# === CUSTOMIZE THIS PROMPT FOR YOUR BUSINESS ===
_GENERAL_AGENT_PROMPT = """\
You are Rosie — Tonya Knight's AI chief of staff at Rose and Alice Creative, a NZ digital marketing agency.
You have full workspace access — files, database, web search, code execution, everything.

## Your Role
- Strategic thinking partner for a solo digital marketing founder
- Data analyst — query the SQLite database (data/data.db) for revenue, clients, leads, and GA4 traffic
- Marketing specialist — paid ads (Meta/Google), content, SEO, email, ecommerce
- Task coordinator — tell Tonya to use /new for isolated tasks (proposals, reports, research)

## Business Context
- Business: Rose and Alice Creative (Auckland, NZ)
- Goal: Double revenue from $10k to $20k/month without hiring
- Clients: 10-20 active NZ SMBs across beauty, ecommerce, fitness, trades, property
- Tools: Meta Ads, Google Ads, Shopify, Klaviyo, Mailchimp, Xero

## Telegram Rules
- Keep responses concise — Tonya is on her phone
- Use markdown formatting (bold, bullets) for readability
- For charts: use matplotlib, save PNGs to outputs/charts/
- When you create files, mention the path so the bot can deliver them

## Image Analysis
When photos are sent, they're saved to data/command/photos/.
Use the Read tool to view the image. Analyze screenshots, ad results, client reports, etc.
"""


async def run_general_prime(
    workspace_dir: str,
    model: str = "sonnet",
    max_turns: int = 15,
    max_budget_usd: float = 2.00,
) -> WorkerResult:
    from .agent_sdk import run_prime as _run_prime
    return await _run_prime(
        workspace_dir=workspace_dir,
        model=model,
        max_turns=max_turns,
        max_budget_usd=max_budget_usd,
        system_append=_GENERAL_AGENT_PROMPT,
        prime_command=str(PRIME_TELEGRAM_PATH),
    )


async def run_general_agent(
    prompt: str,
    session_id: str,
    workspace_dir: str,
    model: str = "sonnet",
    max_turns: int = 30,
    max_budget_usd: float = 5.00,
) -> WorkerResult:
    from .agent_sdk import run_task_on_session as _run_task
    return await _run_task(
        prompt=prompt,
        session_id=session_id,
        workspace_dir=workspace_dir,
        model=model,
        max_turns=max_turns,
        max_budget_usd=max_budget_usd,
        system_append=_GENERAL_AGENT_PROMPT,
    )
