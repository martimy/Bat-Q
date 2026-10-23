"""Tests for the analysis report HTML builders in common/htmlreport.py."""

import pandas as pd

from common import htmlreport as H
from common.presenter import NO_DATA
from fakes import FakeAnswer, trace

DF = pd.DataFrame({"Node": ["r1", "r2"], "Empty": [None, None], "Val": ["a", None]})


# ---------------------------------------------------------- small helpers
def test_df_to_html_has_no_index_and_blank_missing_cells():
    out = H._df_to_html(pd.DataFrame({"a": ["x", None]}))
    assert "bq-table" in out and "bq-table-wrap" in out
    assert "<th>a</th>" in out and "None" not in out and "NaN" not in out


def test_table_block_shows_the_table_and_the_removed_columns():
    out = H._table_block(pd.DataFrame({"a": [1]}), {"z", "b"})
    assert "<td>1</td>" in out
    assert "Empty columns removed:</strong> b, z" in out  # sorted


def test_table_block_without_removed_columns_has_no_note():
    assert "removed" not in H._table_block(pd.DataFrame({"a": [1]}), set())


def test_table_block_of_an_empty_frame_is_a_warning():
    out = H._table_block(pd.DataFrame(), set())
    assert "bq-warning" in out and "No data available!" in out and "<table" not in out


# ------------------------------------------------------ render_result_html
def test_empty_answer_is_reported():
    out = H.render_result_html("nodeProperties", FakeAnswer(empty=True))
    assert "The answer set is empty." in out


def test_table_answer_drops_empty_columns_and_says_so():
    out = H.render_result_html("nodeProperties", FakeAnswer(DF))
    assert "<th>Node</th>" in out and "<th>Val</th>" in out
    assert "<th>Empty</th>" not in out
    assert "Empty columns removed:</strong> Empty" in out


def test_answer_with_no_rows_is_reported_as_no_data():
    out = H.render_result_html("nodeProperties", FakeAnswer(pd.DataFrame()))
    assert "No data available!" in out


def test_errors_are_shown_and_escaped():
    out = H.render_result_html("nodeProperties", FakeAnswer(RuntimeError("<b>bad</b>")))
    assert (
        "bq-error" in out
        and "&lt;b&gt;bad&lt;/b&gt;" in out
        and "<b>bad</b>" not in out
    )


def test_traceroute_shows_status_and_each_trace():
    answer = FakeAnswer(
        rows=[{"Traces": [trace("ACCEPTED"), trace("DENIED_IN", node="r9")]}],
        extra={"status": "OK"},
    )
    out = H.render_result_html("traceroute", answer)
    assert "Trace status:</strong> OK" in out
    assert "Trace 1 — Disposition:</strong> ACCEPTED" in out
    assert "Trace 2 — Disposition:</strong> DENIED_IN" in out
    assert "<td>r9</td>" in out


def test_single_trace_is_not_numbered():
    answer = FakeAnswer(rows=[{"Traces": [trace()]}], extra={"status": "OK"})
    out = H.render_result_html("reachability", answer)
    assert "Trace — Disposition:" in out and "Trace 1" not in out


def test_bidirectional_traceroute_shows_both_directions():
    answer = FakeAnswer(
        rows=[
            {
                "Forward_Flow": {"src": "1.1.1.1"},
                "Reverse_Flow": {"src": "2.2.2.2"},
                "Forward_Traces": [trace("ACCEPTED")],
                "Reverse_Traces": [trace("NO_ROUTE")],
            }
        ],
        extra={"status": "OK"},
    )
    out = H.render_result_html("bidirectionalTraceroute", answer)
    assert "Forward Flow:</strong> src = 1.1.1.1" in out
    assert "Reverse Flow:</strong> src = 2.2.2.2" in out
    assert "ACCEPTED" in out and "NO_ROUTE" in out


def test_test_filters_rows_are_flattened():
    answer = FakeAnswer(
        rows=[
            {
                "Node": "n1",
                "Filter_Name": "acl",
                "Flow": "f",
                "Action": "PERMIT",
                "Line_Content": "permit ip any any",
                "Trace": [{"traceElement": {"fragments": [{"text": "hit"}]}}],
            }
        ]
    )
    out = H.render_result_html("testFilters", answer)
    assert "<th>Trace_Text</th>" in out and "<td>hit</td>" in out


def test_bgp_edges_add_a_topology_plot():
    answer = FakeAnswer(pd.DataFrame({"Node": ["a"], "Remote_Node": ["b"]}))
    out = H.render_result_html("bgpEdges", answer)
    assert "plotly" in out.lower() and "<th>Remote_Node</th>" in out


def test_other_questions_have_no_plot():
    assert (
        "plotly" not in H.render_result_html("nodeProperties", FakeAnswer(DF)).lower()
    )


# --------------------------------------------------------- build_report_html
def section(name, options=None, html="<p>x</p>"):
    return {"name": name, "options": options, "html": html}


def test_report_has_title_snapshot_and_sections_in_order():
    page = H.build_report_html(
        [section("First", html="<p>one</p>"), section("Second", html="<p>two</p>")],
        "snap1",
        "2026-10-23 10:00",
    )
    assert page.startswith("<!DOCTYPE html>")
    assert "Bat-Q Network Analysis Report" in page
    assert "<strong>snap1</strong>" in page and "2026-10-23 10:00" in page
    assert page.index("<h2>First</h2>") < page.index("<h2>Second</h2>")
    assert "<p>one</p>" in page  # section bodies are inserted as given


def test_report_shows_question_options():
    page = H.build_report_html([section("A", {"nodes": "r1", "x": 2})], "s", "now")
    assert "Options:</strong> nodes = r1, x = 2" in page


def test_report_drops_repeated_name_and_option_combinations():
    sections = [
        section("A", {"n": "x"}, "<p>first</p>"),
        section("A", {"n": "x"}, "<p>duplicate</p>"),
        section("A", {"n": "y"}, "<p>other options</p>"),
        section("B", None, "<p>b</p>"),
    ]
    page = H.build_report_html(sections, "s", "now")
    assert page.count("<section") == 3
    assert "duplicate" not in page and "other options" in page


def test_report_escapes_names_and_snapshot():
    page = H.build_report_html([section("A<b>")], "snap<1>", "now&then")
    assert "A&lt;b&gt;" in page and "snap&lt;1&gt;" in page and "now&amp;then" in page
    assert "<h2>A<b></h2>" not in page


def test_report_without_sections_is_still_a_page():
    page = H.build_report_html([], "s", "now")
    assert "<body>" in page and "<section" not in page


def test_no_data_text_is_the_shared_constant():
    assert H.NO_DATA == NO_DATA


# ----------------------------------------- questions with their own handling
def test_select_questions_show_empty_cells_as_blank_text():
    df = pd.DataFrame(
        {"File": ["a", "b"], "Status": ["PASSED", None], "Gone": [None, None]}
    )
    out = H.render_result_html("fileParseStatus", FakeAnswer(df))
    assert "<th>Status</th>" in out and "<th>Gone</th>" not in out
    assert "Empty columns removed:</strong> Gone" in out
    assert "None" not in out and "nan" not in out.lower().replace("nanosecond", "")


def test_layer3_edges_add_a_topology_plot():
    edges = pd.DataFrame(
        {
            "Interface": [{"hostname": "r1", "interface": "Gi0"}],
            "Remote_Interface": [{"hostname": "r2", "interface": "Gi0"}],
        }
    )
    out = H.render_result_html("layer3Edges", FakeAnswer(edges))
    assert "plotly" in out.lower() and "r1" in out
