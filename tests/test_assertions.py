"""
Tests for the assertion registry, YAML schema and runner helpers.
Run from the repository root:  python -m pytest tests
"""

import inspect
import os
import sys

import pandas as pd
from types import SimpleNamespace
import pytest
from pybatfish.client import asserts as bf_asserts
from pybatfish.client.session import Asserts

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common import assertion_io as io  # noqa: E402
from common.assertion_specs import (  # noqa: E402
    ASSERTION_SPECS,
    HIDDEN_PARAMS,
)

EXAMPLE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "examples",
    "assertions.yaml",
)


def _pybatfish_function(name, spec):
    return getattr(Asserts if spec["call"] == "session" else bf_asserts, name)


# ---------------------------------------------------------------- registry
@pytest.mark.parametrize(
    "name", [n for n, s in ASSERTION_SPECS.items() if s["source"] == "pybatfish"]
)
def test_spec_matches_installed_pybatfish(name):
    """Catches pybatfish changes (renamed/added/removed parameters)."""
    spec = ASSERTION_SPECS[name]
    sig = inspect.signature(_pybatfish_function(name, spec))
    actual = {
        p: param
        for p, param in sig.parameters.items()
        if p not in HIDDEN_PARAMS and p != "self" and p != spec.get("answer_param")
    }
    assert set(actual) == {p["name"] for p in spec["params"]}
    for p in spec["params"]:
        required = actual[p["name"]].default is inspect.Parameter.empty
        assert required == (not p.get("optional", True)), p["name"]
    if spec.get("answer_param"):
        assert spec["answer_param"] in sig.parameters


def test_all_pybatfish_assertions_are_registered_or_ignored():
    available = {n for n in dir(Asserts) if n.startswith("assert_")}
    available |= {
        "assert_zero_results",
        "assert_num_results",
        "assert_has_route",
        "assert_has_no_route",
    }
    assert available <= set(ASSERTION_SPECS), available - set(ASSERTION_SPECS)


def test_answer_specs_declare_source_of_answer():
    for name, spec in ASSERTION_SPECS.items():
        if spec["call"] == "answer":
            assert spec["answer_from"] in ("question", "routes"), name
            assert spec["answer_param"], name


# --------------------------------------------------------------------- yaml
def test_example_file_loads_cleanly():
    with open(EXAMPLE) as f:
        alist, errors = io.load_assertions(f.read())
    assert errors == []
    assert len(alist) == 9
    assert [a["id"] for a in alist] == [f"a{i}" for i in range(1, 10)]


def test_round_trip_preserves_content():
    with open(EXAMPLE) as f:
        alist, _ = io.load_assertions(f.read())
    again, errors = io.load_assertions(io.dump_assertions(alist))
    assert errors == []
    assert again == alist
    assert "id" not in io.dump_assertions(alist)


@pytest.mark.parametrize(
    "text, fragment",
    [
        ("not: [valid", "Invalid YAML"),
        ("foo: 1", "no 'assertions'"),
        ("version: 2\nassertions: []", "Unsupported"),
        ("assertions: {}", "must be a list"),
        ("assertions:\n  - type: assert_nope", "unknown assertion type"),
        (
            "assertions:\n  - type: assert_num_results\n    question: {fun: bgpEdges}",
            "missing required parameter: num",
        ),
        (
            "assertions:\n  - type: assert_num_results\n    question: {fun: bgpEdges}\n    params: {num: '2'}",
            "must be of type int",
        ),
        (
            "assertions:\n  - type: assert_num_results\n    question: {fun: bgpEdges}\n    params: {num: true}",
            "must be of type int",
        ),
        (
            "assertions:\n  - type: assert_num_results\n    params: {num: 1}",
            "question with a 'fun' is required",
        ),
        (
            "assertions:\n  - type: assert_no_forwarding_loops\n    question: {fun: x}",
            "not allowed",
        ),
        (
            "assertions:\n  - type: assert_no_forwarding_loops\n    params: {bogus: 1}",
            "unknown parameter: bogus",
        ),
        (
            "assertions:\n  - type: assert_no_forwarding_loops\n    scope: sideways",
            "scope must be one of",
        ),
        (
            "assertions:\n  - type: assert_no_forwarding_loops\n    colour: red",
            "unknown key",
        ),
    ],
)
def test_invalid_files_are_rejected(text, fragment):
    alist, errors = io.load_assertions(text)
    assert alist == []
    assert any(fragment in e for e in errors), errors


def test_one_bad_assertion_rejects_the_whole_file():
    text = (
        "assertions:\n"
        "  - type: assert_no_forwarding_loops\n"
        "  - type: assert_nope\n"
    )
    alist, errors = io.load_assertions(text)
    assert alist == [] and len(errors) == 1 and "#2" in errors[0]


def test_unknown_question_checked_when_funs_given():
    text = "assertions:\n  - type: assert_zero_results\n    question: {fun: nope}"
    _, errors = io.load_assertions(text, known_funs={"bgpEdges"})
    assert any("unknown question" in e for e in errors)
    _, errors = io.load_assertions(text)  # not checked without a list
    assert errors == []


