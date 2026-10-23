"""Tests for common/queries.py with a fake Batfish session."""

from types import SimpleNamespace

import pandas as pd
import pytest

from common import queries as Q


class Recorder:
    """Callable question: records how it was called and what answer() got."""

    def __init__(self, frame=None, boom=None):
        self.calls, self.answers = [], []
        self.frame, self.boom = frame, boom

    def __call__(self, **kw):
        self.calls.append(kw)
        return self

    def answer(self, **kw):
        self.answers.append(kw)
        if self.boom:
            raise self.boom
        return SimpleNamespace(frame=lambda: self.frame, kw=kw)


@pytest.fixture
def bf(bf_session_state):
    session = SimpleNamespace(
        q=SimpleNamespace(
            nodeProperties=Recorder(pd.DataFrame({"Node": ["r1", "r2"]})),
            interfaceProperties=Recorder(pd.DataFrame({"Interface": ["r1[Gi0]"]})),
            bgpEdges=Recorder(),
            broken=Recorder(boom=RuntimeError("server error")),
        ),
        set_snapshot=lambda name: f"set:{name}",
        forks=[],
    )
    session.fork_snapshot = lambda **kw: session.forks.append(kw)
    bf_session_state["bf_session"] = session
    return session


# ------------------------------------------------------------------ session
def test_get_bf_session_returns_the_active_session(bf):
    assert Q.get_bf_session() is bf


def test_get_bf_session_without_a_session_explains_what_to_do(bf_session_state):
    with pytest.raises(RuntimeError, match="Home page"):
        Q.get_bf_session()
    bf_session_state["bf_session"] = None
    with pytest.raises(RuntimeError):
        Q.get_bf_session()


# ---------------------------------------------------------------- helpers
def test_node_and_interface_properties_return_one_column(bf):
    assert Q.get_node_properties().tolist() == ["r1", "r2"]
    assert Q.get_interface_properties().tolist() == ["r1[Gi0]"]


def test_set_snapshot_passes_through(bf):
    assert Q.set_snapshot("snap1") == "set:snap1"


def test_fork_snapshot_names_the_fork_and_overwrites(bf):
    Q.fork_snapshot("snap1", failed_nodes=["r1"], failed_interfaces=None)
    assert bf.forks == [
        {
            "base_name": "snap1",
            "name": "snap1_Fail",
            "deactivate_nodes": ["r1"],
            "deactivate_interfaces": None,
            "overwrite": True,
        }
    ]


# ---------------------------------------------------------------- run_query
def test_run_query_without_options(bf):
    answer = Q.run_query({"fun": "nodeProperties"})
    assert answer.kw == {}
    assert bf.q.nodeProperties.calls == [{}]


def test_run_query_passes_options_to_the_question(bf):
    Q.run_query({"fun": "bgpEdges", "options": {"nodes": "r1"}})
    assert bf.q.bgpEdges.calls == [{"nodes": "r1"}]
    assert bf.q.bgpEdges.answers == [{}]


def test_run_query_with_two_snapshots_compares_second_to_first(bf):
    """snapshots = (reference, current): current is the one being analysed."""
    Q.run_query({"fun": "bgpEdges"}, snapshots=("base", "changed"))
    assert bf.q.bgpEdges.answers == [
        {"snapshot": "changed", "reference_snapshot": "base"}
    ]
    Q.run_query({"fun": "bgpEdges", "options": {"nodes": "r1"}}, ("a", "b"))
    assert bf.q.bgpEdges.calls[-1] == {"nodes": "r1"}
    assert bf.q.bgpEdges.answers[-1] == {"snapshot": "b", "reference_snapshot": "a"}


def test_run_query_returns_none_when_the_question_fails(bf):
    assert Q.run_query({"fun": "broken"}) is None


def test_run_query_returns_none_for_an_unknown_question(bf):
    assert Q.run_query({"fun": "doesNotExist"}) is None


def test_run_query_returns_none_without_a_session(bf_session_state):
    assert Q.run_query({"fun": "nodeProperties"}) is None
