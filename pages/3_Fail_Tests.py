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
from pybatfish.question import bfq
from pybatfish.client.commands import bf_fork_snapshot
from pages.common.queries import run_query
import logging

logging.getLogger("pybatfish").setLevel(logging.WARNING)

MAXTABS = 6

# Start Page Here
st.set_page_config(layout="wide")
st.header("Failure Tests")
# st.markdown(APP)


def update_failed(key):
    st.session_state.activesnap[key] = st.session_state[key]


# Get selected questions
alldata = st.session_state.get("qlist")

if st.session_state.activesnap:
    st.subheader(f"Snapshot: {st.session_state.activesnap['name']}")

    # Run selected questions
    if alldata:
        questions_list = [
            (item["name"], item["fun"])
            for category in alldata
            for item in alldata[category]
            if item.get("fun")
        ]

        try:
            nodes = bfq.nodeProperties().answer().frame()
            interfaces = bfq.interfaceProperties().answer().frame()

            failed_nodes = st.multiselect(
                "Select failed nodes",
                nodes["Node"],
                key="failednodes",
                default=st.session_state.activesnap["failednodes"],
                on_change=update_failed,
                kwargs={"key": "failednodes"},  # do not change to 'args'
            )

            failed_interfaces = st.multiselect(
                "Select failed interfaces",
                interfaces["Interface"],
                key="failedinfs",
                default=st.session_state.activesnap["failedinfs"],
                on_change=update_failed,
                kwargs={"key": "failedinfs"},  # do not change to 'args'
            )

            if failed_nodes or failed_interfaces:
                bf_fork_snapshot(
                    st.session_state.activesnap["name"],
                    st.session_state.activesnap["name"] + "_Fail",
                    deactivate_nodes=failed_nodes,
                    deactivate_interfaces=failed_interfaces,
                    overwrite=True,
                )

                tabs = st.tabs([q[0] for q in questions_list])
                for idx, tab in enumerate(tabs):
                    with tab:
                        run_query(questions_list[idx][1])
            else:
                st.write("Select failed nodes and/or interfaces.")
        except Exception as e:
            st.error("Error running query: Probably no active snapshot.")
            st.error(e)

    else:
        st.warning("Select some questions to proceed.")

else:
    st.warning("Please add a snapshot to continue.")