# ------------------------------------------------------------------- runner
def test_runner_statuses():
    pytest.importorskip("streamlit")
    from common import assertions as A

    df2 = pd.DataFrame({"a": [1, 2]})
    assert A.run_assertion("assert_num_results", answer=df2, num=2).status == "pass"
    assert A.run_assertion("assert_num_results", answer=df2, num=3).status == "fail"
    assert A.run_assertion("assert_zero_results", answer="x").status == "error"
    assert A.run_assertion("batq_min_results", answer=df2, num=2).status == "pass"
    assert A.run_assertion("batq_min_results", answer=df2, num=3).status == "fail"
    assert A.run_assertion("batq_min_results", answer=df2).status == "pass"
    assert A.run_assertion("batq_min_results", answer=pd.DataFrame()).status == "fail"


# ------------------------------------------------------ Phase 2: validation
@pytest.mark.parametrize(
    "params, fragment",
    [
        ({"startLocation": "r1", "headers": {"dstIp": "1.1.1.1"}}, "unknown field"),
        ({"startLocation": "r1", "headers": "dstIps=1.1.1.1"}, "must be of type"),
        ({"headers": {"dstIps": "1.1.1.1"}}, "missing required parameter"),
        ({"startLocation": 5, "headers": {}}, "must be of type"),
    ],
)
def test_flow_params_are_validated(params, fragment):
    errors = io.validate_assertion({"type": "assert_flows_succeed", "params": params})
    assert any(fragment in e for e in errors), errors


def test_valid_flow_and_route_params():
    ok = {
        "type": "assert_flows_fail",
        "params": {
            "startLocation": "r1",
            "headers": {"dstIps": "1.1.1.1", "applications": ["SSH"]},
        },
    }
    assert io.validate_assertion(ok) == []
    route = {
        "type": "assert_has_route",
        "params": {"node": "r1", "expected_route": {"Network": "10.0.0.0/24"}},
    }
    assert io.validate_assertion(route) == []
    route["params"]["expected_route"] = {}
    assert any("must not be empty" in e for e in io.validate_assertion(route))


# ---------------------------------------------------- Phase 2: runner logic
def _runner():
    pytest.importorskip("streamlit")
    from common import assertions as A

    return A


ROUTES = pd.DataFrame(
    [{"Node": "r1", "VRF": "default", "Network": "10.0.0.0/24", "Protocol": "bgp"}]
)


def test_route_assertions_on_a_frame():
    A = _runner()
    present = {"Network": "10.0.0.0/24"}
    absent = {"Network": "1.1.1.0/24"}
    run = A.run_assertion
    assert (
        run("assert_has_route", routes=ROUTES, expected_route=present, node="r1").status
        == "pass"
    )
    assert (
        run("assert_has_route", routes=ROUTES, expected_route=absent, node="r1").status
        == "fail"
    )
    assert (
        run(
            "assert_has_no_route", routes=ROUTES, expected_route=absent, node="r1"
        ).status
        == "pass"
    )
    assert (
        run(
            "assert_has_no_route", routes=ROUTES, expected_route=present, node="r1"
        ).status
        == "fail"
    )


def test_has_no_route_on_missing_node_or_vrf_is_an_error_not_a_pass():
    """pybatfish passes these with a warning; Bat-Q must not report a pass."""
    A = _runner()
    for kw in ({"node": "typo"}, {"node": "r1", "vrf": "typo"}):
        r = A.run_assertion(
            "assert_has_no_route",
            routes=ROUTES,
            expected_route={"Network": "10.0.0.0/24"},
            **kw,
        )
        assert r.status == "error", kw
        assert "Not evaluated" in r.message


def test_headers_become_header_constraints_and_bad_fields_error(monkeypatch):
    A = _runner()
    from pybatfish.datamodel.flow import HeaderConstraints

    seen = {}
    monkeypatch.setattr(
        A,
        "get_bf_session",
        lambda: SimpleNamespace(
            asserts=SimpleNamespace(
                assert_flows_succeed=lambda **kw: seen.update(kw) or True
            )
        ),
    )
    r = A.run_assertion(
        "assert_flows_succeed",
        snapshot="s1",
        startLocation="r1",
        headers={"dstIps": "10.0.0.1"},
    )
    assert r.status == "pass"
    assert isinstance(seen["headers"], HeaderConstraints) and seen["snapshot"] == "s1"
    r = A.run_assertion(
        "assert_flows_succeed", startLocation="r1", headers={"dstIp": "1"}
    )
    assert r.status == "error" and "dstIp" in r.message


def test_routes_question_failure_is_an_error(monkeypatch):
    A = _runner()

    class Boom:
        def __call__(self, **kw):
            raise RuntimeError("no connection")

    monkeypatch.setattr(
        A, "get_bf_session", lambda: SimpleNamespace(q=SimpleNamespace(routes=Boom()))
    )
    item = {
        "type": "assert_has_no_route",
        "params": {"node": "r1", "expected_route": {"Network": "10.0.0.0/24"}},
    }
    r = A.run_assertion_item(item, "s1")
    assert (
        r.status == "error" and "routes" in r.message and "no connection" in r.message
    )
