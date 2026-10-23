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

from datetime import datetime

import streamlit as st

from common.assertion_report import (
    build_assertion_report_html,
    build_assertion_report_xlsx,
    collect_report_rows,
)
from common.utils import init_session_state

XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

init_session_state()
st.title("Assertion Reporting", text_alignment="center")

snapshot = st.session_state.get("activesnap", {}).get("name")
alist = st.session_state.get("alist") or []
results = st.session_state.get("assertion_results") or {}

if not snapshot:
    st.warning("Please add a snapshot on the Home page to continue.")
elif not alist:
    st.warning("Add some assertions on the Assertions page first.")
else:
    rows = collect_report_rows(alist, results, snapshot)
    if all(r["status"] is None for r in rows):
        st.warning("Run the assertions on the Assertions page first.")
    else:
        generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")
        report = build_assertion_report_html(rows, snapshot, generated_at)
        xlsx_bytes = build_assertion_report_xlsx(rows, snapshot, generated_at)

        with st.sidebar:
            st.download_button(
                "Download HTML Report",
                data=report,
                file_name=f"batq_assertions_{snapshot}.html",
                mime="text/html",
            )
            st.download_button(
                "Download Spreadsheet (.xlsx)",
                data=xlsx_bytes,
                file_name=f"batq_assertions_{snapshot}.xlsx",
                mime=XLSX_MIME,
            )
        st.iframe(report, height=600)
