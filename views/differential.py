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
from common.queries import run_query
from common.presenter import display_result_diff
from common.utils import convert_template, init_session_state
import logging

logging.getLogger("pybatfish").setLevel(logging.WARNING)

init_session_state()

st.header("Differential")

# Get selected questions
qlist = st.session_state.get("qlist")

if (
    "activesnap" in st.session_state
    and "altsnap" in st.session_state
    and "name" in st.session_state.activesnap
    and "name" in st.session_state.altsnap
    and st.session_state.activesnap["name"] != st.session_state.altsnap["name"]
):
    st.subheader(f"Reference snapshot: {st.session_state.activesnap['name']}")
    st.subheader(f"Alternate snapshot: {st.session_state.altsnap['name']}")

    # Run selected questions
    if qlist:
        qs = convert_template(qlist)
        q_names = [q["name"] for q in qs]
        tabs = st.tabs(q_names)
        for idx, tab in enumerate(tabs):
            with tab:
                answer = run_query(
                    qs[idx],
                    (
                        st.session_state.activesnap["name"],
                        st.session_state.altsnap["name"],
                    ),
                )
                display_result_diff(qs[idx]["fun"], answer)

    else:
        st.warning("Select some questions to proceed.")

else:
    st.warning("Please add and select two distinct snapshots on the Home page to continue.")
