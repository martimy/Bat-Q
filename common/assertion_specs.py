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

# Registry of the assertions Bat-Q offers.
#
# The registry drives the Assertions page (forms are generated from it, as the
# Questions page is generated from bfqs.py), the YAML validation, and the runner.
# It deliberately has no Streamlit dependency so it can be unit tested.
#
# Spec fields
# -----------
# label        Human-readable name.
# description  One-line explanation shown in the UI.
# group        UI grouping.
# phase        Release phase the assertion is planned for (1 or 2).
# source       "pybatfish" (call the pybatfish function) or "batq" (implemented
#              in common/assertions.py).
# call         "session": called through Session.asserts and given a snapshot.
#              "answer":  called with the answer of a question.
# answer_from  Only for call == "answer".
#                "question": the user picks a question (fun + options).
#                "routes":   Bat-Q runs the routes question itself.
# answer_param Name of the function argument that receives the answer/routes.
# params       User-supplied parameters, in the same shape generate_input_fields
#              expects: {"name", "type", "optional"}. "optional" defaults to
#              True. soft, snapshot, session and df_format are never exposed.

SESSION = "session"
ANSWER = "answer"

FROM_QUESTION = "question"
FROM_ROUTES = "routes"

SCOPES = ("active", "alternate", "both", "failed")
DEFAULT_SCOPE = "active"

# Arguments handled by the runner, never entered by the user.
HIDDEN_PARAMS = ("soft", "snapshot", "session", "df_format")


def _nodes(name="nodes"):
    return {"name": name, "type": "NodeSpec", "optional": True}


