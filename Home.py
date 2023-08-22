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
from pybatfish.client.commands import (
    bf_session,
    bf_set_network,
    bf_init_snapshot,
    bf_set_snapshot,
    bf_delete_snapshot,
)
import logging
import socket

logging.getLogger("pybatfish").setLevel(logging.WARNING)

INTRO = r"""
**Bat-Q** v0.1  
Copyright 2023 Maen Artimy    

Bat-Q is a web app that lets you analyze your network configuration files using 
[Batfish](https://www.batfish.org/), a powerful open source network analysis 
tool. Batfish models and analyzes network configurations to identify 
configuration errors, security vulnerabilities, and other potential issues. 
With Bat-Q, you can easily run various queries on your network and get 
instant feedback in a table format.

Bat-Q is built with [Streamlit](https://streamlit.io/), a Python framework for 
creating data-driven web apps. You can find the source code of Bat-Q on 
[GitHub](https://github.com/martimy/Bat-Q), 
where you can also learn how to install and use the app. Bat-Q requires 
Python 3.6+, as well as a Batfish Docker container that can be pulled from 
Docker Hub.

If you are interested in network analysis and want to try out Batfish, Bat-Q is 
a great way to get started. You can explore different categories of questions 
that Batfish offers, such as questions about reachability, routing, access 
lists, and VPN tunnels. These questions allows you to analyze you network 
configuration and you can also investigate the network reaction to various 
failure scenarios.

Bat-Q is open-source software released under the Apache License, Version 2.0. 
By using or contributing to Bat-Q, you agree to the terms and 
conditions of this license.
"""

SNAPSHOT = r"""
A Batfish snapshot is a state of a network at a given time, represented by the 
configuration files of the network devices and some other supplemental 
information. The files must be organized in a specific folder structure. In 
Bat-Q, the folders must be compressed in .zip file.
"""

BASE_NETWORK_NAME = "NETWORK"

# Initialize the session state

if "activesnap" not in st.session_state:
    st.session_state.activesnap = {}

if "altsnap" not in st.session_state:
    st.session_state.altsnap = {}

if "qlist" not in st.session_state:
    # qlist saves the current selection of questions
    st.session_state.qlist = {}

if "cats" not in st.session_state:
    # cats holds the former selection of questions
    st.session_state.cats = {}


# End session states


def test_connection(host, port=9996):
    """
    Test connection to host
    """
    # Create a socket object
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # Set the timeout to 5 seconds
    sock.settimeout(5)

    success = False
    msg = ""
    # Attempt to connect to the host and port
    try:
        result = sock.connect_ex((host, port))
        if result == 0:
            success = True
            msg = f"Host {host} is reachable."
        else:
            msg = f"Host {host} is not reachable!"

    except socket.gaierror:
        msg = "Hostname could not be resolved!"
    except socket.timeout:
        msg = "Connection attempt timed out!"
    finally:
        sock.close()

    return success, msg


@st.cache_data
def init_host(host, network):
    bf_session.host = host
    bf_set_network(network)
    load_questions()


@st.cache_data
def init_snapshot(config_file, snapshot):
    bf_session.init_snapshot(config_file, name=snapshot, overwrite=True)


def upload_snapshot():
    uploaded_file = st.sidebar.file_uploader("Add network snapshot", type="zip")
    if uploaded_file:
        new_name = uploaded_file.name.split(".")[0]
        try:
            bf_init_snapshot(uploaded_file, name=new_name, overwrite=True)
            bf_set_snapshot(new_name)
        except:
            st.sidebar.error(f"File {uploaded_file.name} is not recognized!")


def find_index(lst, item):
    try:
        index = lst.index(item)
        return index
    except ValueError:
        return 0


bf_host = os.getenv("BATFISH_SERVER") or "127.0.0.1"

st.set_page_config(layout="wide")
st.title("Bat-Q")

with st.expander("About", expanded=False):
    st.markdown(INTRO)

success, msg = test_connection(bf_host)
if success:
    init_host(bf_host, BASE_NETWORK_NAME)

    upload_snapshot()
    st.markdown(f"**Batfish Server:** {bf_host}")

    # Get all the snapshots in the current session
    snapshots = bf_session.list_snapshots()

    if snapshots:
        st.header("Select Snapshots", help=SNAPSHOT)

        # Find the index of the saved snapshot among all snapshots
        idx = (
            find_index(snapshots, st.session_state.activesnap["name"])
            if st.session_state.activesnap
            else 0
        )

        # Select the base snapshot
        select_snapshot = st.selectbox(
            "Main Snapshot", snapshots, index=idx, help="This is the base snapshot."
        )

        # if the index of the returned selection is different:
        st.session_state.activesnap["name"] = bf_set_snapshot(select_snapshot)
        # This rests the lists when Home pages is visited
        st.session_state.activesnap["failednodes"] = []
        st.session_state.activesnap["failedinfs"] = []

        idx2 = (
            find_index(snapshots, st.session_state.altsnap["name"])
            if st.session_state.altsnap
            else 0
        )

        st.session_state.altsnap["name"] = st.selectbox(
            "Alternate Snapshot",
            snapshots,
            index=idx2,
            help="This snapshot is used for comparsions.",
        )

        if st.sidebar.button("Delete Snapshot"):
            bf_delete_snapshot(select_snapshot)
            st.session_state.activesnap = {}
            st.experimental_rerun()

else:
    st.error(msg)
