from app import get_runtime_status
from youcom_tools import MarketResearchWorkflow, web_search_tool


def test_web_search_tool_returns_results():
    results = web_search_tool("AI recruiting software")
    assert isinstance(results, list)
    assert results
    assert "title" in results[0]


def test_workflow_creates_reviewable_brief():
    workflow = MarketResearchWorkflow()
    outcome = workflow.run("AI recruiting", founder_goal="reach more startups with less churn")

    assert outcome["review_required"] is True
    assert outcome["save_ready"] is False
    assert "brief" in outcome
    assert outcome["brief"]["title"]
    assert outcome["brief"]["competitors"]


def test_workflow_can_save_brief_to_disk(tmp_path):
    workflow = MarketResearchWorkflow()
    workflow.run("developer tools", founder_goal="win product-led teams")
    saved_path = workflow.save_brief(str(tmp_path / "brief.md"))

    assert saved_path.endswith("brief.md")
    assert (tmp_path / "brief.md").exists()


def test_local_mode_is_supported_without_secrets(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("YOUCOM_API_KEY", raising=False)

    status = get_runtime_status()

    assert status["groq_enabled"] is False
    assert status["youcom_enabled"] is False
    assert status["offline_mode"] is True


def test_offline_fallback_changes_by_query():
    client = __import__('youcom_client').YouComClient(api_key=None)

    project_results = client.search_web("project management software", num_results=3)
    sales_results = client.search_web("crm sales pipeline", num_results=3)

    assert project_results[0]["title"] != sales_results[0]["title"]
    assert all("Notion" in result["title"] or result["title"] in {"Asana", "Monday.com", "Trello", "ClickUp"} for result in project_results)
    assert all("HubSpot" in result["title"] or result["title"] in {"Salesforce", "Pipedrive", "Zoho CRM", "Freshsales"} for result in sales_results)
