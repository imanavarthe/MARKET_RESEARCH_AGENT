from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List

from schemas import CompetitorReport, SearchResult
from security import sanitize_text, validate_company_name


@dataclass
class ResearchState:
    request_id: str
    company_name: str
    competitors: List[Dict[str, Any]] = field(default_factory=list)
    evidence_by_competitor: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)
    reports: List[CompetitorReport] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    status: str = "draft"


def validate_input(company_name: str) -> ResearchState:
    normalized = validate_company_name(company_name)
    return ResearchState(
        request_id=f"req-{abs(hash(normalized)) % 1000000:06d}",
        company_name=normalized,
        status="validated",
    )


def discover_competitors(company_name: str, results: Iterable[Dict[str, Any]] | None = None) -> List[Dict[str, Any]]:
    normalized = validate_company_name(company_name)
    items = list(results or [])
    competitors: List[Dict[str, Any]] = []

    if not items:
        items = [{"name": f"{normalized} competitor", "website": "https://example.com", "summary": "No live search results were returned."}]

    for item in items[:3]:
        name = (item.get("name") or item.get("title") or normalized).strip()
        website = item.get("website") or item.get("url") or "https://example.com"
        competitors.append(
            {
                "name": name,
                "website": website,
                "summary": item.get("summary") or item.get("snippet") or "No summary available.",
                "pricing": item.get("pricing") or "Not publicly available",
                "positioning": item.get("positioning") or "Positioning details are not yet validated.",
            }
        )

    return competitors


def synthesize_reports(state: ResearchState) -> List[CompetitorReport]:
    if state.competitors:
        competitor_items = state.competitors
    else:
        competitor_items = [{"name": state.company_name, "website": "https://example.com", "summary": "No competitor data available."}]

    reports: List[CompetitorReport] = []
    for competitor in competitor_items:
        name = (competitor.get("name") or competitor.get("company") or "Competitor").strip() or "Competitor"
        website = competitor.get("website") or competitor.get("url") or ""
        summary = sanitize_text(competitor.get("summary") or "No summary available.")
        positioning = sanitize_text(competitor.get("positioning") or "Not publicly available")
        pricing = competitor.get("pricing") or "Not publicly available"

        evidence = state.evidence_by_competitor.get(name, [])
        features = []
        sources = []
        recent_news = []
        for item in evidence:
            title = item.get("title") or item.get("name") or "Evidence item"
            if title not in features:
                features.append(sanitize_text(title))
            url = item.get("url") or item.get("website") or ""
            if url:
                sources.append(url)
            recent_news.append({
                "title": sanitize_text(title),
                "url": url,
                "summary": sanitize_text(item.get("snippet") or item.get("summary") or ""),
            })

        report = CompetitorReport(
            competitor_name=name,
            website=website,
            summary=summary,
            positioning=positioning,
            features=features or ["Evidence summary pending validation"],
            pricing=pricing,
            recent_news=recent_news,
            sources=list(dict.fromkeys(sources)),
            confidence="medium",
        )
        reports.append(report)

    state.reports = reports
    state.status = "synthesized" if reports else "failed"
    return reports


def validate_output(state: ResearchState) -> ResearchState:
    if not state.reports:
        state.errors.append("No competitor reports were generated.")
        state.status = "failed"
        return state

    for report in state.reports:
        if not report.competitor_name:
            state.warnings.append("A competitor report is missing a name.")
        if not report.website:
            state.warnings.append(f"{report.competitor_name} has no website URL.")
        if not report.positioning or report.positioning == "Not publicly available":
            state.warnings.append(f"{report.competitor_name} positioning is not evidence-backed.")

    state.status = "validated"
    return state


ResearchWorkflow = validate_input