ASSERTION_SPECS = {
    # ---- Snapshot checks (no required parameters) -----------------------
    "assert_no_undefined_references": {
        "label": "No undefined references",
        "description": "No configuration refers to a structure (ACL, route-map, ...) that is not defined.",
        "group": "Snapshot checks",
        "phase": 1,
        "source": "pybatfish",
        "call": SESSION,
        "params": [],
    },
    "assert_no_forwarding_loops": {
        "label": "No forwarding loops",
        "description": "No forwarding loops exist in the snapshot.",
        "group": "Snapshot checks",
        "phase": 1,
        "source": "pybatfish",
        "call": SESSION,
        "params": [],
    },
    "assert_no_unestablished_bgp_sessions": {
        "label": "No unestablished BGP sessions",
        "description": "All configured BGP sessions are established.",
        "group": "Snapshot checks",
        "phase": 1,
        "source": "pybatfish",
        "call": SESSION,
        "params": [_nodes("nodes"), _nodes("remote_nodes")],
    },
    "assert_no_incompatible_bgp_sessions": {
        "label": "No incompatible BGP sessions",
        "description": "No BGP sessions have incompatible settings.",
        "group": "Snapshot checks",
        "phase": 1,
        "source": "pybatfish",
        "call": SESSION,
        "params": [
            _nodes("nodes"),
            _nodes("remote_nodes"),
            {"name": "status", "type": "str", "optional": True},
        ],
    },
    "assert_no_incompatible_ospf_sessions": {
        "label": "No incompatible OSPF sessions",
        "description": "No OSPF sessions have incompatible settings.",
        "group": "Snapshot checks",
        "phase": 1,
        "source": "pybatfish",
        "call": SESSION,
        "params": [_nodes("nodes"), _nodes("remote_nodes")],
    },
    "assert_no_duplicate_router_ids": {
        "label": "No duplicate router IDs",
        "description": "No two routers share a router ID for the checked protocols.",
        "group": "Snapshot checks",
        "phase": 1,
        "source": "pybatfish",
        "call": SESSION,
        "params": [
            _nodes("nodes"),
            {"name": "protocols", "type": "list", "optional": True},
            {"name": "ignore_same_node", "type": "bool", "optional": True},
        ],
    },
    # ---- Filters --------------------------------------------------------
    "assert_filter_has_no_unreachable_lines": {
        "label": "Filter has no unreachable lines",
        "description": "No line in the selected filters is shadowed by earlier lines.",
        "group": "Filters",
        "phase": 1,
        "source": "pybatfish",
        "call": SESSION,
        "params": [{"name": "filters", "type": "FilterSpec", "optional": False}],
    },
    "assert_filter_permits": {
        "label": "Filter permits flows",
        "description": "The selected filters permit the described flows.",
        "group": "Filters",
        "phase": 2,
        "source": "pybatfish",
        "call": SESSION,
        "params": [
            {"name": "filters", "type": "FilterSpec", "optional": False},
            {"name": "headers", "type": "HeaderConstraints", "optional": False},
            {"name": "startLocation", "type": "LocationSpec", "optional": True},
        ],
    },
    "assert_filter_denies": {
        "label": "Filter denies flows",
        "description": "The selected filters deny the described flows.",
        "group": "Filters",
        "phase": 2,
        "source": "pybatfish",
        "call": SESSION,
        "params": [
            {"name": "filters", "type": "FilterSpec", "optional": False},
            {"name": "headers", "type": "HeaderConstraints", "optional": False},
            {"name": "startLocation", "type": "LocationSpec", "optional": True},
        ],
    },
    # ---- Reachability ---------------------------------------------------
    "assert_flows_succeed": {
        "label": "Flows succeed",
        "description": "The described flows are delivered.",
        "group": "Reachability",
        "phase": 2,
        "source": "pybatfish",
        "call": SESSION,
        "params": [
            {"name": "startLocation", "type": "LocationSpec", "optional": False},
            {"name": "headers", "type": "HeaderConstraints", "optional": False},
        ],
    },
    "assert_flows_fail": {
        "label": "Flows fail",
        "description": "The described flows are not delivered.",
        "group": "Reachability",
        "phase": 2,
        "source": "pybatfish",
        "call": SESSION,
        "params": [
            {"name": "startLocation", "type": "LocationSpec", "optional": False},
            {"name": "headers", "type": "HeaderConstraints", "optional": False},
        ],
    },
    # ---- Results of a question -----------------------------------------
    "assert_zero_results": {
        "label": "Question returns no rows",
        "description": "The selected question returns an empty answer.",
        "group": "Question results",
        "phase": 1,
        "source": "pybatfish",
        "call": ANSWER,
        "answer_from": FROM_QUESTION,
        "answer_param": "answer",
        "params": [],
    },
    "assert_num_results": {
        "label": "Question returns exactly N rows",
        "description": "The selected question returns exactly N rows.",
        "group": "Question results",
        "phase": 1,
        "source": "pybatfish",
        "call": ANSWER,
        "answer_from": FROM_QUESTION,
        "answer_param": "answer",
        "params": [{"name": "num", "type": "int", "optional": False}],
    },
    "batq_min_results": {
        "label": "Question returns at least N rows",
        "description": "The selected question returns at least N rows (N defaults to 1).",
        "group": "Question results",
        "phase": 1,
        "source": "batq",
        "call": ANSWER,
        "answer_from": FROM_QUESTION,
        "answer_param": "answer",
        "params": [{"name": "num", "type": "int", "optional": True}],
    },
    # ---- Routing --------------------------------------------------------
    "assert_has_route": {
        "label": "Route is present",
        "description": "A route matching the description is in the node's RIB.",
        "group": "Routing",
        "phase": 2,
        "source": "pybatfish",
        "call": ANSWER,
        "answer_from": FROM_ROUTES,
        "answer_param": "routes",
        "params": [
            {"name": "expected_route", "type": "RouteMatch", "optional": False},
            {"name": "node", "type": "str", "optional": False},
            {"name": "vrf", "type": "str", "optional": True},
        ],
    },
    "assert_has_no_route": {
        "label": "Route is absent",
        "description": "No route matching the description is in the node's RIB.",
        "group": "Routing",
        "phase": 2,
        "source": "pybatfish",
        "call": ANSWER,
        "answer_from": FROM_ROUTES,
        "answer_param": "routes",
        "params": [
            {"name": "expected_route", "type": "RouteMatch", "optional": False},
            {"name": "node", "type": "str", "optional": False},
            {"name": "vrf", "type": "str", "optional": True},
        ],
    },
}


def get_spec(assertion_type):
    """Returns the spec for an assertion type, or None if unknown."""
    return ASSERTION_SPECS.get(assertion_type)


def needs_question(spec):
    """True if the assertion needs the user to pick a question."""
    return spec.get("answer_from") == FROM_QUESTION


def specs_by_group(max_phase=None):
    """Returns {group: [assertion_type, ...]} in registry order."""
    groups = {}
    for name, spec in ASSERTION_SPECS.items():
        if max_phase is not None and spec["phase"] > max_phase:
            continue
        groups.setdefault(spec["group"], []).append(name)
    return groups
