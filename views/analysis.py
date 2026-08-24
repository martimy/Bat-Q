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
import logging

logging.getLogger("pybatfish").setLevel(logging.WARNING)

init_session_state()

st.header("Network Analysis")

# Get selected questions
qlist = st.session_state.get("qlist")

if "activesnap" in st.session_state and "name" in st.session_state.activesnap:
    set_snapshot(st.session_state.activesnap["name"])
    st.subheader(f"Snapshot: {st.session_state.activesnap['name']}")

    # Run selected questions
    if qlist:
        qs = convert_template(qlist)
        q_names = [q["name"] for q in qs]
        tabs = st.tabs(q_names)
        for idx, tab in enumerate(tabs):
            with tab:
                if qs[idx].get("options"):
                    display_options(qs[idx]["options"])

                with st.status(f"Running '{qs[idx]['name']}'...", expanded=False) as status:
                    answer = run_query(qs[idx])
                    if answer is None:
                        status.update(label=f"'{qs[idx]['name']}' failed", state="error")
                    else:
                        status.update(label=f"'{qs[idx]['name']}' complete", state="complete")

                display_result(qs[idx]["fun"], answer)

    else:
        st.warning("Select some questions to proceed.")

else:
    st.warning("Please add a snapshot on the Home page to continue.")
