"""
Headless tests of the Analysis, Differential Analysis, Failure Tests and
Analysis Reporting pages, using a fake Batfish session.
"""

import pytest
from streamlit.testing.v1 import AppTest

from fakes import FakeAnswer, FakeBatfish, page_path, trace

QLIST = {
    "Node Properties": {"category": "General", "fun": "nodeProperties"},
    "BGP Edges": {
        "category": "Routing",
        "fun": "bgpEdges",
        "variants": [{"nodes": "r1"}, {"nodes": "r2"}],
    },
}


def run_page(name, bf=None, **state):
    at = AppTest.from_file(page_path(name), default_timeout=30)
    if bf is not None:
        at.session_state["bf_session"] = bf
    for key, value in state.items():
        at.session_state[key] = value
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    return at


def labels(elements):
    return [e.value for e in elements]


# ================================================================= Analysis
def test_analysis_needs_a_snapshot():
    at = run_page("analysis", FakeBatfish())
    assert any("add a snapshot" in w.value for w in at.warning)


def test_analysis_without_questions_asks_for_some():
    bf = FakeBatfish()
    at = run_page("analysis", bf, activesnap={"name": "snapA"})
    assert any("Select some questions" in w.value for w in at.warning)
    assert any("No data available to export" in i.value for i in at.sidebar.info)
    assert bf.calls_named("answer") == []


def test_analysis_runs_every_selected_question_on_the_active_snapshot():
    bf = FakeBatfish()
    at = run_page("analysis", bf, activesnap={"name": "snapA"}, qlist=QLIST)
    assert ("set_snapshot", "snapA") in bf.calls
    assert bf.answers_for("nodeProperties") == [({}, {})]
    assert bf.answers_for("bgpEdges") == [({"nodes": "r1"}, {}), ({"nodes": "r2"}, {})]
    assert any("Snapshot: snapA" in s.value for s in at.subheader)
    assert len(at.dataframe) >= 3  # one table per answer


def test_analysis_keeps_results_for_the_reports():
    bf = FakeBatfish()
    at = run_page("analysis", bf, activesnap={"name": "snapA"}, qlist=QLIST)
    data = at.session_state["report_analysis_data"]
    assert [d["name"] for d in data] == ["Node Properties", "BGP Edges", "BGP Edges_1"]
    assert [d["fun"] for d in data] == ["nodeProperties", "bgpEdges", "bgpEdges"]
    assert [d["options"] for d in data] == [None, {"nodes": "r1"}, {"nodes": "r2"}]
    assert all(d["answer"] is not None for d in data)


def test_analysis_offers_the_spreadsheet_download():
    at = run_page("analysis", FakeBatfish(), activesnap={"name": "snapA"}, qlist=QLIST)
    buttons = at.get("download_button")
    assert [b.proto.label for b in buttons] == ["Download Spreadsheet (.xlsx)"]


def test_analysis_continues_when_a_question_fails():
    bf = FakeBatfish(answers={"bgpEdges": RuntimeError("boom")})
    at = run_page("analysis", bf, activesnap={"name": "snapA"}, qlist=QLIST)
    data = at.session_state["report_analysis_data"]
    assert [d["answer"] is None for d in data] == [False, True, True]
    assert at.get("download_button")  # the question that worked is still exported
    assert any("failed" in s.label for s in at.status)


def test_analysis_with_only_failing_questions_has_nothing_to_export():
    bf = FakeBatfish(answers={"nodeProperties": RuntimeError("boom")})
    at = run_page(
        "analysis",
        bf,
        activesnap={"name": "snapA"},
        qlist={"Node Properties": QLIST["Node Properties"]},
    )
    assert at.get("download_button") == []
    assert any("No data available to export" in i.value for i in at.sidebar.info)


def test_analysis_shows_traceroute_answers():
    answer = FakeAnswer(
        rows=[{"Traces": [trace("ACCEPTED"), trace("DENIED_IN")]}],
        extra={"status": "OK"},
    )
    bf = FakeBatfish(answers={"traceroute": answer})
    qlist = {"Traceroute": {"category": "Reachability", "fun": "traceroute"}}
    at = run_page("analysis", bf, activesnap={"name": "snapA"}, qlist=qlist)
    assert any("Trace status:" in m.value for m in at.markdown)
    assert [t.label for t in at.tabs] == ["Trace 1", "Trace 2"]


def test_analysis_shows_a_message_when_an_answer_cannot_be_formatted():
    bf = FakeBatfish(answers={"nodeProperties": FakeAnswer(RuntimeError("bad frame"))})
    at = run_page(
        "analysis",
        bf,
        activesnap={"name": "snapA"},
        qlist={"Node Properties": QLIST["Node Properties"]},
    )
    assert any("Unable to display formatted answer" in e.value for e in at.error)


# ========================================================= Differential
def snaps(active="snapA", alt="snapB"):
    return {"activesnap": {"name": active}, "altsnap": {"name": alt}}


@pytest.mark.parametrize(
    "state",
    [
        {},
        {"activesnap": {"name": "snapA"}},
        {"activesnap": {"name": "snapA"}, "altsnap": {"name": "snapA"}},
        {"activesnap": {}, "altsnap": {"name": "snapB"}},
    ],
)
def test_differential_needs_two_distinct_snapshots(state):
    bf = FakeBatfish()
    at = run_page("differential", bf, **state)
    assert any("two distinct snapshots" in w.value for w in at.warning)
    assert bf.calls_named("answer") == []


def test_differential_without_questions_asks_for_some():
    at = run_page("differential", FakeBatfish(), **snaps())
    assert any("Select some questions" in w.value for w in at.warning)


