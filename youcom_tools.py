"""LangChain tools for You.com web and news research."""

from functools import lru_cache
from pathlib import Path

from langchain_core.tools import tool

from youcom_client import YouComClient


@lru_cache(maxsize=1)
def _get_client() -> YouComClient:
    """Return the lazily initialized You.com client."""
    return YouComClient()

def _format_results(results: list[dict]) -> str:
    """Format search results as readable tool output."""
    if not results:
        return "No results found."
    return "\n".join(
        f"- {r['title']}\n  {r.get('snippet', '')}\n  Source: {r['url']}"
        for r in results
    )


def web_search_tool(
    query: str,
    client: YouComClient | None = None,
    num_results: int = 5,
) -> list[dict]:
    """Return normalized web results for legacy callers and tests."""
    return (client or _get_client()).search_web(query, num_results=num_results)


def news_search_tool(
    query: str,
    client: YouComClient | None = None,
    num_results: int = 5,
) -> list[dict]:
    """Return normalized news results for the researcher node."""
    return (client or _get_client()).search_news(query, num_results=num_results)


class MarketResearchWorkflow:
    """Preserve the original brief workflow API on top of the new client."""

    def __init__(self, client: YouComClient | None = None) -> None:
        """Initialize the workflow with an optional shared client."""
        self.client = client or YouComClient()
        self.brief: dict | None = None

    def run(self, market: str, founder_goal: str = "", target_customer: str = "founders") -> dict:
        """Create a reviewable market brief from local or live search results."""
        candidates = web_search_tool(f"{market} competitors pricing for {target_customer}", self.client)
        rows = [
            {
                "name": item.get("title", "Competitor"),
                "website": item.get("url", ""),
                "pricing": "Not publicly available",
                "positioning": item.get("snippet", "No positioning text detected"),
            }
            for item in candidates[:3]
        ]
        self.brief = {
            "title": f"{market.title()} Market Brief",
            "executive_summary": f"The {market} market is active and competitive, with multiple players competing on workflow simplicity and AI-assisted automation.",
            "market_signal": founder_goal or "The market rewards products that are clear, fast, and easy to adopt.",
            "competitors": rows,
            "recommended_positioning": f"Position the new product as a lower-friction option for {market} buyers.",
            "next_steps": ["Interview target users", "Validate the strongest customer pain point", "Test a focused onboarding flow"],
        }
        return {"market": market, "brief": self.brief, "review_required": True, "save_ready": False}

    def save_brief(self, path: str = "market_brief.md") -> str:
        """Write the latest brief to a Markdown file and return its resolved path."""
        if self.brief is None:
            raise ValueError("No brief has been generated yet.")
        output_path = Path(path)
        output_path.write_text(f"# {self.brief['title']}\n\n{self.brief['executive_summary']}\n", encoding="utf-8")
        return str(output_path.resolve())


@tool
def youcom_web_search(query: str) -> str:
    """Search the web via you.com for pricing, features, and market positioning."""
    return _format_results(_get_client().search_web(query))


@tool
def youcom_news_search(query: str) -> str:
    """Search recent news via you.com for launches and announcements."""
    return _format_results(_get_client().search_news(query))
