"""
Bat-Q's pages run headlessly against a real Batfish session.
"""

import uuid

import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

from common.assertions import result_key
from it_helpers import answer_frame, host_ip, page_path, rows, snapshot_zip
from conftest import HOST

pytestmark = pytest.mark.integration

LIVE = {"name": "live", "failednodes": [], "failedinfs": []}


@pytest.fixture(autouse=True)
def fresh_caches():
    """The setup page caches its session; do not reuse one from another test."""
    st.cache_data.clear()
    st.cache_resource.clear()
    yield
    st.cache_data.clear()
    st.cache_resource.clear()


def open_page(name, bf=None, **state):
    at = AppTest.from_file(page_path(name), default_timeout=300)
    if bf is not None:
        at.session_state["bf_session"] = bf
    for key, value in state.items():
        at.session_state[key] = value
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    return at


def all_cells(at):
    return {str(v) for df in at.dataframe for v in df.value.to_numpy().ravel()}


# ------------------------------------------------------------------- Analysis
def test_analysis_page_with_real_answers(bf):
    web = {"startLocation": "as1border1", "headers": {"dstIps": host_ip("host1")}}
    qlist = {
        "Node Properties": {"fun": "nodeProperties"},
        "Layer 3 Edges": {"fun": "layer3Edges"},
        "Traceroute": {"fun": "traceroute", "variants": [web]},
    }
    at = open_page("analysis", bf, activesnap=dict(LIVE), qlist=qlist)
    data = at.session_state["report_analysis_data"]
    assert [d["name"] for d in data] == list(qlist)
    # a dictionary is accepted where Batfish expects header constraints
    assert all(d["answer"] is not None for d in data), [d["name"] for d in data]
    assert "as1border1" in all_cells(at)
    assert not at.error
    assert at.get("download_button")


# --------------------------------------------------------------- Differential
def test_differential_page_between_live_and_candidate(bf):
    qlist = {"Differential Reachability": {"fun": "differentialReachability"}}
    at = open_page(
        "differential",
        bf,
        qlist=qlist,
        activesnap={"name": "live"},
        altsnap={"name": "candidate"},
    )
    assert not at.error
    assert not any("failed" in s.label for s in at.status), [s.label for s in at.status]


def test_a_plain_question_can_be_run_in_differential_mode(bf):
    """The page runs every selected question in differential mode."""
    answer = bf.q.nodeProperties().answer(
        snapshot="candidate", reference_snapshot="live"
    )
    assert answer is not None


# -------------------------------------------------------------- Failure tests
def test_failure_page_forks_the_snapshot_with_the_failed_node(bf):
    qlist = {"Node Properties": {"fun": "nodeProperties"}}
    at = open_page("fail_tests", bf, activesnap=dict(LIVE), qlist=qlist)
    assert "as1border1" in at.multiselect(key="failednodes").options
    at.multiselect(key="failednodes").select("as1border1").run()
    assert not at.exception, [e.value for e in at.exception]
    assert not at.error
    assert "live_Fail" in bf.list_snapshots()
    assert rows(bf, "routes", "live_Fail") < rows(bf, "routes", "live")


# ----------------------------------------------------------------- Assertions
def test_assertions_page_runs_against_the_real_server(bf):
    def item(aid, a_type, **extra):
        base = {
            "id": aid,
            "type": a_type,
            "name": "",
            "description": "",
            "scope": "active",
            "params": {},
        }
        return {**base, **extra}

    alist = [
        item("a1", "assert_no_forwarding_loops"),
        item("a2", "assert_no_undefined_references"),
        item(
            "a3",
            "assert_zero_results",
            question={"fun": "nodeProperties", "options": {}},
        ),
        item(
            "a4",
            "assert_num_results",
            params={"num": rows(bf, "nodeProperties")},
            question={"fun": "nodeProperties", "options": {}},
        ),
    ]
    at = open_page("assertions", bf, activesnap=dict(LIVE), alist=alist)
    [b for b in at.button if b.label == "Run all"][0].click().run()
    assert not at.exception, [e.value for e in at.exception]
    status = {
        a["id"]: at.session_state["assertion_results"][
            result_key(a["id"], "live")
        ].status
        for a in alist
    }
    assert status["a1"] == ("pass" if rows(bf, "detectLoops") == 0 else "fail")
    assert status["a2"] == ("pass" if rows(bf, "undefinedReferences") == 0 else "fail")
    assert status["a3"] == "fail" and status["a4"] == "pass"

    # the report page can use those results as they are
    report = open_page(
        "assertion_reporting",
        activesnap=dict(LIVE),
        alist=at.session_state["alist"],
        assertion_results=at.session_state["assertion_results"],
    )
    assert len(report.get("download_button")) == 2


# ---------------------------------------------------------------------- Setup
def test_setup_page_uploads_a_snapshot_to_a_real_server(bf, monkeypatch):
    network = f"batq_it_{uuid.uuid4().hex[:8]}"
    monkeypatch.setenv("BATFISH_SERVER", HOST)
    try:
        at = AppTest.from_file(page_path("net_setup"), default_timeout=300)
        at.session_state["network_name"] = network  # never touch "NETWORK"
        at.run()
        assert not at.exception, [e.value for e in at.exception]
        at.file_uploader[0].set_value(
            ("it_upload.zip", snapshot_zip("live"), "application/zip")
        ).run()
        assert not at.exception, [e.value for e in at.exception]
        assert not at.error, [e.value for e in at.error]
        options = next(s for s in at.selectbox if s.label == "Main Snapshot").options
        assert options == ["it_upload"]
        assert at.session_state["activesnap"]["name"] == "it_upload"
        # and the uploaded snapshot really holds the example network
        session = at.session_state["bf_session"]
        assert len(answer_frame(session, "nodeProperties", "it_upload")) >= 13
    finally:
        try:
            bf.delete_network(network)
        except Exception:
            pass
