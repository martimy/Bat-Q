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

# Assertion report: a verification summary (verdict, counts, one line per
# assertion) followed by details for every assertion that did not pass.
# This is deliberately separate from the analysis report (htmlreport.py,
# spreadsheet.py), which is a collection of question answers.

import html
import io

import pandas as pd

from common.assertion_specs import get_spec
from common.assertions import ERROR, FAIL, PASS, result_key
from common.htmlreport import TABLE_CSS, _df_to_html
from common.spreadsheet import _safe_sheet_name, question_to_dataframe

NOT_RUN = None
STATUS_LABEL = {PASS: "Passed", FAIL: "Failed", ERROR: "Error", NOT_RUN: "Not run"}
STATUS_CLASS = {PASS: "pass", FAIL: "fail", ERROR: "error", NOT_RUN: "notrun"}

MAX_MESSAGE_CHARS = 5000  # long pybatfish messages, and Excel's 32,767-char cell limit
MAX_ROWS_HTML = 200  # failing rows shown per assertion in the HTML report
MAX_ROWS_XLSX = 50000
MAX_CHECKS_CHARS = 200

VERDICT_FAILED = "FAILED"
VERDICT_INCONCLUSIVE = "INCONCLUSIVE"
VERDICT_PASSED = "PASSED"
VERDICT_EMPTY = "NO ASSERTIONS"
VERDICT_CLASS = {
    VERDICT_FAILED: "fail",
    VERDICT_INCONCLUSIVE: "error",
    VERDICT_PASSED: "pass",
    VERDICT_EMPTY: "notrun",
}


# --------------------------------------------------------------------- data
def _checks_text(a):
    """Compact description of what the assertion checks."""
    parts = []
    if a.get("question"):
        parts.append(f"question: {a['question']['fun']}")
        options = a["question"].get("options")
        if options:
            parts.append(f"options: {options}")
    parts.extend(f"{k} = {v}" for k, v in (a.get("params") or {}).items())
    text = "; ".join(parts)
    if len(text) > MAX_CHECKS_CHARS:
        text = text[: MAX_CHECKS_CHARS - 3] + "..."
    return text


def collect_report_rows(alist, results, snapshot):
    """
    One row per assertion in `alist`, joined with its result on `snapshot`.
    Assertions that have not been run are included with status None.
    """
    rows = []
    for n, a in enumerate(alist, start=1):
        spec = get_spec(a["type"]) or {}
        r = results.get(result_key(a["id"], snapshot))
        rows.append(
            {
                "n": n,
                "name": a.get("name") or spec.get("label") or a["type"],
                "type": a["type"],
                "group": spec.get("group", ""),
                "description": a.get("description") or "",
                "checks": _checks_text(a),
                "status": r.status if r else NOT_RUN,
                "message": (r.message if r else "")[:MAX_MESSAGE_CHARS],
                "runtime": r.runtime if r else None,
                "ran_at": r.ran_at if r else "",
                "fun": r.fun if r else None,
                "answer": r.answer if r else None,
            }
        )
    return rows


def summarize(rows):
    """Counts and an overall verdict. Errors never count as a pass."""
    counts = {
        "total": len(rows),
        "passed": sum(1 for r in rows if r["status"] == PASS),
        "failed": sum(1 for r in rows if r["status"] == FAIL),
        "errors": sum(1 for r in rows if r["status"] == ERROR),
        "not_run": sum(1 for r in rows if r["status"] is NOT_RUN),
    }
    if not rows:
        verdict = VERDICT_EMPTY
    elif counts["failed"]:
        verdict = VERDICT_FAILED
    elif counts["errors"] or counts["not_run"]:
        verdict = VERDICT_INCONCLUSIVE
    else:
        verdict = VERDICT_PASSED
    return counts, verdict


def _frame_of(row):
    """The answer behind an assertion as a DataFrame (or None)."""
    answer = row["answer"]
    if answer is None:
        return None
    if isinstance(answer, pd.DataFrame):
        return answer
    return question_to_dataframe(row["fun"], answer)


