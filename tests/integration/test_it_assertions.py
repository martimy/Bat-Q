"""
Bat-Q's assertion runner against a real server. Verdicts are compared with
what Batfish itself answers to the same question (see README.md).
"""

import pytest
from pybatfish.client.asserts import UNESTABLISHED_OSPF_SESSION_STATUS_SPEC
from pybatfish.datamodel.flow import HeaderConstraints, PathConstraints

from common.assertions import run_assertion, run_assertion_item
from it_helpers import answer_frame, host_ip, rows

pytestmark = pytest.mark.integration

SNAPSHOTS = ["live", "candidate"]


def verdict(condition):
    return "pass" if condition else "fail"


# ------------------------------------------------------- snapshot-level checks
SNAPSHOT_CHECKS = {
    "assert_no_forwarding_loops": lambda bf, s: rows(bf, "detectLoops", s) == 0,
    "assert_no_undefined_references": lambda bf, s: rows(bf, "undefinedReferences", s)
    == 0,
    "assert_no_unestablished_bgp_sessions": lambda bf, s: rows(
        bf, "bgpSessionStatus", s, status="NOT_ESTABLISHED"
    )
    == 0,
    "assert_no_incompatible_ospf_sessions": lambda bf, s: rows(
        bf,
        "ospfSessionCompatibility",
        s,
        statuses=UNESTABLISHED_OSPF_SESSION_STATUS_SPEC,
    )
    == 0,
}


@pytest.mark.parametrize("snapshot", SNAPSHOTS)
@pytest.mark.parametrize("name", list(SNAPSHOT_CHECKS))
def test_snapshot_checks_agree_with_batfish(bf_state, name, snapshot):
    bf = bf_state["bf_session"]
    result = run_assertion(name, snapshot=snapshot)
    assert result.status == verdict(SNAPSHOT_CHECKS[name](bf, snapshot)), result.message


@pytest.mark.parametrize(
    "name", ["assert_no_incompatible_bgp_sessions", "assert_no_duplicate_router_ids"]
)
def test_other_snapshot_checks_run_without_error(bf_state, name):
    assert run_assertion(name, snapshot="live").status in ("pass", "fail")


def test_node_options_are_passed_through(bf_state):
    result = run_assertion(
        "assert_no_unestablished_bgp_sessions", snapshot="live", nodes="as1border1"
    )
    expected = rows(
        bf_state["bf_session"],
        "bgpSessionStatus",
        "live",
        status="NOT_ESTABLISHED",
        nodes="as1border1",
    )
    assert result.status == verdict(expected == 0), result.message


# ------------------------------------------------------------------- filters
FILTER = "OUTSIDE_TO_INSIDE"
TELNET = {"dstIps": "2.128.0.0/16", "applications": ["TELNET"]}
WEB = {"srcIps": "1.0.0.0/8", "dstIps": host_ip("host1"), "applications": ["HTTP"]}


def test_unreachable_filter_lines_agree_with_batfish(bf_state):
    expected = rows(
        bf_state["bf_session"], "filterLineReachability", "live", filters=FILTER
    )
    result = run_assertion(
        "assert_filter_has_no_unreachable_lines", snapshot="live", filters=FILTER
    )
    assert result.status == verdict(expected == 0), result.message


@pytest.mark.parametrize("snapshot", SNAPSHOTS)
@pytest.mark.parametrize("headers", [TELNET, WEB], ids=["telnet", "web"])
def test_filter_assertions_agree_with_batfish(bf_state, snapshot, headers):
    bf = bf_state["bf_session"]
    hc = HeaderConstraints(**headers)
    denied = rows(
        bf, "searchFilters", snapshot, filters=FILTER, headers=hc, action="deny"
    )
    permitted = rows(
        bf, "searchFilters", snapshot, filters=FILTER, headers=hc, action="permit"
    )
    permits = run_assertion(
        "assert_filter_permits", snapshot=snapshot, filters=FILTER, headers=headers
    )
    denies = run_assertion(
        "assert_filter_denies", snapshot=snapshot, filters=FILTER, headers=headers
    )
    assert permits.status == verdict(denied == 0), permits.message
    assert denies.status == verdict(permitted == 0), denies.message


# ------------------------------------------------------------------ reachability
FLOWS = [
    ("as1border1", {"dstIps": host_ip("host1"), "applications": ["HTTP"]}),
    ("as3border1", {"dstIps": host_ip("host2"), "applications": ["HTTP"]}),
    ("as2dept1", {"dstIps": host_ip("host1"), "applications": ["TELNET"]}),
]


