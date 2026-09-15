from __future__ import annotations

from typing import Any

import streamlit as st

from langgraph_workflow import run_market_research


st.set_page_config(page_title="Competitive Market Research Agent", layout="wide")
st.title("Competitive Market Research Agent")
st.caption("LangGraph orchestration • Groq-ready reasoning • You.com grounded evidence • Session-only rendering")

with st.sidebar:
    st.markdown("### Scope")
    st.write("This app researches competitors, synthesizes a brief, and renders reviewable cards in the current session only.")
    st.write("- No persistence")
    st.write("- No business actions")
    st.write("- No automatic exports")

company_name = st.text_input("Company or product name", placeholder="OpenAI, Notion, Stripe...")
founder_goal = st.text_area("Founder goal (optional)", placeholder="Reach more startups with less churn")

if st.button("Research competitors", type="primary"):
    if not company_name.strip():
        st.warning("Please enter a valid company name.")
    else:
        with st.spinner("Running the research workflow..."):
            result = run_market_research(company_name.strip(), founder_goal.strip())

        brief = result.get("brief") or result.get("report", {}).get("brief")
        if not brief:
            st.error("The workflow did not return a usable brief.")
            st.json(result)
        else:
            st.success("Research complete. Review the report below.")
            st.subheader(brief.get("title") or "Market Brief")
            st.markdown(brief.get("executive_summary") or "No executive summary available.")
            st.markdown("**Market signal:**")
            st.write(brief.get("market_signal") or "No market signal available.")

            competitors = brief.get("competitors") or []
            for i, competitor in enumerate(competitors):
                with st.expander(f"{i + 1}. {competitor.get('company') or competitor.get('name') or 'Competitor'}"):
                    st.write(competitor.get("positioning") or "No positioning summary available.")
                    st.write("**Pricing:**", competitor.get("pricing") or "Not publicly available")
                    st.write("**Website:**", competitor.get("website") or "No website listed")

            st.markdown("### Recommended positioning")
            st.write(brief.get("recommended_positioning") or "No recommended positioning available.")

            st.markdown("### Next steps")
            for step in brief.get("next_steps") or []:
                st.write(f"- {step}")

            with st.expander("Workflow metadata"):
                st.json({
                    "status": result.get("status"),
                    "company_name": result.get("company_name"),
                    "report": result.get("report", {}),
                })
