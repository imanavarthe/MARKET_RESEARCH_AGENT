from schemas import CompetitorReport, SearchResult
from security import validate_company_name, sanitize_text
from graph import ResearchState, validate_input, synthesize_reports


def test_search_result_contract():
    result = SearchResult(title="Acme", url="https://acme.com", snippet="AI recruiting")
    assert result.title == "Acme"
    assert result.url.startswith("https://")


def test_company_name_validation():
    normalized = validate_company_name("  OpenAI  ")
    assert normalized == "OpenAI"

    try:
        validate_company_name(" ")
        assert False, "Expected validation error"
    except ValueError:
        pass


def test_synthesizer_handles_unknown_fields():
    state = ResearchState(
        request_id="r1",
        company_name="OpenAI",
        competitors=[{"name": "Anthropic", "website": "https://anthropic.com"}],
        evidence_by_competitor={"Anthropic": [{"title": "Anthropic launch", "url": "https://anthropic.com"}]},
        reports=[],
        warnings=[],
        errors=[],
        status="ready",
    )
    reports = synthesize_reports(state)
    assert reports
    assert isinstance(reports[0], CompetitorReport)
    assert reports[0].competitor_name == "Anthropic"
