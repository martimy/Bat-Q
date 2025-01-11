# -*- coding: utf-8 -*-
"""
Copyright 2023-2025 Maen Artimy

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
from pages.common.queries import (
    run_query,
    get_node_properties,
    get_interface_properties,
    fork_snapshot,
)
from pages.common.presenter import display_result
from pages.common.utils import convert_template
from pages.common.queries import set_snapshot
import logging

logging.getLogger("pybatfish").setLevel(logging.WARNING)

# Get selected questions
qlist = st.session_state.get("qlist")
# active_snapshot = st.session_state.activesnap["name"]

# Start Page Here
st.set_page_config(layout="wide")
st.header("Failure Tests")


def update_failed(key):
    st.session_state.activesnap[key] = st.session_state[key]


if "bf" in st.session_state:

    bf = st.session_state.get("bf")

    if "activesnap" in st.session_state and "name" in st.session_state.activesnap:
        active_snapshot = set_snapshot(bf, st.session_state.activesnap["name"])
        st.subheader(f"Active Snapshot: {active_snapshot}")

        # Run selected questions
        if qlist:
            try:
                nodes = get_node_properties(bf)
                interfaces = get_interface_properties(bf)

                # Select a node and/or an interface to fail
                failed_nodes = st.multiselect(
                    "Select failed nodes",
                    nodes,
                    key="failednodes",
                    default=st.session_state.activesnap["failednodes"],
                    on_change=update_failed,
                    kwargs={"key": "failednodes"},  # do not change to 'args'
                )

                failed_interfaces = st.multiselect(
                    "Select failed interfaces",
                    interfaces,
                    key="failedinfs",
                    default=st.session_state.activesnap["failedinfs"],
                    on_change=update_failed,
                    kwargs={"key": "failedinfs"},  # do not change to 'args'
                )

                # Create a new snapshot by forking the active snapshot
                # the new snapshot includes the failed components
                if failed_nodes or failed_interfaces:
                    fork_snapshot(bf, active_snapshot, failed_nodes, failed_interfaces)

                    # Run selected questions
                    qs = convert_template(qlist)
                    q_names = [q["name"] for q in qs]
                    tabs = st.tabs(q_names)
                    for idx, tab in enumerate(tabs):
                        with tab:
                            answer = run_query(bf.q, qs[idx])
                            display_result(qs[idx]["fun"], answer)

            except Exception as e:
                st.error(f"Error encountered in one of the questions: {e}")

        else:
            st.warning("Select some questions to proceed.")

    else:
        st.warning("Please add a snapshot to continue.")
else:
    st.error("No Batfish Session!")
