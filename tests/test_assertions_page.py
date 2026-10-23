"""
Headless tests of views/assertions.py using Streamlit's AppTest and a fake
Batfish session (no Batfish server needed).
Run from the repository root:  python -m pytest tests
"""

import pandas as pd
import pytest

from fakes import ROOT, fake_session, page_path
from streamlit.testing.v1 import AppTest

PAGE = page_path("assertions")


@pytest.fixture
def app():
    log, calls = [], []
    at = AppTest.from_file(PAGE, default_timeout=30)
    at.session_state["bf_session"] = fake_session(log, calls)
    at.session_state["activesnap"] = {"name": "snap1"}
    at.run()
    assert not at.exception
    at.log = log
    at.calls = calls
    return at


def add(at, a_type, params=None, question=None, question_options=None):
    n = at.session_state["assertion_form_n"]
    at.selectbox(key=f"asrt{n}_type").select(a_type).run()
    if question:
        at.selectbox(key=f"asrt{n}_{a_type}_question").select(question).run()
    for name, value in (params or {}).items():
        at.text_input(key=f"asrt{n}_{a_type}_0_{name}").set_value(value)
    at.button(key=f"asrt{n}_submit").click().run()
    assert not at.exception


def result(at, aid):
    return at.session_state["assertion_results"].get(f"{aid}@snap1")


def populate(at):
    add(at, "assert_no_undefined_references")  # a1 -> pass
    add(at, "assert_no_forwarding_loops")  # a2 -> fail
    add(at, "assert_num_results", {"num": "2"}, "BGP Edges")  # a3 -> fail (3 rows)
    add(at, "assert_zero_results", question="Undefined References")  # a4 -> pass
    add(at, "assert_zero_results", question="Unused Structures")  # a5 -> error


def run_all(at):
    [b for b in at.button if b.label == "Run all"][0].click().run()
    assert not at.exception


def test_needs_snapshot():
    at = AppTest.from_file(PAGE, default_timeout=30)
    at.run()
    assert not at.exception
    assert any("snapshot" in w.value for w in at.warning)


def test_empty_page(app):
    assert any("No assertions yet" in i.value for i in app.info)


def test_add_assertions(app):
    populate(app)
    alist = app.session_state["alist"]
    assert [a["id"] for a in alist] == ["a1", "a2", "a3", "a4", "a5"]
    assert alist[2]["params"] == {"num": 2}
    assert alist[2]["question"]["fun"] == "bgpEdges"
    assert alist[2]["scope"] == "active"


def test_required_parameter_is_validated(app):
    add(app, "assert_num_results", question="BGP Edges")  # num missing
    assert app.session_state["alist"] == []
    assert any("num" in e.value for e in app.error)


def test_run_all_statuses_and_metrics(app):
    populate(app)
    run_all(app)
    status = {a: result(app, a).status for a in ("a1", "a2", "a3", "a4", "a5")}
    assert status == {
        "a1": "pass",
        "a2": "fail",
        "a3": "fail",
        "a4": "pass",
        "a5": "error",  # question failed: never reported as pass/fail
    }
    assert "boom" in result(app, "a5").message
    assert result(app, "a3").fun == "bgpEdges"
    assert [m.value for m in app.metric] == ["2", "2", "1", "0"]
    assert set(app.log) == {"snap1"}  # snapshot passed explicitly


def test_single_run(app):
    populate(app)
    app.button(key="run_a1").click().run()
    assert set(app.session_state["assertion_results"]) == {"a1@snap1"}


def test_delete_move_and_results_cleanup(app):
    populate(app)
    run_all(app)
    app.button(key="del_a2").click().run()
    assert [a["id"] for a in app.session_state["alist"]] == ["a1", "a3", "a4", "a5"]
    assert "a2@snap1" not in app.session_state["assertion_results"]
    app.button(key="up_a3").click().run()
    assert [a["id"] for a in app.session_state["alist"]] == ["a3", "a1", "a4", "a5"]
    app.button(key="down_a5").click().run()  # already last: no change
    assert [a["id"] for a in app.session_state["alist"]][-1] == "a5"
    assert not app.exception


def test_edit_updates_and_clears_result(app):
    populate(app)
    run_all(app)
    app.button(key="edit_a3").click().run()
    assert not app.exception
    n = app.session_state["assertion_form_n"]
    assert app.session_state["assertion_editing"] == "a3"
    field = app.text_input(key=f"asrt{n}_assert_num_results_0_num")
    assert field.value == "2"  # prefilled
    field.set_value("3")
    app.button(key=f"asrt{n}_submit").click().run()
    assert not app.exception
    a3 = [a for a in app.session_state["alist"] if a["id"] == "a3"][0]
    assert a3["params"] == {"num": 3}
    assert app.session_state["assertion_editing"] is None
    assert "a3@snap1" not in app.session_state["assertion_results"]
    app.button(key="run_a3").click().run()
    assert result(app, "a3").status == "pass"


