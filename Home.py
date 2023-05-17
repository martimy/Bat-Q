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
# from pybatfish.question import bfq
from pybatfish.client.commands import (
    bf_session,
    bf_set_network,
    bf_init_snapshot,
    bf_fork_snapshot,
    bf_set_snapshot,
    bf_delete_snapshot,
)
import logging


INTRO = """
This is a Streamlit app that enables the user to run network analysis 
queries using [Batfish](https://www.batfish.org/). 

Batfish is an open-source tool used for network analysis and verification. 
It allows network engineers to model and analyze network configurations and 
identify configuration errors, security vulnerabilities, and other potential 
issues before they cause problems.
"""
BASE_NETWORK_NAME = "NETWORK"


@st.cache_data
def init_host(host, network):
    bf_session.host = host
    bf_set_network(network)
    load_questions()


@st.cache_data
def init_snapshot(config_file, snapshot):
    bf_session.init_snapshot(config_file, name=snapshot, overwrite=True)

def upload_snapshot():
    filename = st.sidebar.file_uploader("Add network snapshot", type="zip")
    if filename:
        new_name = filename.name.split(".")[0]
        try:
            bf_init_snapshot(filename, name=new_name, overwrite=True)
            bf_set_snapshot(new_name)
        except:
            st.sidebar.error(f"File {filename.name} is not recognized!")

def find_index(lst, item):
    try:
        index = lst.index(item)
        return index
    except ValueError:
        return 0
    
logging.getLogger("pybatfish").setLevel(logging.WARNING)


if "activesnap" not in st.session_state:
    st.session_state.activesnap = None
    

bf_host = os.getenv("BATFISH_SERVER") or "127.0.0.1"

st.set_page_config(layout="wide")


# try
init_host(bf_host, BASE_NETWORK_NAME)


st.title("Bat-Q")
st.markdown(INTRO)

upload_snapshot()
st.markdown(f"**Batfish Server:** {bf_host}")

snapshots = bf_session.list_snapshots()

if snapshots:
    st.header("Loaded Snapshots")
    idx = (
        find_index(snapshots, st.session_state.activesnap)
        if st.session_state.activesnap
        else 0
    )
    select_snapshot = st.selectbox("Select Snapshot", snapshots, index=idx)
    st.session_state.activesnap = bf_set_snapshot(select_snapshot)
    st.write(f"Snapshot: {select_snapshot}")

    if st.sidebar.button("Delete Snapshot"):
        bf_delete_snapshot(select_snapshot)
        st.experimental_rerun()