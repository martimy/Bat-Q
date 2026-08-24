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
from pybatfish.client.session import Session
import logging
import socket
from pages.common.utils import init_session_state

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
init_session_state()


@st.cache_data(ttl=60)
def test_connection(host, port=9996):
    """
    Test connection to host
    """
    # Create a socket object
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # Set the timeout to 5 seconds
    sock.settimeout(5)

    msg = ""
    # Attempt to connect to the host and port
    try:
        if sock.connect_ex((host, port)):  # returns 0 if successful
            msg = f"Host {host} is not reachable!"

    except socket.gaierror:
        msg = "Hostname could not be resolved!"
    except socket.timeout:
        msg = "Connection attempt timed out!"
    finally:
        sock.close()

    return msg


@st.cache_resource
def get_batfish_session_resource(host: str, network: str):
    """
    Creates and caches the Batfish Session resource.
    """
    bf = Session(host=host)
    bf.set_network(network)

    # Delete existing snapshots upon initial connection
    for snapshot in bf.list_snapshots():
        try:
            bf.delete_snapshot(snapshot)
        except Exception:
            pass

    return bf


def get_or_create_session(host, network):
    """
    Initializes or returns the active Batfish session stored in session_state.
    """
    if st.session_state.bf_session is None:
        st.session_state.bf_session = get_batfish_session_resource(host, network)

    return st.session_state.bf_session


def upload_snapshot(bf_session):
    with st.sidebar:
        uploaded_file = st.file_uploader("Add network snapshot", type="zip")
        if uploaded_file is not None:
            file_id = f"{uploaded_file.name}_{uploaded_file.size}"
            if st.session_state.get("last_uploaded_file") != file_id:
                new_name = uploaded_file.name.rsplit(".", 1)[0]
                try:
                    bf_session.init_snapshot(uploaded_file, name=new_name, overwrite=True)
                    bf_session.set_snapshot(new_name)
                    st.session_state.last_uploaded_file = file_id
                    st.session_state.activesnap["name"] = new_name
                    st.session_state.activesnap["failednodes"] = []
                    st.session_state.activesnap["failedinfs"] = []
                    st.rerun()
                except Exception as e:
                    st.error(f"File {uploaded_file.name} is not recognized! Error: {e}")


def find_index(lst, item):
    try:
        return lst.index(item)
    except ValueError:
        return 0


bf_host = os.getenv("BATFISH_SERVER") or "127.0.0.1"

st.set_page_config(layout="wide")
st.title("Bat-Q")

with st.expander("About", expanded=False):
    st.markdown(INTRO)

msg = test_connection(bf_host)
if msg == "":
    # Retrieve or create session via st.session_state
    bf_session = get_or_create_session(bf_host, BASE_NETWORK_NAME)

    upload_snapshot(bf_session)
    st.markdown(f"**Batfish Server:** {bf_host}")

    # Get all the snapshots in the current session
    snapshots = bf_session.list_snapshots()

    if snapshots:
        st.header("Select Snapshots", help=SNAPSHOT)

        idx = (
            find_index(snapshots, st.session_state.activesnap["name"])
            if st.session_state.activesnap
            else 0
        )

        select_snapshot = st.selectbox(
            "Main Snapshot", snapshots, index=idx, help="This is the base snapshot."
        )

        st.session_state.activesnap["name"] = bf_session.set_snapshot(select_snapshot)
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

        with st.sidebar:
            if st.button("Delete Snapshot"):
                # Updated from legacy bf_delete_snapshot
                bf_session.delete_snapshot(select_snapshot)
                if st.session_state.get("activesnap", {}).get("name") == select_snapshot:
                    st.session_state.activesnap = {}
                if st.session_state.get("altsnap", {}).get("name") == select_snapshot:
                    st.session_state.altsnap = {}
                st.rerun()
    else:
        st.warning("Upload a network snapshot.")
else:
    st.error(msg)