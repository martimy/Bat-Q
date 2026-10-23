"""
Tests for the assertion report (HTML and Excel) and its page.
Run from the repository root:  python -m pytest tests
"""

import io
import os
import sys
from types import SimpleNamespace

import pandas as pd
import pytest

pytest.importorskip("streamlit")
pytest.importorskip("plotly")
pytest.importorskip("networkx")
openpyxl = pytest.importorskip("openpyxl")
pytest.importorskip("xlsxwriter")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from streamlit.testing.v1 import AppTest  # noqa: E402

from common import assertion_report as R  # noqa: E402
from common.assertions import (  # noqa: E402
    AssertionResult,
    drop_snapshot_results,
    rename_snapshot_results,
)

PAGE = os.path.join(ROOT, "views", "assertion_reporting.py")
SNAP = "snap1"


def item(aid, a_type="assert_no_forwarding_loops", name="", **extra):
    base = {
        "id": aid,
        "type": a_type,
        "name": name,
        "description": "",
        "scope": "active",
        "params": {},
    }
    base.update(extra)
    return base


def res(status, message="", answer=None, fun=None, snapshot=SNAP):
    return AssertionResult(
        status,
        message,
        runtime=0.25,
        snapshot=snapshot,
        ran_at="2026-10-23 10:00:00",
        fun=fun,
        answer=answer,
    )


def build(entries, snapshot=SNAP):
    """entries: [(assertion dict, AssertionResult | None)] -> report rows."""
    alist = [a for a, _ in entries]
    results = {f"{a['id']}@{snapshot}": r for a, r in entries if r is not None}
    return R.collect_report_rows(alist, results, snapshot)


def mixed_rows():
    return build(
        [
            (item("a1", name="Loop check"), res("pass")),
            (
                item(
                    "a2",
                    "assert_zero_results",
                    name="No unused structures",
                    question={"fun": "unusedStructures", "options": {}},
                ),
                res(
                    "fail",
                    "Found 2 results, expected none",
                    answer=pd.DataFrame(
                        {"Node": ["r1", "r2"], "Name": ["acl1", "acl2"]}
                    ),
                    fun="unusedStructures",
                ),
            ),
            (
                item("a3", "assert_no_undefined_references"),
                res("error", "RuntimeError: boom"),
            ),
            (item("a4", "assert_no_incompatible_ospf_sessions"), None),
        ]
    )


# ----------------------------------------------------------------- summary
@pytest.mark.parametrize(
    "statuses, verdict",
    [
        ([], R.VERDICT_EMPTY),
        (["pass", "pass"], R.VERDICT_PASSED),
        (["pass", "fail"], R.VERDICT_FAILED),
        (["pass", "error"], R.VERDICT_INCONCLUSIVE),
        (["pass", None], R.VERDICT_INCONCLUSIVE),
        (["error", "fail"], R.VERDICT_FAILED),
    ],
)
def test_verdict(statuses, verdict):
    rows = [{"status": s} for s in statuses]
    counts, got = R.summarize(rows)
    assert got == verdict
    assert counts["total"] == len(statuses)


def test_counts():
    counts, verdict = R.summarize(mixed_rows())
    assert counts == {"total": 4, "passed": 1, "failed": 1, "errors": 1, "not_run": 1}
    assert verdict == R.VERDICT_FAILED


def test_collect_rows_joins_results_for_the_given_snapshot_only():
    a = item("a1")
    results = {"a1@snap1": res("pass"), "a1@other": res("fail", snapshot="other")}
    assert R.collect_report_rows([a], results, "snap1")[0]["status"] == "pass"
    assert R.collect_report_rows([a], results, "other")[0]["status"] == "fail"
    assert R.collect_report_rows([a], results, "third")[0]["status"] is None


def test_collect_rows_names_and_limits():
    rows = build(
        [
            (item("a1"), res("fail", "x" * 20000)),
            (item("a2", "assert_not_in_registry"), None),
            (item("a3", name="Mine"), None),
        ]
    )
    assert rows[0]["name"] == "No forwarding loops"  # registry label
    assert len(rows[0]["message"]) == R.MAX_MESSAGE_CHARS
    assert rows[1]["name"] == "assert_not_in_registry"  # unknown type survives
    assert rows[2]["name"] == "Mine"
    assert [r["n"] for r in rows] == [1, 2, 3]