def test_differential_compares_the_alternate_to_the_reference():
    bf = FakeBatfish()
    at = run_page("differential", bf, qlist=QLIST, **snaps("ref", "alt"))
    assert bf.answers_for("nodeProperties") == [
        ({}, {"snapshot": "alt", "reference_snapshot": "ref"})
    ]
    assert len(bf.answers_for("bgpEdges")) == 2
    titles = [s.value for s in at.subheader]
    assert "Reference snapshot: ref" in titles and "Alternate snapshot: alt" in titles


def test_differential_shows_reference_and_snapshot_traces():
    answer = FakeAnswer(
        rows=[
            {
                "Reference_Traces": [trace("ACCEPTED")],
                "Snapshot_Traces": [trace("NO_ROUTE")],
            }
        ],
        extra={"status": "OK"},
    )
    bf = FakeBatfish(answers={"differentialReachability": answer})
    qlist = {"Differential Reachability": {"fun": "differentialReachability"}}
    at = run_page("differential", bf, qlist=qlist, **snaps())
    text = labels(at.markdown)
    assert "**Reference Trace:**" in text and "**Snapshot Trace:**" in text
    assert any("ACCEPTED" in m for m in text) and any("NO_ROUTE" in m for m in text)


def test_differential_survives_a_failed_question():
    bf = FakeBatfish(answers={"nodeProperties": RuntimeError("boom")})
    at = run_page(
        "differential",
        bf,
        qlist={"Node Properties": QLIST["Node Properties"]},
        **snaps(),
    )
    assert any("failed" in s.label for s in at.status)


# ========================================================= Failure Tests
def test_failure_tests_need_a_snapshot():
    at = run_page("fail_tests", FakeBatfish())
    assert any("add a snapshot" in w.value for w in at.warning)


def test_failure_tests_without_questions_asks_for_some():
    at = run_page("fail_tests", FakeBatfish(), activesnap={"name": "snapA"})
    assert any("Select some questions" in w.value for w in at.warning)


def test_failure_tests_do_nothing_until_something_fails():
    bf = FakeBatfish()
    at = run_page("fail_tests", bf, activesnap={"name": "snapA"}, qlist=QLIST)
    assert at.multiselect(key="failednodes").options == ["r1", "r2"]
    assert at.multiselect(key="failedinfs").options == ["r1[Gi0]", "r2[Gi0]"]
    assert bf.calls_named("fork_snapshot") == []
    assert bf.answers_for("bgpEdges") == []


def test_failed_nodes_fork_the_snapshot_and_run_the_questions_on_it():
    bf = FakeBatfish()
    at = run_page("fail_tests", bf, activesnap={"name": "snapA"}, qlist=QLIST)
    at.multiselect(key="failednodes").select("r1").run()
    assert not at.exception
    fork = bf.calls_named("fork_snapshot")[0][1]
    assert fork == {
        "base_name": "snapA",
        "name": "snapA_Fail",
        "deactivate_nodes": ["r1"],
        "deactivate_interfaces": [],
        "overwrite": True,
    }
    assert len(bf.answers_for("bgpEdges")) == 2  # questions ran after the fork
    assert bf.current == "snapA_Fail"
    # the choice is remembered on the active snapshot
    assert at.session_state["activesnap"]["failednodes"] == ["r1"]


def test_failed_interfaces_alone_are_enough():
    bf = FakeBatfish()
    at = run_page("fail_tests", bf, activesnap={"name": "snapA"}, qlist=QLIST)
    at.multiselect(key="failedinfs").select("r2[Gi0]").run()
    fork = bf.calls_named("fork_snapshot")[0][1]
    assert fork["deactivate_nodes"] == [] and fork["deactivate_interfaces"] == [
        "r2[Gi0]"
    ]


def test_failure_tests_remember_earlier_choices():
    bf = FakeBatfish()
    at = run_page(
        "fail_tests",
        bf,
        activesnap={"name": "snapA", "failednodes": ["r2"], "failedinfs": []},
        qlist=QLIST,
    )
    assert at.multiselect(key="failednodes").value == ["r2"]
    assert bf.calls_named("fork_snapshot")[0][1]["deactivate_nodes"] == ["r2"]


def test_failure_tests_report_errors_instead_of_crashing():
    bf = FakeBatfish(answers={"nodeProperties": RuntimeError("server down")})
    at = run_page("fail_tests", bf, activesnap={"name": "snapA"}, qlist=QLIST)
    assert any(
        "Error encountered" in e.value and "server down" in e.value for e in at.error
    )


# ================================================================ Reporting
def test_reporting_needs_results():
    at = run_page("reporting")
    assert any("Run some questions" in w.value for w in at.warning)
    assert at.get("download_button") == []


def test_reporting_builds_a_report_from_analysis_results():
    bf = FakeBatfish()
    analysis = run_page("analysis", bf, activesnap={"name": "snapA"}, qlist=QLIST)
    at = run_page(
        "reporting",
        report_analysis_data=analysis.session_state["report_analysis_data"],
        activesnap={"name": "snapA"},
    )
    buttons = at.get("download_button")
    assert [b.proto.label for b in buttons] == ["Download HTML Report"]
    assert not buttons[0].proto.disabled


def test_reporting_handles_a_failed_question_in_the_data():
    data = [
        {
            "name": "Node Properties",
            "fun": "nodeProperties",
            "options": None,
            "answer": None,
        }
    ]
    at = run_page("reporting", report_analysis_data=data, activesnap={"name": "s"})
    assert at.get("download_button")
    assert not at.error
