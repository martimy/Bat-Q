import streamlit as st
from datetime import datetime
from common.htmlreport import render_result_html, build_report_html
from common.utils import init_session_state

init_session_state()
st.title("Network Analysis Reporting", text_alignment="center")

data = st.session_state.get("report_analysis_data")
snapshot_name = st.session_state.get("activesnap", {}).get("name", "unknown")

if not data:
    st.warning("Run some questions on the Analysis page first.")
else:
    sections = [
        {"name": item["name"], "options": item.get("options"),
         "html": render_result_html(item["fun"], item["answer"])}
        for item in data
    ]
    report = build_report_html(sections, snapshot_name, datetime.now().strftime("%Y-%m-%d %H:%M"))

    with st.sidebar:
        st.download_button("Download HTML Report", data=report,
                            file_name=f"batq_report_{snapshot_name}.html", mime="text/html")
    st.iframe(report, height=600)