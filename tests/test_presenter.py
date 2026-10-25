"""Tests for the pure data helpers in common/presenter.py."""

import numpy as np
import pandas as pd
import pytest

from common import presenter as P
from common.bfqs import read_questions


# ---------------------------------------------------------- _is_empty_value
@pytest.mark.parametrize(
    "value",
    [None, float("nan"), np.nan, pd.NA, pd.NaT, "", "  ", "\t\n", [], (), set(), {}],
)
def test_empty_values(value):
    assert P._is_empty_value(value) is True


@pytest.mark.parametrize("value", [0, 0.0, False, "x", " x ", [0], {"a": 1}, (None,)])
def test_non_empty_values(value):
    assert P._is_empty_value(value) is False


# ------------------------------------------------------------ format_result
def frame():
    return pd.DataFrame(
        {"a": [1, 2], "empty": ["", None], "lst": [[], []], "b": ["x", ""]}
    )


def test_format_result_drops_all_empty_columns_and_reports_them():
    out, removed = P.format_result(frame())
    assert list(out.columns) == ["a", "b"]
    assert removed == {"empty", "lst"}
    assert out["a"].tolist() == [1, 2]


def test_format_result_shows_empty_cells_as_blank_text():
    df = pd.DataFrame({"a": ["x", None], "b": [1, 2]})
    out, _ = P.format_result(df)
    assert out["a"].tolist() == ["x", ""]


def test_format_result_keeps_zero_and_false():
    out, removed = P.format_result(pd.DataFrame({"n": [0, 0], "f": [False, False]}))
    assert list(out.columns) == ["n", "f"] and removed == set()


def test_format_result_modifies_the_frame_it_is_given():
    """Documents a side effect: empty cells of the input are replaced by NaN."""
    df = frame()
    P.format_result(df)
    assert df["empty"].isna().all()


def test_format_result_with_nothing_to_show():
    out, removed = P.format_result(pd.DataFrame({"a": [None]}))
    assert out.shape == (1, 0) and removed == {"a"}
    out, removed = P.format_result(pd.DataFrame())
    assert out.shape == (0, 0) and removed == set()


# ------------------------------------------------------- format_result_lite
def test_format_result_lite_drops_all_empty_columns_without_touching_cells():
    df = pd.DataFrame({"a": [1, 2], "e": [None, ""], "c": ["x", None]})
    out, removed = P.format_result_lite(df)
    assert list(out.columns) == ["a", "c"] and removed == {"e"}
    assert out["c"].iloc[0] == "x"
    assert pd.isna(out["c"].iloc[1])  # still missing, not turned into ""


def test_format_result_lite_leaves_its_input_alone():
    df = frame()
    before = df.copy(deep=True)
    P.format_result_lite(df)
    assert df.equals(before)


def test_format_result_lite_of_an_empty_frame():
    out, removed = P.format_result_lite(pd.DataFrame())
    assert out.shape == (0, 0) and removed == set()


# --------------------------------------------------------------- dict_to_str
def test_dict_to_str():
    assert P.dict_to_str({"a": 1, "b": [1, 2]}) == "a = 1, b = [1, 2]"
    assert P.dict_to_str({"only": "one"}) == "only = one"
    assert P.dict_to_str({}) == ""
    assert P.dict_to_str(None) == ""


# --------------------------------------------------------- json_to_dataframe
def make_trace(hops):
    return {"hops": hops}


def hop(node, *steps):
    return {
        "node": {"name": node},
        "steps": [{"type": t, "action": a, "detail": d} for t, a, d in steps],
    }


def test_json_to_dataframe_flattens_hops_and_steps_in_order():
    t = make_trace(
        [
            hop("r1", ("X", "ACC", {"k": "v"}), ("Y", "FWD", {"k": "v2"})),
            hop("r2", ("Z", "DEL", {"k": "v3"})),
        ]
    )
    df = P.json_to_dataframe(t)
    assert list(df.columns) == ["Node", "Type", "Action", "Detail"]
    assert df.to_dict("list") == {
        "Node": ["r1", "r1", "r2"],
        "Type": ["X", "Y", "Z"],
        "Action": ["ACC", "FWD", "DEL"],
        "Detail": ["v", "v2", "v3"],
    }