# -------------------------------------------------------------------- HTML
def test_html_structure():
    page = R.build_assertion_report_html(mixed_rows(), SNAP, "2026-10-23 10:00")
    assert "Bat-Q Assertion Report" in page and "snap1" in page
    assert f'bq-verdict fail">{R.VERDICT_FAILED}' in page
    for label in ("Passed", "Failed", "Errors", "Not run"):
        assert label in page
    # every assertion is in the summary, in order
    order = [page.index(n) for n in ("Loop check", "No unused structures")]
    assert order == sorted(order)
    assert "No undefined references" in page and "No incompatible OSPF sessions" in page
    # details exist for the failure and the error, not for the pass
    details = page[page.index("<h2>Details</h2>") :]
    assert "No unused structures" in details and "No undefined references" in details
    assert "Loop check" not in details
    assert "Found 2 results, expected none" in details
    assert "acl1" in details and "acl2" in details  # the offending rows
    assert "could not be evaluated" in details  # error explained


def test_html_verdicts_and_empty_report():
    passed = build([(item("a1"), res("pass"))])
    page = R.build_assertion_report_html(passed, SNAP, "now")
    assert f'bq-verdict pass">{R.VERDICT_PASSED}' in page
    assert "<h2>Details</h2>" not in page
    inconclusive = build([(item("a1"), res("pass")), (item("a2"), None)])
    page = R.build_assertion_report_html(inconclusive, SNAP, "now")
    assert R.VERDICT_INCONCLUSIVE in page
    page = R.build_assertion_report_html([], SNAP, "now")
    assert R.VERDICT_EMPTY in page and "No assertions defined" in page


def test_html_escapes_user_text():
    evil = "<script>alert(1)</script>"
    rows = build(
        [
            (
                item(
                    "a1", name=evil, description="a & b <i>", params={"filters": evil}
                ),
                res("fail", f"msg {evil}", answer=pd.DataFrame({"c": [evil]}), fun="x"),
            )
        ]
    )
    page = R.build_assertion_report_html(rows, evil, evil)
    assert "<script>alert(1)</script>" not in page
    assert page.count("&lt;script&gt;alert(1)&lt;/script&gt;") >= 4
    assert "a &amp; b &lt;i&gt;" in page


def test_html_caps_failing_rows_and_notes_empty_answers():
    big = pd.DataFrame({"n": range(R.MAX_ROWS_HTML + 50)})
    rows = build(
        [
            (item("a1"), res("fail", "m", answer=big, fun="q")),
            (item("a2"), res("fail", "m", answer=pd.DataFrame(), fun="q2")),
        ]
    )
    page = R.build_assertion_report_html(rows, SNAP, "now")
    assert f"Showing the first {R.MAX_ROWS_HTML} of {R.MAX_ROWS_HTML + 50} rows" in page
    assert f"<td>{R.MAX_ROWS_HTML + 10}</td>" not in page  # row beyond the cap
    assert "The answer has no rows." in page


def test_html_failure_with_a_batfish_style_answer_has_no_plot():
    """Question answers are shown as tables; no topology plot or CDN script."""
    frame = pd.DataFrame(
        {
            "Node": ["r1"],
            "Remote_Node": ["r2"],
            "Interface": ["i1"],
            "Remote_Interface": ["i2"],
        }
    )
    answer = SimpleNamespace(frame=lambda: frame, rows=[])
    rows = build([(item("a1"), res("fail", "m", answer=answer, fun="bgpEdges"))])
    page = R.build_assertion_report_html(rows, SNAP, "now")
    assert "r1" in page and "plotly" not in page.lower()


# -------------------------------------------------------------------- XLSX
def load(xlsx_bytes):
    return openpyxl.load_workbook(io.BytesIO(xlsx_bytes))


def test_xlsx_none_without_assertions():
    assert R.build_assertion_report_xlsx([], SNAP, "now") is None


def test_xlsx_summary_and_failure_sheets():
    wb = load(R.build_assertion_report_xlsx(mixed_rows(), SNAP, "2026-10-23 10:00"))
    assert wb.sheetnames == ["Summary", "2 No unused structures"]
    ws = wb["Summary"]
    cells = {ws.cell(r, 1).value: ws.cell(r, 2).value for r in range(1, 7)}
    assert cells["Snapshot"] == SNAP and cells["Verdict"] == R.VERDICT_FAILED
    assert "1 passed, 1 failed, 1 errors, 1 not run" == cells["Counts"]
    header_row = next(r for r in range(1, 12) if ws.cell(r, 1).value == "#")
    table = [
        [ws.cell(r, c).value for c in range(1, 9)]
        for r in range(header_row + 1, header_row + 5)
    ]
    assert [t[1] for t in table] == ["Passed", "Failed", "Error", "Not run"]
    assert table[1][2] == "No unused structures"
    assert table[1][5] == "Found 2 results, expected none"
    assert table[3][6] is None  # not run: no runtime
    fail_ws = wb["2 No unused structures"]
    values = [[c.value for c in row] for row in fail_ws.iter_rows()]
    assert values[2] == ["Node", "Name"] and values[3] == ["r1", "acl1"]


