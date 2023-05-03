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

import os
import streamlit as st
from pybatfish.question import load_questions
from pybatfish.question import bfq
from pybatfish.client.commands import (
    bf_session,
    bf_set_network,
    bf_init_snapshot,
    bf_set_snapshot
)
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


# @st.cache_data(experimental_allow_widgets=True)
def load_net_configs():
    return st.sidebar.file_uploader("Upload network snapshot", type="zip")

@st.cache_data
def init_session(host, config_file, snapshot, network):
    bf_session.host = host
    bf_init_snapshot(config_file, name=snapshot, overwrite=True)
    bf_set_network(network)
    load_questions()


def run_query(question_name):
    """
    Run Batfish question.
    """

    try:
        # Run query
        fun = getattr(bfq, question_name)
        result = fun().answer().frame()

        # Replace empty lists with NaN values
        for c in result.columns:
            result[c] = result[c].apply(
                lambda y: nan if isinstance(y, list) and len(y) == 0 else y
            )

        # Replace empty strings with NaN values
        result = result.replace("", nan)

        # Drop all empty columns
        filtered_df = result.dropna(axis=1, how="all")
        filtered_df = filtered_df.replace(nan, "")

        removed = set(result.columns) - set(filtered_df.columns)
        removed_str = ", ".join(list(removed))

        # Print the result
        if filtered_df.empty:
            st.warning(NO_DATA)
        else:
            st.dataframe(filtered_df, use_container_width=True)
            # st.session_state.previous.insert(
            #     0, {"name": question_name, "result": filtered_df, "removed": removed_str, "favorite": False})

        # Print removed columns
        if removed:
            st.write(f"The query returned these empty columns: {removed_str}.")

    except Exception as e:
        st.error(f"Error running query {e}")


if "filename" not in st.session_state:
    st.session_state.filename = None
    
# Start Page Here
st.set_page_config(layout="wide")
st.header("Network Analysis")
st.markdown(APP)

bf_host = os.getenv('BATFISH_SERVER') or "127.0.0.1"
st.sidebar.write(f"Batfish Server: {bf_host}")


# Check if the snopshot already loaded
# The API does not allow a better aprroach than exception for now    
try:
    bf_set_snapshot("First")
    st.sidebar.write(f"Config File: {st.session_state.filename.name}")
    if st.sidebar.button("Remove Snapshot"):
        st.session_state.filename = load_net_configs()
except:
    st.session_state.filename = load_net_configs()

# Step 2: Check if the host is reachable and allow user to upload network snapshot
if st.session_state.filename is not None:
    try:
        init_session(bf_host, st.session_state.filename, "First", "Network")
    
        # Step 3: Execute a list of questions
        alldata = st.session_state.get("qlist")
    
        if alldata:
            questions_list = [
                (item["name"], item["fun"])
                for category in alldata
                for item in alldata[category]
                if item.get("fun")
            ]
    
            tabs = st.tabs([q[0] for q in questions_list])
            idx = 0
            for tab in tabs:
                with tab:
                    run_query(questions_list[idx][1])
                    idx += 1
        else:
            st.warning("Select some questions to proceed.")
    except Exception as e:
        st.error(f"Error: {str(e)}")
else:
    st.warning("Please upload a network configuration files to continue.")
    