def test_json_to_dataframe_without_hops_has_the_columns_but_no_rows():
    df = P.json_to_dataframe(make_trace([]))
    assert df.shape == (0, 4) and list(df.columns) == [
        "Node",
        "Type",
        "Action",
        "Detail",
    ]


def test_json_to_dataframe_expands_multi_key_details_into_rows():
    """Documents current behaviour: one row per key of a step's detail dict."""
    df = P.json_to_dataframe(make_trace([hop("r", ("X", "A", {"k": 1, "j": 2}))]))
    assert df["Detail"].tolist() == [1, 2] and df["Node"].tolist() == ["r", "r"]


def test_json_to_dataframe_with_scalar_detail():
    df = P.json_to_dataframe(make_trace([hop("r", ("X", "A", "scalar"))]))
    assert df["Detail"].tolist() == ["scalar"]
    assert df["Node"].tolist() == ["r"]


@pytest.mark.parametrize("detail", [None, 5, 2.5, True, "text"])
def test_json_to_dataframe_with_any_plain_detail(detail):
    df = P.json_to_dataframe(make_trace([hop("r", ("X", "A", detail))]))
    assert len(df) == 1 and df["Node"].tolist() == ["r"]


def test_json_to_dataframe_expands_list_details_into_rows():
    df = P.json_to_dataframe(make_trace([hop("r", ("X", "A", ["a", "b"]))]))
    assert df["Detail"].tolist() == ["a", "b"] and df["Node"].tolist() == ["r", "r"]


def test_json_to_dataframe_keeps_order_with_mixed_details():
    t = make_trace(
        [hop("r1", ("X", "A", {"k": "v"}), ("Y", "B", "plain"), ("Z", "C", None))]
    )
    df = P.json_to_dataframe(t)
    assert df["Type"].tolist() == ["X", "Y", "Z"]
    assert df["Detail"].tolist() == ["v", "plain", None]


# ------------------------------------------------------- flatten_trace_data
def test_flatten_trace_data_one_row_per_trace_element():
    rows = [
        {
            "Node": "n1",
            "Filter_Name": "f",
            "Flow": "fl",
            "Action": "PERMIT",
            "Line_Content": "l",
            "Trace": [
                {
                    "traceElement": {
                        "fragments": [
                            {"text": "a"},
                            {"text": "b", "vendorStructureId": {"x": 1}},
                            {"nothing": 1},
                        ]
                    }
                },
                {"traceElement": {"fragments": []}},
            ],
        }
    ]
    out = P.flatten_trace_data(rows)
    assert len(out) == 2
    assert out[0]["Trace_Text"] == "a b"
    assert out[0]["Trace_Vendor_Structure"] == {"x": 1}
    assert out[1]["Trace_Text"] == "" and out[1]["Trace_Vendor_Structure"] is None
    assert {r["Node"] for r in out} == {"n1"}
    assert out[0]["Filter_Name"] == "f"


def test_flatten_trace_data_rows_without_traces_still_appear():
    out = P.flatten_trace_data([{"Node": "n2", "Trace": []}, {"Node": "n3"}])
    assert [r["Node"] for r in out] == ["n2", "n3"]
    assert all(r["Trace_Text"] is None for r in out)


def test_flatten_trace_data_of_nothing():
    assert P.flatten_trace_data([]) == []


# ------------------------------------------------- question name constants
def test_question_lists_refer_to_real_questions():
    funs = {q["fun"] for c in read_questions()["Batfish"] for q in c["questions"]}
    assert set(P.topology_questions) <= funs
    assert set(P.select_questions) <= funs