def test_remove_all(app):
    populate(app)
    [b for b in app.button if b.label == "Remove all"][0].click().run()
    assert app.session_state["alist"] == []
    assert any("No assertions yet" in i.value for i in app.info)


# ------------------------------------------------------------- YAML files
EXAMPLE = str(ROOT / "examples" / "assertions.yaml")


def upload(at, content, name="assertions.yaml"):
    n = at.session_state["assertion_upload_n"]
    if isinstance(content, str):
        content = content.encode("utf-8")
    at.file_uploader(key=f"assertion_upload_{n}").set_value(
        (name, content, "text/yaml")
    ).run()


def download_disabled(at):
    return at.get("download_button")[0].proto.disabled


def test_load_example_file(app):
    app.session_state["qlist"] = {"Node Properties": {"fun": "nodeProperties"}}
    upload(app, open(EXAMPLE, "rb").read())
    assert not app.exception
    alist = app.session_state["alist"]
    assert [a["id"] for a in alist] == [f"a{i}" for i in range(1, 10)]
    assert alist[5]["params"] == {"num": 2}
    assert alist[5]["question"] == {"fun": "bgpEdges", "options": {}}
    assert alist[8]["type"] == "assert_has_route"
    # question selection is untouched, uploader was reset for the next load
    assert app.session_state["qlist"] == {"Node Properties": {"fun": "nodeProperties"}}
    assert app.session_state["assertion_upload_n"] == 1
    assert not app.error


def test_load_replaces_assertions_and_results(app):
    populate(app)
    run_all(app)
    upload(app, open(EXAMPLE, "rb").read())
    assert len(app.session_state["alist"]) == 9
    assert app.session_state["assertion_results"] == {}


def test_same_file_can_be_loaded_again(app):
    data = open(EXAMPLE, "rb").read()
    upload(app, data)
    app.button(key="del_a1").click().run()
    assert len(app.session_state["alist"]) == 8
    upload(app, data)
    assert len(app.session_state["alist"]) == 9


@pytest.mark.parametrize(
    "text, fragment",
    [
        ("assertions:\n  - type: assert_nope", "unknown assertion type"),
        (
            "assertions:\n  - type: assert_zero_results\n    question: {fun: nope}",
            "unknown question",
        ),
        ("not: [valid", "Invalid YAML"),
        ("version: 9\nassertions: []", "Unsupported"),
    ],
)
def test_bad_file_changes_nothing(app, text, fragment):
    add(app, "assert_no_forwarding_loops")
    before = list(app.session_state["alist"])
    upload(app, text)
    assert not app.exception
    assert app.session_state["alist"] == before
    assert any("No assertions were changed" in e.value for e in app.error)
    assert any(fragment in m.value for m in app.sidebar.markdown), [
        m.value for m in app.sidebar.markdown
    ]
    # the uploader is not reset, so the errors stay visible
    assert app.session_state["assertion_upload_n"] == 0


def test_non_text_file_is_rejected(app):
    upload(app, b"\xff\xfe\x00\x80binary")
    assert not app.exception
    assert any("not a UTF-8" in e.value for e in app.error)
    assert app.session_state["alist"] == []


def test_save_button_state(app):
    assert download_disabled(app)
    add(app, "assert_no_forwarding_loops")
    assert not download_disabled(app)


def test_phase_2_assertions_from_file_run(app):
    text = (
        "assertions:\n"
        "  - type: assert_flows_succeed\n"
        "    params:\n"
        "      startLocation: r1\n"
        "      headers: {dstIps: 10.0.0.1}\n"
        "  - type: assert_has_route\n"
        "    params:\n"
        "      expected_route: {Network: 10.0.0.0/24}\n"
        "      node: r1\n"
    )
    upload(app, text)
    assert len(app.session_state["alist"]) == 2
    run_all(app)
    assert result(app, "a1").status == "pass"
    assert result(app, "a2").status == "pass"
    app.button(key="edit_a1").click().run()  # loaded Phase 2 items can be edited
    assert not app.exception


def test_unknown_header_field_in_file_is_rejected(app):
    text = (
        "assertions:\n"
        "  - type: assert_flows_succeed\n"
        "    params:\n"
        "      startLocation: r1\n"
        "      headers: {dstIp: 10.0.0.1}\n"
    )
    upload(app, text)
    assert app.session_state["alist"] == []
    assert any("dstIp" in m.value for m in app.sidebar.markdown)


# ----------------------------------------------------------------- Phase 2
def test_every_registry_assertion_is_offered(app):
    from common.assertion_specs import ASSERTION_SPECS

    n = app.session_state["assertion_form_n"]
    offered = list(app.selectbox(key=f"asrt{n}_type").options)
    assert offered == [
        f"{sp['group']} · {sp['label']}" for sp in ASSERTION_SPECS.values()
    ]


