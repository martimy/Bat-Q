# -*- coding: utf-8 -*-
"""
Copyright 2023-2026 Maen Artimy

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

import streamlit as st
from common.queries import run_query, set_snapshot
from common.presenter import display_result, display_options
from common.utils import convert_template, init_session_state
from common.spreadsheet import build_report_xlsx
import logging

logging.getLogger("pybatfish").setLevel(logging.WARNING)

init_session_state()

st.title("Network Analysis", text_alignment="center")

# Get selected questions
qlist = st.session_state.get("qlist")

if "activesnap" in st.session_state and "name" in st.session_state.activesnap:
    set_snapshot(st.session_state.activesnap["name"])
    st.subheader(f"Snapshot: {st.session_state.activesnap['name']}")

    # Run selected questions
    if qlist:
        qs = convert_template(qlist)
        for q in qs:
            qn = q["name"]
            with st.status(f"Running '{qn}'...", expanded=False) as status:
                if q.get("options"):
                    display_options(q["options"])
                answer = run_query(q)
                if answer is None:
                    status.update(label=f"'{qn}' failed", state="error")
                else:
                    status.update(label=f"'{qn}' complete", state="complete")
                display_result(q["fun"], answer)
                st.session_state["report_analysis_data"].append({"name": qn, "fun": q["fun"], "options": q.get("options"), "answer": answer})

    else:
        st.warning("Select some questions to proceed.")

    with st.sidebar:
        snapshot_name = st.session_state.activesnap["name"]
        data = st.session_state.get("report_analysis_data")
        xlsx_bytes = build_report_xlsx(data)
        if xlsx_bytes:
            st.download_button(
                "Download Spreadsheet (.xlsx)",
                data=xlsx_bytes,
                file_name=f"batq_report_{snapshot_name}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        else:
            st.info("No data available to export.")

else:
    st.warning("Please add a snapshot on the Home page to continue.")