@pytest.mark.parametrize("snapshot", SNAPSHOTS)
@pytest.mark.parametrize(
    "start, headers", FLOWS, ids=["as1-http", "as3-http", "dept-telnet"]
)
def test_flow_assertions_agree_with_batfish(bf_state, snapshot, start, headers):
    bf = bf_state["bf_session"]
    kwargs = dict(
        pathConstraints=PathConstraints(startLocation=start),
        headers=HeaderConstraints(**headers),
    )
    failing = rows(bf, "reachability", snapshot, actions="failure", **kwargs)
    succeeding = rows(bf, "reachability", snapshot, actions="success", **kwargs)
    succeeds = run_assertion(
        "assert_flows_succeed", snapshot=snapshot, startLocation=start, headers=headers
    )
    fails = run_assertion(
        "assert_flows_fail", snapshot=snapshot, startLocation=start, headers=headers
    )
    assert succeeds.status == verdict(failing == 0), succeeds.message
    assert fails.status == verdict(succeeding == 0), fails.message


def test_a_flow_from_an_unknown_start_location_is_an_error_not_a_pass(bf_state):
    for name in ("assert_flows_succeed", "assert_flows_fail"):
        result = run_assertion(
            name,
            snapshot="live",
            startLocation="no_such_device",
            headers={"dstIps": host_ip("host1")},
        )
        assert result.status == "error", (name, result.message)


# ---------------------------------------------------- answers of questions
def item(a_type, question=None, **params):
    entry = {"id": "a1", "type": a_type, "params": params}
    if question:
        entry["question"] = question
    return entry


NODES = {"fun": "nodeProperties"}


def test_row_count_assertions(bf_state):
    bf = bf_state["bf_session"]
    n = rows(bf, "nodeProperties")
    assert n > 0

    def run(a_type, **p):
        return run_assertion_item(item(a_type, NODES, **p), "live")

    assert run("assert_num_results", num=n).status == "pass"
    assert run("assert_num_results", num=n + 1).status == "fail"
    assert run("batq_min_results", num=n).status == "pass"
    assert run("batq_min_results", num=n + 1).status == "fail"
    assert run("assert_zero_results").status == "fail"


def test_zero_results_agrees_with_batfish(bf_state):
    bf = bf_state["bf_session"]
    for fun in ("undefinedReferences", "detectLoops", "unusedStructures"):
        expected = rows(bf, fun) == 0
        result = run_assertion_item(item("assert_zero_results", {"fun": fun}), "live")
        assert result.status == verdict(expected), (fun, result.message)


def test_question_options_are_used(bf_state):
    question = {"fun": "nodeProperties", "options": {"nodes": "as1border1,as1border2"}}
    assert (
        run_assertion_item(item("assert_num_results", question, num=2), "live").status
        == "pass"
    )
    assert (
        run_assertion_item(item("assert_num_results", question, num=13), "live").status
        == "fail"
    )


def test_a_failing_assertion_keeps_the_rows_it_looked_at(bf_state):
    result = run_assertion_item(item("assert_zero_results", NODES), "live")
    assert result.status == "fail" and result.fun == "nodeProperties"
    assert "as1border1" in set(result.answer.frame()["Node"])
    assert result.snapshot == "live"


def test_a_question_that_cannot_be_run_is_an_error(bf_state):
    # pybatfish rejects an unknown parameter or question before any request
    bad_option = {"fun": "nodeProperties", "options": {"bogusParam": 1}}
    unknown = {"fun": "noSuchQuestion"}
    for question in (bad_option, unknown):
        result = run_assertion_item(item("assert_zero_results", question), "live")
        assert result.status == "error", result.message
        assert "failed" in result.message


# -------------------------------------------------------------------- routes
def test_route_assertions_use_real_routes(bf_state):
    bf = bf_state["bf_session"]
    frame = answer_frame(bf, "routes", "live", nodes="as1border1", vrfs="default")
    assert len(frame) > 0, "the example network should have routes on as1border1"
    row = frame.iloc[0]
    present = {"Network": row["Network"], "Protocol": row["Protocol"]}
    absent = {"Network": "203.0.113.0/24"}  # TEST-NET-3, never in the example

    def run(a_type, route, **p):
        entry = item(a_type, node="as1border1", expected_route=route, **p)
        return run_assertion_item(entry, "live")

    assert run("assert_has_route", present).status == "pass"
    assert run("assert_has_route", present, vrf="default").status == "pass"
    assert run("assert_has_route", absent).status == "fail"
    assert run("assert_has_no_route", absent).status == "pass"
    assert run("assert_has_no_route", present).status == "fail"


def test_route_assertions_on_a_missing_node_or_vrf_are_never_a_pass(bf_state):
    route = {"Network": "203.0.113.0/24"}
    nowhere = item("assert_has_no_route", node="no_such_device", expected_route=route)
    assert run_assertion_item(nowhere, "live").status == "error"
    no_vrf = item(
        "assert_has_no_route", node="as1border1", vrf="nope", expected_route=route
    )
    assert run_assertion_item(no_vrf, "live").status == "error"
    missing = item("assert_has_route", node="no_such_device", expected_route=route)
    assert run_assertion_item(missing, "live").status in ("fail", "error")
