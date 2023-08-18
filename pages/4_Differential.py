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
from pages.common.queries import run_query
from pages.common.presenter import display_result
from pages.common.utils import convert_template
import logging

logging.getLogger("pybatfish").setLevel(logging.WARNING)

# Start Page Here
st.set_page_config(layout="wide")
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
    st.subheader(f"Refrence snapshot: {st.session_state.activesnap['name']}")
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
                display_result(answer)

    else:
        st.warning("Select some questions to proceed.")

else:
    st.warning("Please add two snapshots to continue.")