# --------------------------------------------------------------------- HTML
REPORT_CSS = """
body { font-family: -apple-system, Segoe UI, Roboto, Arial, sans-serif; margin: 2rem; color: #1a1a1a; }
h1 { margin-bottom: 0.2rem; }
.bq-meta { color: #555; margin-bottom: 1.5rem; }
.bq-verdict { padding: 14px 18px; border-radius: 6px; font-size: 1.3rem; font-weight: 600; margin-bottom: 1rem; }
.bq-counts { display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 2rem; }
.bq-count { border: 1px solid #ddd; border-radius: 6px; padding: 8px 16px; min-width: 90px; }
.bq-count b { display: block; font-size: 1.5rem; }
.bq-badge { display: inline-block; padding: 2px 10px; border-radius: 10px; font-size: 0.85rem; font-weight: 600; }
.pass { background: #e6f4ea; color: #14602b; }
.fail { background: #fdecea; color: #8a1c14; }
.error { background: #fff4d6; color: #7a5b00; }
.notrun { background: #eee; color: #555; }
.bq-section { margin-bottom: 2rem; border-top: 1px solid #eee; padding-top: 1.2rem; }
.bq-section h3 { margin: 0 0 0.4rem; }
.bq-note { color: #666; font-size: 0.85rem; }
.bq-checks { font-family: ui-monospace, Menlo, Consolas, monospace; font-size: 0.85rem; color: #333; }
pre.bq-message { background: #f6f6f6; padding: 10px 12px; border-radius: 4px; overflow-x: auto; white-space: pre-wrap; font-size: 0.85rem; }
.bq-legend { margin-top: 3rem; border-top: 1px solid #eee; padding-top: 1rem; }
td.bq-wrap { white-space: normal !important; max-width: 36rem; }
@media print { .bq-section { break-inside: avoid; } }
"""

LEGEND = (
    "<strong>Passed</strong>: the assertion held. "
    "<strong>Failed</strong>: the assertion does not hold; details follow. "
    "<strong>Error</strong>: the assertion could not be evaluated (for example, "
    "a question failed or a node was not found), so it is neither passed nor failed. "
    "<strong>Not run</strong>: the assertion was defined but not run on this snapshot. "
    "Results reflect the last run of each assertion."
)


def _e(value):
    return html.escape(str(value))


def _badge(status):
    return (
        f"<span class='bq-badge {STATUS_CLASS[status]}'>{STATUS_LABEL[status]}</span>"
    )


def _answer_html(row):
    """
    The rows an assertion looked at, as a table (no plots), capped so
    reports stay readable.
    """
    if row["answer"] is None:
        return ""
    frame = _frame_of(row)
    title = f"<p><strong>Answer of</strong> <code>{_e(row['fun'])}</code>:</p>"
    if frame is None or len(frame) == 0:
        return title + "<p class='bq-note'>The answer has no rows.</p>"
    if len(frame) > MAX_ROWS_HTML:
        return (
            title
            + _df_to_html(frame.head(MAX_ROWS_HTML))
            + f"<p class='bq-note'>Showing the first {MAX_ROWS_HTML} of "
            f"{len(frame)} rows.</p>"
        )
    return title + _df_to_html(frame)


def _summary_table(rows):
    body = []
    for r in rows:
        runtime = "" if r["runtime"] is None else f"{r['runtime']:.2f}"
        body.append(
            "<tr>"
            f"<td>{r['n']}</td>"
            f"<td>{_badge(r['status'])}</td>"
            f"<td class='bq-wrap'><strong>{_e(r['name'])}</strong>"
            + (
                f"<br><span class='bq-note'>{_e(r['description'])}</span>"
                if r["description"]
                else ""
            )
            + "</td>"
            f"<td class='bq-wrap bq-checks'>{_e(r['type'])}"
            + (f"<br>{_e(r['checks'])}" if r["checks"] else "")
            + "</td>"
            f"<td>{runtime}</td>"
            f"<td>{_e(r['ran_at'])}</td>"
            "</tr>"
        )
    return (
        "<div class='bq-table-wrap'><table class='bq-table'>"
        "<thead><tr><th>#</th><th>Status</th><th>Assertion</th><th>Checks</th>"
        "<th>Runtime (s)</th><th>Ran at</th></tr></thead>"
        f"<tbody>{''.join(body)}</tbody></table></div>"
    )


def _detail_section(r):
    out = [
        f"<section class='bq-section'><h3>{r['n']}. {_e(r['name'])} "
        f"{_badge(r['status'])}</h3>"
    ]
    if r["description"]:
        out.append(f"<p>{_e(r['description'])}</p>")
    out.append(
        f"<p class='bq-checks'>{_e(r['type'])}"
        + (f" &middot; {_e(r['checks'])}" if r["checks"] else "")
        + "</p>"
    )
    if r["status"] == ERROR:
        out.append(
            "<p class='bq-note'>This assertion could not be evaluated, "
            "so it is neither passed nor failed.</p>"
        )
    if r["message"]:
        out.append(f"<pre class='bq-message'>{_e(r['message'])}</pre>")
    out.append(_answer_html(r))
    out.append("</section>")
    return "".join(out)


def build_assertion_report_html(rows, snapshot_name, generated_at):
    """Returns the assertion report as a self-contained HTML document."""
    counts, verdict = summarize(rows)
    cards = "".join(
        f"<div class='bq-count'><b>{counts[key]}</b>{label}</div>"
        for key, label in (
            ("passed", "Passed"),
            ("failed", "Failed"),
            ("errors", "Errors"),
            ("not_run", "Not run"),
        )
    )
    needs_detail = [r for r in rows if r["status"] in (FAIL, ERROR)]
    details = ""
    if needs_detail:
        details = "<h2>Details</h2>" + "".join(_detail_section(r) for r in needs_detail)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Bat-Q Assertion Report — {_e(snapshot_name)}</title>
