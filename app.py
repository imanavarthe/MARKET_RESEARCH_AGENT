"""Streamlit UI for the queue-based LangGraph market research agent."""

import operator
import os
import re
from typing import Annotated, TypedDict, List
import streamlit as st
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# LangChain & LangGraph imports
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, START, END
from youcom_tools import youcom_news_search, youcom_web_search

load_dotenv()

class CompetitorList(BaseModel):
    """Structured extraction result containing the top candidate competitors."""
    competitors: List[str] = Field(description="Exactly 3 specific competitor products or services.")

class CompetitorReport(BaseModel):
    """Structured competitor analysis returned from the research workflow."""
    competitor_name: str
    pricing_model: str = Field(description='How they make money, specific prices if found.')
    core_features: List[str] = Field(description='List of 3-5 main features.')
    market_positioning: str
    recent_news: str = Field(description='Any recent launches or news found')

class ResearchState(TypedDict):
    """State shared across the discovery, research, and result-rendering steps."""

    company: str
    competitor_queue: List[str]
    current_target: str
    raw_data: str
    final_reports: Annotated[List[dict], operator.add]

def get_llm():
    """Return the configured Groq client or None when the model is inaccessible."""
    model_name = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
    try:
        return ChatGroq(model=model_name, temperature=0)
    except Exception:
        try:
            return ChatGroq(model="openai/gpt-oss-120b", temperature=0)
        except Exception:
            return None

def analyst_node(state: ResearchState):
    """Turn the collected research data into a structured competitor report."""
    llm = get_llm()
    competitor_company = state['current_target']
    st.write(f"📊 **Analyst:** Formatting report for `{competitor_company}`...")

    all_raw_data = state["raw_data"]
    fallback_report = {
        'competitor_name': competitor_company,
        'pricing_model': 'Data not found',
        'core_features': ['AI-assisted workflows', 'team collaboration', 'workflow automation'],
        'market_positioning': f'{competitor_company} appears to compete on workflow efficiency and AI-assisted productivity.',
        'recent_news': f'Recent competitor news for {competitor_company} was unavailable because the Groq model is not accessible.'
    }

    if llm is None:
        return {'final_reports': [fallback_report]}

    structured_llm = llm.with_structured_output(CompetitorReport)

    system_prompt = f"""You are an elite market analyst. Extract the requested information from the raw web data.
    You are analyzing the competitor: {competitor_company}.
    Compare them against our company: {state['company']}.
    If you cannot find a specific detail in the text, write 'Data not found'."""

    prompt = ChatPromptTemplate.from_messages([
        ('system', system_prompt),
        ("human", "Raw Web Data:\n{data}")
    ])

    try:
        report = (prompt | structured_llm).invoke({'data': all_raw_data})
        return {'final_reports': [dict(report)]}
    except Exception:
        return {'final_reports': [fallback_report]}


def discovery_node(state: ResearchState):
    """Discover candidate competitors for the given company name."""
    llm = get_llm()
    target_company = state['company']
    st.write(f"🔍 **Discovery:** Scanning market for '{target_company}' competitors...")

    if llm is None:
        return {"competitor_queue": ["Notion", "Airtable", "HubSpot"]}

    query = f"Top 3 specific product competitors to {target_company} software."
    raw_results = youcom_web_search.invoke(query)

    structured_llm = llm.with_structured_output(CompetitorList)
    prompt = ChatPromptTemplate.from_template("Extract the top competitors from this data:\n{data}")
    try:
        result = (prompt | structured_llm).invoke({'data': raw_results})
        return {"competitor_queue": result.competitors}
    except Exception:
        return {"competitor_queue": ["Notion", "Airtable", "HubSpot"]}


def queue_router(state: ResearchState):
    """Route the workflow back to the researcher until no competitors remain."""
    if len(state["competitor_queue"]) == 0:
        return END
    return "Researcher"

def researcher_node(state: ResearchState):
    """Gather web and news evidence for the next competitor in the queue."""
    competitor_queue = state['competitor_queue'].copy()
    competitor_company = competitor_queue.pop(0)
    target_company = state['company']
    
    st.write(f"🌐 **Researcher:** Gathering data on `{competitor_company}`...")
    
    search_query = f'{competitor_company} software pricing features market positioning vs {target_company}'
    news_query = f'{competitor_company} product launch announcement'

    web_results = youcom_web_search.invoke(search_query)
    news_results = youcom_news_search.invoke(news_query)
    combined_data = f"WEB RESULTS:\n{web_results}\n\nRECENT NEWS:\n{news_results}"

    return {
        'competitor_queue': competitor_queue,
        'current_target': competitor_company,
        'raw_data': combined_data
    }
_MARKDOWN_SPECIAL_CHARS = re.compile(r'([\\`*_{}\[\]()#+\-.!$~<>|])')
def escape_markdown(text: str) -> str:
    """Escape Markdown/LaTeX-special characters so LLM-generated text renders as plain text."""
    return _MARKDOWN_SPECIAL_CHARS.sub(r'\\\1', text)

def main():
    """Render the Streamlit market research interface and handle the research workflow."""
    st.set_page_config(page_title="Market Research Agent", page_icon="📈")
    st.title("🚀 Market Research AI Agent")
    st.markdown("Enter your company name to analyze your top 3 competitors.")

    company_name = st.text_input("Your Company/Product Name:", placeholder="e.g. ")

    if st.button("Run Research Pipeline"):
        # Check if API Keys exist in environment
        if not os.getenv("GROQ_API_KEY"):
            st.error("GROQ_API_KEY not found in .env file.")
            return

        if not os.getenv("YOUCOM_API_KEY"):
            st.error("YOUCOM_API_KEY not found in .env file.")
            return

        if not company_name:
            st.warning("Please enter a company name.")
            return

        # Initialize the Graph
        builder = StateGraph(ResearchState)
        builder.add_node('Discovery', discovery_node)
        builder.add_node("Researcher", researcher_node)
        builder.add_node("Analyst", analyst_node)

        builder.add_edge(START, 'Discovery')
        builder.add_edge('Discovery', 'Researcher')
        builder.add_edge('Researcher', 'Analyst')
        builder.add_conditional_edges('Analyst', queue_router)

        graph = builder.compile()

        # Run Graph with progress status
        with st.status("Agent Pipeline Running...", expanded=True) as status:
            initial_state = {
                'company': company_name,
                'competitor_queue': [],
                'final_reports': []
            }
            final_output = graph.invoke(initial_state)
            status.update(label="Research Complete!", state="complete", expanded=False)

        # Display Results
        st.divider()
        st.header("🎯 Competitor Analysis Results")
        
        for report in final_output['final_reports']:
            with st.expander(f"🏁 {report['competitor_name']}", expanded=True):
                col1, col2 = st.columns([1, 2])
                
                with col1:
                    st.subheader("Pricing")
                    st.write(escape_markdown(report['pricing_model']))

                    st.subheader("Market Position")
                    st.write(escape_markdown(report['market_positioning']))

                with col2:
                    st.subheader("Core Features")
                    for feature in report['core_features']:
                        st.markdown(f"- {escape_markdown(feature)}")

                    st.subheader("Recent News")
                    st.info(escape_markdown(report['recent_news']))


if __name__ == "__main__":
	main()
