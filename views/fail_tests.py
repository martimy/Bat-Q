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
from common.queries import (
    run_query,
    get_node_properties,
    get_interface_properties,
    fork_snapshot,
    set_snapshot,
)
from common.presenter import display_result
from common.utils import convert_template, init_session_state
import logging

logging.getLogger("pybatfish").setLevel(logging.WARNING)

init_session_state()

st.header("Failure Tests")

# Get selected questions
qlist = st.session_state.get("qlist")


def update_failed(key):
    st.session_state.activesnap[key] = st.session_state[key]


if "activesnap" in st.session_state and "name" in st.session_state.activesnap:
    active_snapshot = set_snapshot(st.session_state.activesnap["name"])
    st.subheader(f"Active Snapshot: {active_snapshot}")

    # Run selected questions
    if qlist:
        try:
            nodes = get_node_properties()
            interfaces = get_interface_properties()

            # Select a node and/or an interface to fail
            failed_nodes = st.multiselect(
                "Select failed nodes",
                nodes,
                key="failednodes",
                default=st.session_state.activesnap.get("failednodes", []),
                on_change=update_failed,
                kwargs={"key": "failednodes"},
            )

            failed_interfaces = st.multiselect(
                "Select failed interfaces",
                interfaces,
                key="failedinfs",
                default=st.session_state.activesnap.get("failedinfs", []),
                on_change=update_failed,
                kwargs={"key": "failedinfs"},
            )

            # Create a new snapshot by forking the active snapshot
            if failed_nodes or failed_interfaces:
                fork_snapshot(active_snapshot, failed_nodes, failed_interfaces)
                qs = convert_template(qlist)
                for q in qs:
                    qn = q["name"]
                    with st.status(f"Running '{qn}'...", expanded=False) as status:
                        answer = run_query(q)
                        if answer is None:
                            status.update(label=f"'{qn}' failed", state="error")
                        else:
                            status.update(label=f"'{qn}' complete", state="complete")
                        display_result(q["fun"], answer)

        except Exception as e:
            st.error(f"Error encountered in one of the questions: {e}")

    else:
        st.warning("Select some questions to proceed.")

else:
    st.warning("Please add a snapshot on the Home page to continue.")
