"""
Tests for the assertion registry, YAML schema and runner helpers.
Run from the repository root:  python -m pytest tests
"""

import inspect
import os
import sys

import pandas as pd
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
    assert len(alist) == 6
    assert [a["id"] for a in alist] == [f"a{i}" for i in range(1, 7)]


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
