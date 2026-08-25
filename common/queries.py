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


def get_bf_session():
    """
    Returns the active Batfish session from session_state.
    """
    bf = st.session_state.get("bf_session")
    if bf is None:
        raise RuntimeError(
            "Batfish session is not initialized. Please connect on the Home page."
        )
    return bf


def get_node_properties():
    bf = get_bf_session()
    return bf.q.nodeProperties().answer().frame()["Node"]


def get_interface_properties():
    bf = get_bf_session()
    return bf.q.interfaceProperties().answer().frame()["Interface"]


def set_snapshot(active_snapshot):
    bf = get_bf_session()
    return bf.set_snapshot(active_snapshot)


def fork_snapshot(active_snapshot, failed_nodes=None, failed_interfaces=None):
    bf = get_bf_session()
    bf.fork_snapshot(
        base_name=active_snapshot,
        name=active_snapshot + "_Fail",
        deactivate_nodes=failed_nodes,
        deactivate_interfaces=failed_interfaces,
        overwrite=True,
    )


def run_query(question, snapshots=None):
    """
    Run Batfish question and get an answer.
    """
    answer = None
    question_fun = question["fun"]
    try:
        bf = get_bf_session()
        fun = getattr(bf.q, question_fun)
        qargs = question.get("options")

        if snapshots:
            if qargs:
                answer = fun(**qargs).answer(
                    snapshot=snapshots[1], reference_snapshot=snapshots[0]
                )
            else:
                answer = fun().answer(
                    snapshot=snapshots[1], reference_snapshot=snapshots[0]
                )
        else:
            if qargs:
                answer = fun(**qargs).answer()
            else:
                answer = fun().answer()

    except Exception as e:
        # TODO: either send to logs or display on screen
        print(e)
    finally:
        return answer
