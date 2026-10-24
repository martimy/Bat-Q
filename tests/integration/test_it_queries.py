"""common/queries.py and the snapshot helpers against a real server."""

import pytest

from common import queries as Q
from it_helpers import answer_frame, hostnames, rows

pytestmark = pytest.mark.integration


def test_node_and_interface_properties(bf_state):
    nodes = Q.get_node_properties()
    assert set(hostnames("live")) <= set(nodes.str.lower())
    interfaces = Q.get_interface_properties()
    assert len(interfaces) > 0
    assert any("as1border1" in str(i).lower() for i in interfaces)


def test_set_snapshot_returns_its_name(bf_state):
    assert Q.set_snapshot("candidate") == "candidate"
    assert Q.set_snapshot("live") == "live"


def test_run_query_without_options_uses_the_current_snapshot(bf_state):
    answer = Q.run_query({"fun": "nodeProperties"})
    assert answer is not None
    assert len(answer.frame()) == rows(bf_state["bf_session"], "nodeProperties")


def test_run_query_passes_options(bf_state):
    answer = Q.run_query(
        {"fun": "nodeProperties", "options": {"nodes": "as1border1,as1border2"}}
    )
    assert sorted(answer.frame()["Node"]) == ["as1border1", "as1border2"]


def test_run_query_returns_none_for_a_question_that_fails(bf_state):
    assert Q.run_query({"fun": "noSuchQuestion"}) is None
    # a parameter the question does not have is rejected by pybatfish
    assert Q.run_query({"fun": "nodeProperties", "options": {"bogusParam": 1}}) is None


def test_differential_query_between_live_and_candidate(bf_state):
    """The candidate change breaks connectivity, so the differential has rows."""
    answer = Q.run_query(
        {"fun": "differentialReachability"}, snapshots=("live", "candidate")
    )
    assert answer is not None
    assert len(answer.frame()) > 0


def test_a_failure_fork_is_created_and_the_node_is_out_of_service(bf_state):
    bf = bf_state["bf_session"]
    Q.fork_snapshot("live", failed_nodes=["as1border1"], failed_interfaces=[])
    assert "live_Fail" in bf.list_snapshots()
    before = len(answer_frame(bf, "routes", "live"))
    after = len(answer_frame(bf, "routes", "live_Fail"))
    assert before > 0 and after < before  # a failed border router loses its routes


def test_forking_again_overwrites_the_previous_fork(bf_state):
    bf = bf_state["bf_session"]
    Q.fork_snapshot("live", failed_nodes=["as1border1"], failed_interfaces=[])
    Q.fork_snapshot("live", failed_nodes=["as3border1"], failed_interfaces=[])
    assert bf.list_snapshots().count("live_Fail") == 1