<style>
{REPORT_CSS}
{TABLE_CSS}
</style>
</head>
<body>
<h1>Bat-Q Assertion Report</h1>
<p class="bq-meta">Snapshot: <strong>{_e(snapshot_name)}</strong> &middot; Generated: {_e(generated_at)}</p>
<div class="bq-verdict {VERDICT_CLASS[verdict]}">{verdict}</div>
<div class="bq-counts">{cards}</div>
<h2>Summary</h2>
{_summary_table(rows) if rows else "<p class='bq-note'>No assertions defined.</p>"}
{details}
<p class="bq-legend bq-note">{LEGEND}</p>
</body>
</html>
"""


# --------------------------------------------------------------------- XLSX
def _cell(value):
    """Excel cells hold scalars only; anything else becomes text."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, pd.Timestamp):
        return value.to_pydatetime().replace(tzinfo=None)
    return str(value)


def _sheet_frame(frame):
    frame = frame.head(MAX_ROWS_XLSX)
    return frame.astype(object).apply(lambda col: col.map(_cell))


def build_assertion_report_xlsx(rows, snapshot_name, generated_at):
    """
    Returns the assertion report as .xlsx bytes, or None if there are no
    assertions. Sheet "Summary" has the verdict and one row per assertion;
    every failed assertion with an answer gets a sheet with the rows it
    looked at.
    """
    if not rows:
        return None
    counts, verdict = summarize(rows)
    buffer = io.BytesIO()
    used = {"Summary"}

    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        book = writer.book
        bold = book.add_format({"bold": True})
        header = book.add_format({"bold": True, "bg_color": "#F4F4F4", "border": 1})
        wrap = book.add_format({"text_wrap": True, "valign": "top"})
        top = book.add_format({"valign": "top"})
        status_fmt = {
            PASS: book.add_format(
                {"bg_color": "#E6F4EA", "font_color": "#14602B", "valign": "top"}
            ),
            FAIL: book.add_format(
                {"bg_color": "#FDECEA", "font_color": "#8A1C14", "valign": "top"}
            ),
            ERROR: book.add_format(
                {"bg_color": "#FFF4D6", "font_color": "#7A5B00", "valign": "top"}
            ),
            NOT_RUN: book.add_format(
                {"bg_color": "#EEEEEE", "font_color": "#555555", "valign": "top"}
            ),
        }

        ws = book.add_worksheet("Summary")
        writer.sheets["Summary"] = ws
        ws.write(0, 0, "Bat-Q Assertion Report", bold)
        meta = [
            ("Snapshot", snapshot_name),
            ("Generated", generated_at),
            ("Verdict", verdict),
            (
                "Counts",
                f"{counts['passed']} passed, {counts['failed']} failed, "
                f"{counts['errors']} errors, {counts['not_run']} not run",
            ),
        ]
        for i, (k, v) in enumerate(meta, start=1):
            ws.write(i, 0, k, bold)
            ws.write(i, 1, v)

        first = len(meta) + 2
        columns = [
            "#",
            "Status",
            "Assertion",
            "Type",
            "Checks",
            "Message",
            "Runtime (s)",
            "Ran at",
        ]
        for c, name in enumerate(columns):
            ws.write(first, c, name, header)
        for i, r in enumerate(rows, start=first + 1):
            ws.write(i, 0, r["n"], top)
            ws.write(i, 1, STATUS_LABEL[r["status"]], status_fmt[r["status"]])
            ws.write(i, 2, r["name"], wrap)
            ws.write(i, 3, r["type"], wrap)
            ws.write(i, 4, r["checks"], wrap)
            ws.write(i, 5, r["message"], wrap)
            if r["runtime"] is not None:
                ws.write(i, 6, round(r["runtime"], 3), top)
            ws.write(i, 7, r["ran_at"], top)
        ws.autofilter(first, 0, first + len(rows), len(columns) - 1)
        ws.freeze_panes(first + 1, 0)
        for c, width in enumerate([5, 10, 32, 34, 48, 60, 12, 20]):
            ws.set_column(c, c, width)

        for r in rows:
            if r["status"] != FAIL:
                continue
            frame = _frame_of(r)
            if frame is None or frame.empty:
                continue
            name = _safe_sheet_name(f"{r['n']} {r['name']}", used)
            ws2 = book.add_worksheet(name)
            writer.sheets[name] = ws2
            ws2.write(
                0, 0, f"{r['n']}. {r['name']} - {STATUS_LABEL[r['status']]}", bold
            )
            if len(frame) > MAX_ROWS_XLSX:
                ws2.write(
                    1, 0, f"Showing the first {MAX_ROWS_XLSX} of {len(frame)} rows."
                )
            _sheet_frame(frame).to_excel(
                writer, sheet_name=name, index=False, startrow=2
            )

    buffer.seek(0)
    return buffer.getvalue()
