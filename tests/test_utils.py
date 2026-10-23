"""Tests for common/utils.py (naming helpers, template conversion, defaults)."""

import pytest

from common import utils as U
from common.bfqs import read_questions

ITEMS = ["How", "Why", "Why_3", "Why_12", "What"]


# ------------------------------------------------------------ naming helpers
def test_get_same_prefix_returns_prefix_and_matches():
    assert U.get_same_prefix("Why", ITEMS) == ("Why", ["Why", "Why_3", "Why_12"])
    # a numbered name maps to the same base name
    assert U.get_same_prefix("Why_3", ITEMS)[0] == "Why"


def test_get_same_prefix_keeps_spaces_in_names():
    prefix, matches = U.get_same_prefix(
        "Node Properties", ["Node Properties", "Node Roles", "Nodes_1"]
    )
    assert prefix == "Node Properties"
    assert matches == ["Node Properties"]


def test_get_highest_number_is_numeric_not_alphabetical():
    assert U.get_highest_number("Why", ITEMS) == "Why_12"  # not "Why_3"


def test_get_highest_number_without_numbered_items():
    assert U.get_highest_number("How", ITEMS) is None
    assert U.get_highest_number("Missing", ITEMS) is None


@pytest.mark.parametrize(
    "item, expected",
    [
        ("How", "How_1"),  # exists, never numbered
        ("Why", "Why_13"),  # continues after the highest
        ("Why_3", "Why_13"),  # same, starting from a numbered name
        ("New", "New_1"),  # not in the list at all
    ],
)
def test_get_next_item(item, expected):
    assert U.get_next_item(item, ITEMS) == expected


def test_get_next_item_never_reuses_a_name():
    items = ["Q"]
    for _ in range(5):
        new = U.get_next_item("Q", items)
        assert new not in items
        items.append(new)
    assert items == ["Q", "Q_1", "Q_2", "Q_3", "Q_4", "Q_5"]


@pytest.mark.xfail(
    strict=True,
    reason="Latent bug: the base name is taken before the first '_', so a "
    "name containing '_' gets an existing name back. Not reachable today "
    "because no question name contains '_' (see test_bfqs.py).",
)
def test_get_next_item_with_underscore_in_name_is_unique():
    items = ["A_b", "A_b_1"]
    assert U.get_next_item("A_b", items) not in items


@pytest.mark.xfail(
    strict=True,
    reason="Latent bug: a non-numeric suffix after a matching prefix raises "
    "ValueError instead of being ignored.",
)
def test_get_highest_number_ignores_non_numeric_suffix():
    assert U.get_highest_number("Why", ["Why_3x"]) is None


# --------------------------------------------------------- sort_qlist_by_schema
SCHEMA = [
    {"questions": [{"name": "B"}, {"name": "A"}]},
    {"questions": [{"name": "C"}, {"name": "A"}, {"noname": 1}]},
]


def test_sort_follows_schema_order_with_unknown_last():
    qlist = {"C": 1, "Z": 2, "A": 3, "B": 4}
    assert list(U.sort_qlist_by_schema(qlist, SCHEMA)) == ["B", "A", "C", "Z"]


def test_sort_keeps_values_and_original_order_of_unknown_names():
    out = U.sort_qlist_by_schema({"Y": 1, "X": 2, "B": 3}, SCHEMA)
    assert out == {"B": 3, "Y": 1, "X": 2}
    assert list(out) == ["B", "Y", "X"]


@pytest.mark.parametrize("qlist", [{}, None])
def test_sort_of_nothing_is_empty(qlist):
    assert U.sort_qlist_by_schema(qlist, SCHEMA) == {}


def test_sort_uses_the_real_schema_by_default():
    names = [q["name"] for c in read_questions()["Batfish"] for q in c["questions"]]
    qlist = {names[5]: 1, names[0]: 2, "Not a question": 3}
    assert list(U.sort_qlist_by_schema(qlist)) == [names[0], names[5], "Not a question"]


# ------------------------------------------------------------ convert_template
def test_convert_template_follows_schema_order_and_numbers_variants():
    template = {
        "BGP Edges": {
            "fun": "bgpEdges",
            "variants": [{"nodes": "a"}, {"nodes": "b"}, {"nodes": "c"}],
        },
        "Node Properties": {"fun": "nodeProperties"},
    }
    out = U.convert_template(template)
    assert [q["name"] for q in out] == [
        "Node Properties",
        "BGP Edges",
        "BGP Edges_1",
        "BGP Edges_2",
    ]
    assert out[0] == {"name": "Node Properties", "fun": "nodeProperties"}
    assert [q.get("options") for q in out[1:]] == [
        {"nodes": "a"},
        {"nodes": "b"},
        {"nodes": "c"},
    ]
    assert {q["fun"] for q in out[1:]} == {"bgpEdges"}


def test_convert_template_edge_cases():
    out = U.convert_template({"Mine": {"fun": "x", "variants": []}, "NoFun": {}})
    assert out == [{"name": "Mine", "fun": "x"}, {"name": "NoFun", "fun": ""}]


# ----------------------------------------------------------- init_session_state
def test_init_session_state_sets_defaults(bf_session_state):
    U.init_session_state()
    assert bf_session_state["bf_session"] is None
    assert bf_session_state["network_name"] == "NETWORK"
    for key in ("qlist", "activesnap", "altsnap", "assertion_results"):
        assert bf_session_state[key] == {}
    for key in ("alist", "report_analysis_data", "cats_expander"):
        assert bf_session_state[key] == []
    assert bf_session_state["assertion_form_n"] == 0
    assert bf_session_state["assertion_editing"] is None


def test_init_session_state_keeps_existing_values_and_is_idempotent(bf_session_state):
    bf_session_state["network_name"] = "MYNET"
    bf_session_state["alist"] = [{"id": "a1"}]
    U.init_session_state()
    U.init_session_state()
    assert bf_session_state["network_name"] == "MYNET"
    assert bf_session_state["alist"] == [{"id": "a1"}]


def test_defaults_are_not_shared_between_sessions(bf_session_state):
    U.init_session_state()
    bf_session_state["alist"].append(1)
    bf_session_state.clear()
    U.init_session_state()
    assert bf_session_state["alist"] == []


def test_sort_returns_the_list_unchanged_if_the_schema_cannot_be_read(monkeypatch):
    import common.bfqs

    def broken():
        raise RuntimeError("schema unavailable")

    monkeypatch.setattr(common.bfqs, "read_questions", broken)
    qlist = {"Z": 1, "A": 2}
    assert U.sort_qlist_by_schema(qlist) is qlist
