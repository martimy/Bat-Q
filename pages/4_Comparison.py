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
from pages.common.queries import run_query_ext
import logging

logging.getLogger("pybatfish").setLevel(logging.WARNING)
NO_DATA = """No data available!
This usually means that the query is not applicable to the network.
"""

APP = """This is a Streamlit app that enables the user to run network analysis 
queries using [Batfish](https://www.batfish.org/). 
The app allows the user to select a Batfish question by category and name. 
The app runs the selected question and displays the results in a table. 
All answered questions are saved.

Find more information about Batfish questions
[here](https://batfish.readthedocs.io/en/latest/index.html).
"""

nan = float("NaN")
MAXTABS = 6


# Start Page Here
st.set_page_config(layout="wide")
st.header("Comparisons")
# st.markdown(APP)

# Get selected questions
qlist = st.session_state.get("qlist")

if "activesnap" in st.session_state and "altsnap" in st.session_state:
    st.subheader(f"Refrence snapshot: {st.session_state.activesnap['name']}")
    st.subheader(f"Alternate snapshot: {st.session_state.altsnap['name']}")

    # Run selected questions
    if qlist:
        # TODO: this generates an exception of questions_list is empty
        q_names = [q for q in qlist]
        tabs = st.tabs(q_names)
        for idx, tab in enumerate(tabs):
            with tab:
                run_query_ext(
                    qlist[q_names[idx]],
                    (
                        st.session_state.activesnap["name"],
                        st.session_state.altsnap["name"],
                    ),
                )

    else:
        st.warning("Select some questions to proceed.")

else:
    st.warning("Please add two snapshots to continue.")
