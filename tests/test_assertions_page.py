"""
Headless tests of views/assertions.py using Streamlit's AppTest and a fake
Batfish session (no Batfish server needed).
Run from the repository root:  python -m pytest tests
"""

import os
import sys
from types import SimpleNamespace

import pandas as pd
import pytest

pytest.importorskip("streamlit")
pytest.importorskip("plotly")
pytest.importorskip("networkx")

from pybatfish.exception import BatfishAssertException  # noqa: E402
from streamlit.testing.v1 import AppTest  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
PAGE = os.path.join(ROOT, "views", "assertions.py")


class FakeQuestion:
    def __init__(self, rows=0, fail=False, log=None):
        self.rows, self.fail, self.log = rows, fail, log

    def __call__(self, **options):
        return self

    def answer(self, snapshot=None):
        self.log.append(snapshot)
        if self.fail:
            raise RuntimeError("boom")
        return pd.DataFrame({"x": range(self.rows)})


def fake_session(log):
    def loops(**kw):
        raise BatfishAssertException("Found forwarding loops")

    return SimpleNamespace(
        q=SimpleNamespace(
            undefinedReferences=FakeQuestion(0, log=log),
            bgpEdges=FakeQuestion(3, log=log),
            unusedStructures=FakeQuestion(fail=True, log=log),
        ),
        asserts=SimpleNamespace(
            assert_no_forwarding_loops=loops,
            assert_no_undefined_references=lambda **kw: True,
        ),
    )


@pytest.fixture
def app():
    log = []
    at = AppTest.from_file(PAGE, default_timeout=30)
    at.session_state["bf_session"] = fake_session(log)
    at.session_state["activesnap"] = {"name": "snap1"}
    at.run()
    assert not at.exception
    at.log = log
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
