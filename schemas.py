from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str = ""
    source_type: str = "web"
    published_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "url": self.url,
            "snippet": self.snippet,
            "source_type": self.source_type,
            "published_at": self.published_at,
        }


@dataclass
class Competitor:
    name: str
    website: str = ""
    summary: str = ""
    pricing: str = "Not publicly available"
    positioning: str = ""
    source_url: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "website": self.website,
            "summary": self.summary,
            "pricing": self.pricing,
            "positioning": self.positioning,
            "source_url": self.source_url,
        }


@dataclass
class CompetitorReport:
    competitor_name: str
    website: str = ""
    summary: str = ""
    positioning: str = "Not publicly available"
    features: List[str] = field(default_factory=list)
    pricing: str = "Not publicly available"
    recent_news: List[Dict[str, str]] = field(default_factory=list)
    sources: List[str] = field(default_factory=list)
    research_timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds"))
    confidence: str = "medium"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "competitor_name": self.competitor_name,
            "website": self.website,
            "summary": self.summary,
            "positioning": self.positioning,
            "features": self.features,
            "pricing": self.pricing,
            "recent_news": self.recent_news,
            "sources": self.sources,
            "research_timestamp": self.research_timestamp,
            "confidence": self.confidence,
        }


@dataclass
class EvidenceBundle:
    title: str
    url: str = ""
    snippet: str = ""
    source_type: str = "web"
    published_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "url": self.url,
            "snippet": self.snippet,
            "source_type": self.source_type,
            "published_at": self.published_at,
        }
