"""Run ONCE with your real key to verify the assumptions this repo makes about Tavily.

    cd backend && TAVILY_API_KEY=tvly-... python scripts/smoke_tavily.py "OpenAI"

Costs 1 search credit. Prints the raw shape so you can compare it with docs/PHASE3_NOTES.md.
"""
import asyncio
import json
import os
import pathlib
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from app.services.research import parse_published  # noqa: E402
from app.services.tavily_client import TavilyClient  # noqa: E402


async def main(subject: str) -> None:
    key = os.environ.get("TAVILY_API_KEY")
    if not key:
        sys.exit("Set TAVILY_API_KEY first.")
    now = datetime.now(timezone.utc)
    client = TavilyClient(key, base_url=os.environ.get("TAVILY_BASE_URL", "https://api.tavily.com"))
    results = await client.search(
        subject, topic="news", start_date=(now - timedelta(days=30)).strftime("%Y-%m-%d"),
        end_date=now.strftime("%Y-%m-%d"), max_results=5,
    )
    await client.aclose()
    print(f"{len(results)} results")
    if not results:
        return
    print("keys on first result:", sorted(results[0]))
    for r in results:
        raw = r.get("published_date") or r.get("publishedDate") or r.get("date")
        print(f"- raw date={raw!r} -> parsed={parse_published(raw)} | score={r.get('score')} | {r.get('title', '')[:60]}")
    print("\nfirst result (truncated):")
    print(json.dumps({k: (str(v)[:120]) for k, v in results[0].items()}, indent=2))


asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else "OpenAI"))