def test_xlsx_sheet_names_are_valid_and_unique():
    answer = pd.DataFrame({"a": [1]})
    rows = build(
        [
            (
                item("a1", name="Bad/name: with [chars]? and a very long title indeed"),
                res("fail", "m", answer=answer, fun="q"),
            ),
            (
                item("a2", name="Bad/name: with [chars]? and a very long title indeed"),
                res("fail", "m", answer=answer, fun="q"),
            ),
        ]
    )
    names = load(R.build_assertion_report_xlsx(rows, SNAP, "now")).sheetnames
    assert len(names) == 3 and len(set(names)) == 3
    assert all(len(n) <= 31 and not set(n) & set("[]:*?/\\") for n in names)


def test_xlsx_handles_non_scalar_cells_and_limits():
    frame = pd.DataFrame(
        {
            "List": [["a", "b"]],
            "Dict": [{"k": 1}],
            "When": [pd.Timestamp("2026-01-01 10:00:00", tz="UTC")],
            "Num": [1.5],
        }
    )
    rows = build(
        [
            (item("a1"), res("fail", "x" * 20000, answer=frame, fun="q")),
            (item("a2"), res("pass", answer=frame, fun="q")),  # passes get no sheet
            (item("a3"), res("error", "boom")),  # nor do errors
            (item("a4"), res("fail", "no answer kept")),  # nor failures without rows
        ]
    )
    wb = load(R.build_assertion_report_xlsx(rows, SNAP, "now"))
    assert len(wb.sheetnames) == 2
    ws = wb[wb.sheetnames[1]]
    values = [c.value for c in list(ws.iter_rows())[3]]
    assert values[0] == "['a', 'b']" and values[1] == "{'k': 1}" and values[3] == 1.5
    assert len(wb["Summary"].cell(8, 6).value or "") <= R.MAX_MESSAGE_CHARS


# ------------------------------------------------------- stale-result helpers
def test_drop_and_rename_snapshot_results():
    results = {
        "a1@s1": res("pass", snapshot="s1"),
        "a1@s2": res("fail", snapshot="s2"),
        "a2@s1@x": res("pass", snapshot="s1@x"),  # '@' inside a snapshot name
    }
    assert set(drop_snapshot_results(results, "s1")) == {"a1@s2", "a2@s1@x"}
    assert (
        set(drop_snapshot_results(results, "x"))
        == {"a1@s1", "a1@s2", "a2@s1@x"} - {"a2@s1@x"} | set()
    )
    renamed = rename_snapshot_results(dict(results), "s2", "s3")
    assert set(renamed) == {"a1@s1", "a1@s3", "a2@s1@x"}
    assert renamed["a1@s3"].snapshot == "s3"


# --------------------------------------------------------------------- page
def page_app(alist=None, results=None, snapshot=SNAP):
    at = AppTest.from_file(PAGE, default_timeout=30)
    if snapshot:
        at.session_state["activesnap"] = {"name": snapshot}
    if alist is not None:
        at.session_state["alist"] = alist
    if results is not None:
        at.session_state["assertion_results"] = results
    at.run()
    assert not at.exception
    return at


def test_page_needs_snapshot_assertions_and_results():
    assert any("snapshot" in w.value for w in page_app(snapshot=None).warning)
    assert any("Add some assertions" in w.value for w in page_app().warning)
    at = page_app(alist=[item("a1")], results={})
    assert any("Run the assertions" in w.value for w in at.warning)
    assert at.get("download_button") == []


def test_page_offers_both_downloads_once_something_was_run():
    at = page_app(
        alist=[item("a1"), item("a2")],
        results={f"a1@{SNAP}": res("pass")},  # a2 not run: still reported
    )
    buttons = at.get("download_button")
    assert [b.proto.label for b in buttons] == [
        "Download HTML Report",
        "Download Spreadsheet (.xlsx)",
    ]
    assert not any(b.proto.disabled for b in buttons)


def test_report_ignores_results_of_other_snapshots():
    at = page_app(
        alist=[item("a1")],
        results={"a1@other": res("pass", snapshot="other")},
    )
    assert any("Run the assertions" in w.value for w in at.warning)