def test_flow_assertions(app):
    headers = "{'dstIps': '10.0.0.1', 'applications': ['HTTP']}"
    add(app, "assert_flows_succeed", {"startLocation": "r1", "headers": headers})
    add(app, "assert_flows_succeed", {"startLocation": "bad", "headers": headers})
    add(app, "assert_flows_fail", {"startLocation": "r1", "headers": headers})
    assert app.session_state["alist"][0]["params"] == {
        "startLocation": "r1",
        "headers": {"dstIps": "10.0.0.1", "applications": ["HTTP"]},
    }
    run_all(app)
    assert [result(app, a).status for a in ("a1", "a2", "a3")] == [
        "pass",
        "fail",
        "pass",
    ]
    # the runner hands pybatfish a real HeaderConstraints and the snapshot
    from pybatfish.datamodel.flow import HeaderConstraints

    name, kw = app.calls[0]
    assert name == "flows_succeed" and kw["snapshot"] == "snap1"
    assert isinstance(kw["headers"], HeaderConstraints)
    assert kw["headers"].dstIps == "10.0.0.1" and kw["soft"] is False


def test_filter_assertions(app):
    headers = "{'srcIps': '1.1.1.1'}"
    add(app, "assert_filter_permits", {"filters": "acl_in", "headers": headers})
    add(app, "assert_filter_permits", {"filters": "deny_all", "headers": headers})
    add(
        app,
        "assert_filter_denies",
        {"filters": "acl_in", "headers": headers, "startLocation": "r1"},
    )
    add(app, "assert_filter_has_no_unreachable_lines", {"filters": "shadowed"})
    run_all(app)
    assert [result(app, a).status for a in ("a1", "a2", "a3", "a4")] == [
        "pass",
        "fail",
        "pass",
        "fail",
    ]
    denies = [kw for name, kw in app.calls if name == "filter_denies"][0]
    assert denies["startLocation"] == "r1"
    permits = [kw for name, kw in app.calls if name == "filter_permits"][0]
    assert "startLocation" not in permits  # optional, so not passed


ROUTE_BGP = "{'Network': '10.0.0.0/24', 'Protocol': 'bgp'}"
ROUTE_OTHER = "{'Network': '172.16.0.0/12'}"


def test_route_assertions(app):
    add(app, "assert_has_route", {"expected_route": ROUTE_BGP, "node": "r1"})  # a1
    add(app, "assert_has_route", {"expected_route": ROUTE_OTHER, "node": "r1"})  # a2
    add(app, "assert_has_route", {"expected_route": ROUTE_BGP, "node": "r9"})  # a3
    add(app, "assert_has_no_route", {"expected_route": ROUTE_OTHER, "node": "r1"})  # a4
    add(app, "assert_has_no_route", {"expected_route": ROUTE_BGP, "node": "r1"})  # a5
    add(  # a6: node exists, VRF does not
        app,
        "assert_has_no_route",
        {"expected_route": ROUTE_BGP, "node": "r1", "vrf": "nope"},
    )
    add(  # a7: non-default VRF
        app,
        "assert_has_route",
        {"expected_route": "{'Protocol': 'connected'}", "node": "r1", "vrf": "mgmt"},
    )
    run_all(app)
    status = {a: result(app, a).status for a in (f"a{i}" for i in range(1, 8))}
    assert status == {
        "a1": "pass",
        "a2": "fail",
        "a3": "fail",  # pybatfish: "No node: r9"
        "a4": "pass",
        "a5": "fail",
        "a6": "error",  # missing VRF: pybatfish would silently pass
        "a7": "pass",
    }
    assert "No node" in result(app, "a3").message
    assert "Not evaluated" in result(app, "a6").message
    # only the checked node/VRF is queried (default VRF unless given)
    assert ("routes", {"nodes": "r1", "vrfs": "default"}) in app.calls
    assert ("routes", {"nodes": "r1", "vrfs": "mgmt"}) in app.calls
    # failing route assertions keep the routes they looked at
    assert result(app, "a2").fun == "routes"
    assert isinstance(result(app, "a2").answer, pd.DataFrame)
    assert not app.exception


def test_phase_2_inputs_are_validated(app):
    add(app, "assert_flows_succeed", {"startLocation": "r1", "headers": "{'dstIp': 1}"})
    assert any("dstIp" in e.value for e in app.error)
    add(app, "assert_has_route", {"expected_route": "{}", "node": "r1"})
    assert any("must not be empty" in e.value for e in app.error)
    add(
        app, "assert_has_route", {"expected_route": ROUTE_BGP, "node": ""}
    )  # node missing
    assert any("node" in e.value for e in app.error)
    assert app.session_state["alist"] == []
