# -*- coding: utf-8 -*-
"""
Copyright 2023 Maen Artimy

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
from pages.common.queries import run_query, set_snapshot
from pages.common.presenter import display_result, display_options
from pages.common.utils import convert_template, init_session_state
import logging


logging.getLogger("pybatfish").setLevel(logging.WARNING)

init_session_state()

# Start Page Here
st.set_page_config(layout="wide")
st.header("Network Analysis")
# st.markdown(APP)

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

                answer = run_query(qs[idx])
                display_result(qs[idx]["fun"], answer)

    else:
        st.warning("Select some questions to proceed.")

else:
    st.warning("Please add a snapshot to continue.")
