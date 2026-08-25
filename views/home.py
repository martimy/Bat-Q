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

import os
import streamlit as st
import pandas as pd
from pybatfish.client.session import Session
import logging
import socket
from common.utils import init_session_state

logging.getLogger("pybatfish").setLevel(logging.WARNING)

INTRO = r"""
**Bat-Q** v0.2  
Copyright 2023-2026 Maen Artimy    

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

NETWORK_HELP = r"""
A Batfish network is a workspace that groups related snapshots together 
(e.g. one network per site or per team). Changing the name switches to that 
network's own snapshots — a name that doesn't exist yet is created 
automatically.
"""

init_session_state()


@st.cache_data(ttl=60)
def test_connection(host, port=9996):
    """
    Test connection to host
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(5)
    msg = ""
    try:
        if sock.connect_ex((host, port)):
            msg = f"Host {host} is not reachable!"
    except socket.gaierror:
        msg = "Hostname could not be resolved!"
    except socket.timeout:
        msg = "Connection attempt timed out!"
    finally:
        sock.close()
    return msg


@st.cache_resource
def get_batfish_session_resource(host: str):
    """
    Creates and caches the Batfish Session resource. The session is not
    tied to a single network so its name can be changed later.
    """
    return Session(host=host)


def get_or_create_session(host):
    """
    Initializes or returns the active Batfish session stored in session_state.
    """
    if st.session_state.bf_session is None:
        st.session_state.bf_session = get_batfish_session_resource(host)
    return st.session_state.bf_session


def switch_network(bf_session, network_name):
    """
    Points the session at the requested network. Snapshot/answer selections
    from a previous network don't carry over, so they're cleared whenever
    the active network actually changes.
    """
    if st.session_state.current_network != network_name:
        bf_session.set_network(network_name)
        st.session_state.current_network = network_name
        st.session_state.activesnap = {}
        st.session_state.altsnap = {}
        st.session_state.last_uploaded_file = None


def unique_snapshot_name(base_name, existing):
    """
    Returns base_name if it's free, otherwise base_name_1, base_name_2, ...
    """
    if base_name not in existing:
        return base_name
    n = 1
    candidate = f"{base_name}_{n}"
    while candidate in existing:
        n += 1
        candidate = f"{base_name}_{n}"
    return candidate


def upload_snapshot(bf_session):
    with st.sidebar:
        uploaded_file = st.file_uploader("Add network snapshot", type="zip")
        if uploaded_file is not None:
            file_id = f"{uploaded_file.name}_{uploaded_file.size}"
            if st.session_state.get("last_uploaded_file") != file_id:
                base_name = uploaded_file.name.rsplit(".", 1)[0]
                existing = bf_session.list_snapshots()

                # Never overwrite an existing snapshot on upload -- give the
                # new one a unique name so it's always added to the list.
                new_name = unique_snapshot_name(base_name, existing)

                try:
                    bf_session.init_snapshot(uploaded_file, name=new_name, overwrite=False)
                    bf_session.set_snapshot(new_name)
                    st.session_state.last_uploaded_file = file_id
                    st.session_state.activesnap = {
                        "name": new_name,
                        "failednodes": [],
                        "failedinfs": [],
                    }
                    st.toast(f"Snapshot '{new_name}' uploaded successfully!", icon="✅")
                    st.rerun()
                except Exception as e:
                    st.error(f"File {uploaded_file.name} is not recognized! Error: {e}")


def clear_snapshot_refs(name):
    if st.session_state.activesnap.get("name") == name:
        st.session_state.activesnap = {}
    if st.session_state.altsnap.get("name") == name:
        st.session_state.altsnap = {}


def rename_snapshot_refs(old_name, new_name):
    if st.session_state.activesnap.get("name") == old_name:
        st.session_state.activesnap["name"] = new_name
    if st.session_state.altsnap.get("name") == old_name:
        st.session_state.altsnap["name"] = new_name


def render_snapshot_manager(bf_session):
    """
    Lists every snapshot in the current network with inline rename/delete
    controls. Pybatfish has no native rename, so a rename is implemented as
    fork-to-new-name followed by deleting the old one.
    """
    snapshots = bf_session.list_snapshots()

    st.subheader("Manage Snapshots", help=SNAPSHOT)

    if not snapshots:
        st.info("No snapshots yet. Upload one from the sidebar to get started.")
        return snapshots

    table = pd.DataFrame({"Snapshot": snapshots, "Rename to": snapshots, "Delete": False})

    edited = st.data_editor(
        table,
        column_config={
            "Snapshot": st.column_config.TextColumn("Snapshot", disabled=True),
            "Rename to": st.column_config.TextColumn(
                "Rename to", help="Edit and apply to rename this snapshot."
            ),
            "Delete": st.column_config.CheckboxColumn(
                "Delete", help="Mark for deletion, then click Apply."
            ),
        },
        hide_index=True,
        width='stretch', #replaces: use_container_width=True,
        key="snapshot_editor",
    )

    if st.button("Apply Snapshot Changes"):
        renamed, deleted, errors = 0, 0, []
        planned_names = set(snapshots)

        for _, row in edited.iterrows():
            old_name = row["Snapshot"]
            new_name = row["Rename to"].strip()

            if row["Delete"]:
                try:
                    bf_session.delete_snapshot(old_name)
                    clear_snapshot_refs(old_name)
                    planned_names.discard(old_name)
                    deleted += 1
                except Exception as e:
                    errors.append(f"Delete '{old_name}': {e}")
                continue

            if new_name and new_name != old_name:
                if new_name in planned_names:
                    errors.append(f"Rename '{old_name}': '{new_name}' is already in use.")
                    continue
                try:
                    bf_session.fork_snapshot(base_name=old_name, name=new_name, overwrite=True)
                    bf_session.delete_snapshot(old_name)
                    rename_snapshot_refs(old_name, new_name)
                    planned_names.discard(old_name)
                    planned_names.add(new_name)
                    renamed += 1
                except Exception as e:
                    errors.append(f"Rename '{old_name}' to '{new_name}': {e}")

        for err in errors:
            st.error(err)

        if renamed or deleted:
            st.toast(f"Applied: {renamed} renamed, {deleted} deleted.", icon="✅")
            st.rerun()

    return bf_session.list_snapshots()


def find_index(lst, item):
    try:
        return lst.index(item)
    except ValueError:
        return 0


# Page View Logic
bf_host = os.getenv("BATFISH_SERVER") or "127.0.0.1"

with st.expander("About", expanded=False):
    st.image("docs/pics/logo.svg", width=240)
    st.markdown(INTRO)

msg = test_connection(bf_host)
if msg == "":
    bf_session = get_or_create_session(bf_host)

    st.session_state.network_name = st.text_input(
        "Network Name",
        value=st.session_state.network_name,
        help=NETWORK_HELP,
    ).strip() or st.session_state.network_name

    switch_network(bf_session, st.session_state.network_name)
    upload_snapshot(bf_session)

    st.markdown(
        f"**Batfish Server:** {bf_host}  \n**Network:** {st.session_state.network_name}"
    )

    snapshots = render_snapshot_manager(bf_session)

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

        if st.session_state.activesnap.get("name") != select_snapshot:
            st.session_state.activesnap = {
                "name": bf_session.set_snapshot(select_snapshot),
                "failednodes": [],
                "failedinfs": [],
            }

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
    else:
        st.warning("Upload a network snapshot.")
else:
    st.error(msg)
