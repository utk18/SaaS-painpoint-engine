import json
import os

import streamlit as st

from main import get_brightdata_api_token, run_pain_point_engine_sync

st.set_page_config(
    page_title="SaaS Pain-Point Engine",
    page_icon="🔍",
    layout="wide",
)

st.title("SaaS Pain-Point Engine")
st.caption("Find Reddit complaints and turn them into micro-SaaS ideas using Bright Data MCP + NVIDIA NIM.")

with st.sidebar:
    st.header("Settings")
    subreddit = st.text_input("Subreddit", value="saas", placeholder="saas")
    st.caption("Enter a subreddit name without `r/`. Example: `saas`, `startups`, `entrepreneur`.")
    run = st.button("Analyze community", type="primary", use_container_width=True)

    st.divider()
    st.subheader("API status")
    st.write("Bright Data:", "✅ configured" if get_brightdata_api_token() else "❌ missing")
    st.write("NVIDIA NIM:", "✅ configured" if os.getenv("NVIDIA_API_KEY") else "❌ missing")

if "result" not in st.session_state:
    st.session_state.result = None

if run:
    if not subreddit.strip():
        st.error("Enter a subreddit name.")
    elif not get_brightdata_api_token():
        st.error("Set BRIGHTDATA_API_KEY or API_TOKEN in `.env`.")
    else:
        with st.status("Running analysis...", expanded=True) as status:
            st.write("1. Searching Reddit discussions via Bright Data MCP")
            st.write("2. Scraping subreddit feed")
            st.write("3. Extracting pain points with NVIDIA NIM")
            try:
                st.session_state.result = run_pain_point_engine_sync(subreddit)
                status.update(label="Analysis complete", state="complete", expanded=False)
            except Exception as exc:
                status.update(label="Analysis failed", state="error", expanded=True)
                st.error(str(exc))
                st.session_state.result = None

result = st.session_state.result

if result:
    st.subheader(f"Founder complaint report for r/{result['subreddit']}")

    if result["parsed_report"]:
        report = result["parsed_report"]
        st.markdown(f"**Community:** {report.get('community', result['subreddit'])}")

        problems = report.get("extracted_problems", [])
        if not problems:
            st.warning("The model returned JSON, but no extracted problems were found.")
        else:
            for idx, problem in enumerate(problems, start=1):
                with st.expander(f"Idea {idx}: score {problem.get('market_readiness_score', 'N/A')}/10", expanded=idx == 1):
                    st.markdown(f"**User frustration:** {problem.get('user_frustration', '')}")
                    st.markdown(f"**Trigger:** {problem.get('context_or_trigger', '')}")
                    st.markdown(f"**Potential SaaS solution:** {problem.get('potential_saas_solution', '')}")

        st.download_button(
            label="Download JSON report",
            data=json.dumps(report, indent=2),
            file_name=f"saas_painpoints_{result['subreddit']}.json",
            mime="application/json",
        )
    else:
        st.warning("Could not parse the model output as JSON.")
        if result.get("parse_error"):
            st.code(result["parse_error"])
        st.code(result["raw_output"])

    with st.expander("Source context"):
        st.markdown("**Search query**")
        st.code(result["search_query"])
        st.markdown("**Search snippets**")
        st.text(result["search_text"][:4000] or "No search snippets returned.")
        st.markdown("**Scraped markdown preview**")
        st.text(result["raw_markdown"][:4000] or "No scraped content returned.")

else:
    st.info("Enter a subreddit in the sidebar and click **Analyze community** to generate SaaS pain-point ideas.")
