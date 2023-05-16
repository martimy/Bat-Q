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
    bf_fork_snapshot,
    bf_set_snapshot,
    bf_delete_snapshot
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
BASE_NETWORK_NAME = "NETWORK"

def upload_snapshot():
    filename = st.sidebar.file_uploader("Add network snapshot", type="zip")
    if filename:
        new_name = filename.name.split(".")[0]
        try:
            bf_init_snapshot(filename, name=new_name, overwrite=True)
            bf_set_snapshot(new_name)
        except:
            st.sidebar.error(f"File {filename.name} is not recognized!")

@st.cache_data
def init_host(host, network):
    bf_session.host = host
    bf_set_network(network)
    load_questions()
    
@st.cache_data
def init_snapshot(config_file, snapshot):
    bf_session.init_snapshot(config_file, name=snapshot, overwrite=True)

def find_index(lst, item):
    try:
        index = lst.index(item)
        return index
    except ValueError:
        return 0


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
            st.markdown(f"The query returned these empty columns:  \n{removed_str}.")

    except Exception as e:
        st.error(f"Error running query {e}")


if "activesnap" not in st.session_state:
    st.session_state.activesnap = None

# Start Page Here
st.set_page_config(layout="wide")
st.header("Network Analysis")
st.markdown(APP)

bf_host = os.getenv("BATFISH_SERVER") or "127.0.0.1"
st.sidebar.write(f"Batfish Server: {bf_host}")

# try
init_host(bf_host, BASE_NETWORK_NAME)
            
upload_snapshot()

snapshots = bf_session.list_snapshots()

# Get selected questions
alldata = st.session_state.get("qlist")

if snapshots:
    idx = find_index(snapshots, st.session_state.activesnap) if st.session_state.activesnap else 0
    select_snapshot = st.sidebar.selectbox("Select Snapshot", snapshots, index=idx)
    st.session_state.activesnap = bf_set_snapshot(select_snapshot)    
    st.write(f"Snapshot: {select_snapshot}")

    # Run selected questions
    if alldata:
        questions_list = [
            (item["name"], item["fun"])
            for category in alldata
            for item in alldata[category]
            if item.get("fun")
        ]

        tabs = st.tabs([q[0] for q in questions_list])
        for idx, tab in enumerate(tabs):
            with tab:
                run_query(questions_list[idx][1])

        st.subheader("Failure Tests")

        nodes = bfq.nodeProperties().answer().frame()
        failed_nodes = st.multiselect("Select failed nodes", nodes["Node"])

        interfaces = bfq.interfaceProperties().answer().frame()
        failed_interfaces = st.multiselect(
            "Select failed interfaces", interfaces["Interface"]
        )

        if failed_nodes or failed_interfaces:
            bf_fork_snapshot(
                st.session_state.activesnap,
                st.session_state.activesnap+"_Fail",
                deactivate_nodes=failed_nodes,
                deactivate_interfaces=failed_interfaces,
                overwrite=True,
            )

            tabs = st.tabs([q[0] for q in questions_list])
            for idx, tab in enumerate(tabs):
                with tab:
                    run_query(questions_list[idx][1])
    else:
        st.warning("Select some questions to proceed.")
    
    if st.sidebar.button("Delete Snapshot"):
        bf_delete_snapshot(select_snapshot)
        st.experimental_rerun()
else:
    st.warning("Please add a snapshot to continue.")

