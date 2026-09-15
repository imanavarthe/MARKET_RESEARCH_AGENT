"""Queue-based LangGraph orchestration for the market research agent."""

from __future__ import annotations

from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from schemas import CompetitorReport
from security import sanitize_text, validate_company_name
from youcom_client import YouComClient
from youcom_tools import news_search_tool, web_search_tool


class ResearchState(TypedDict, total=False):
    """Short-term memory shared by the discovery, researcher, and analyst nodes."""

    company_name: str
    competitor_queue: list[dict[str, Any]]
    active_competitor: dict[str, Any]
    final_reports: list[CompetitorReport]
    events: list[str]
    status: str
    live: bool


def _append_event(state: ResearchState, event: str) -> list[str]:
    """Return the existing event log with one event appended."""
    return [*state.get("events", []), event]


def _analyst_report(candidate: dict[str, Any], web: list[dict[str, Any]], news: list[dict[str, Any]]) -> CompetitorReport:
    """Turn one research bundle into a grounded structured report."""
    name = candidate.get("name", "Unknown competitor")
    snippets = [item.get("snippet", "") for item in web if item.get("snippet")]
    combined = " ".join(snippets) or candidate.get("summary", "")
    lower = combined.lower()
    features = [
        feature
        for feature in ("AI-assisted workflows", "team collaboration", "automation", "analytics")
        if feature.split()[0] in lower or not snippets
    ]
    pricing = "Data not found"
    if "$" in combined:
        pricing = next((part.strip() for part in combined.split(".") if "$" in part), "Data found in source")
    positioning = (
        f"{name} is positioned around AI-assisted productivity and faster team workflows."
        if "ai" in lower
        else f"{name} competes through workflow simplicity, adoption speed, and team coordination."
    )
    return CompetitorReport(
        competitor_name=sanitize_text(name),
        website=candidate.get("website", ""),
        summary=sanitize_text(combined[:500] or "Data not found"),
        positioning=sanitize_text(positioning),
        features=list(dict.fromkeys(features))[:4] or ["Data not found"],
        pricing=sanitize_text(pricing),
        recent_news=[
            {
                "title": item.get("title", "Data not found"),
                "url": item.get("url", ""),
                "summary": item.get("snippet", ""),
            }
            for item in news
        ],
        sources=list(dict.fromkeys([item.get("url", "") for item in web + news if item.get("url")])),
        confidence="medium" if snippets else "low",
    )


class LangGraphMarketResearchFlow:
    """Run discovery once, then loop researcher and analyst nodes per competitor."""

    def __init__(self, client: YouComClient | None = None) -> None:
        """Initialize the graph with a shared live or fixture-backed client."""
        self.client = client or YouComClient()
        self.graph = self._build_graph()

    def _build_graph(self):
        """Construct the discovery, research, analysis, and queue-router graph."""
        workflow = StateGraph(ResearchState)

        def discovery_node(state: ResearchState) -> ResearchState:
            company_name = state["company_name"]
            results = web_search_tool(
                f"{company_name} product competitors",
                client=self.client,
                num_results=5,
            )
            candidates = [
                {
                    "name": item.get("title") or "Unknown competitor",
                    "website": item.get("url", ""),
                    "summary": item.get("snippet", ""),
                }
                for item in results[:3]
            ]
            return {
                "competitor_queue": candidates,
                "events": _append_event(state, f"Discovery created queue with {len(candidates)} competitors"),
                "status": "discovered",
            }

        def researcher_node(state: ResearchState) -> ResearchState:
            queue = list(state.get("competitor_queue", []))
            candidate = queue.pop(0)
            name = candidate["name"]
            web = web_search_tool(
                f"{name} pricing features positioning",
                client=self.client,
                num_results=3,
            )
            news = news_search_tool(
                f"{name} product news launches announcements",
                client=self.client,
                num_results=3,
            )
            return {
                "competitor_queue": queue,
                "active_competitor": {"candidate": candidate, "web": web, "news": news},
                "events": _append_event(state, f"Researcher collected web and news evidence for {name}"),
                "status": "researched",
            }

        def analyst_node(state: ResearchState) -> ResearchState:
            bundle = state["active_competitor"]
            report = _analyst_report(bundle["candidate"], bundle["web"], bundle["news"])
            return {
                "final_reports": [*state.get("final_reports", []), report],
                "events": _append_event(state, f"Analyst appended JSON report for {report.competitor_name}"),
                "status": "analyzed",
            }

        def queue_router(state: ResearchState) -> str:
            """Route back to the researcher until every competitor is complete."""
            return "researcher" if state.get("competitor_queue") else "finish"

        workflow.add_node("discovery", discovery_node)
        workflow.add_node("researcher", researcher_node)
        workflow.add_node("analyst", analyst_node)
        workflow.add_edge(START, "discovery")
        workflow.add_edge("discovery", "researcher")
        workflow.add_edge("researcher", "analyst")
        workflow.add_conditional_edges(
            "analyst",
            queue_router,
            {"researcher": "researcher", "finish": END},
        )
        return workflow.compile()

    def invoke(self, company_name: str) -> ResearchState:
        """Validate input and execute the complete queue-based graph."""
        normalized = validate_company_name(company_name)
        state: ResearchState = {
            "company_name": normalized,
            "competitor_queue": [],
            "final_reports": [],
            "events": ["LangGraph orchestrator started"],
            "status": "started",
            "live": self.client.live,
        }
        result = self.graph.invoke(state)
        result["events"] = [*result.get("events", []), "Queue router reached END"]
        result["status"] = "complete"
        return result


def run_market_research(company_name: str) -> ResearchState:
    """Convenience entrypoint for running the LangGraph research flow."""
    return LangGraphMarketResearchFlow().invoke(company_name)
