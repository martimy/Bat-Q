# -*- coding: utf-8 -*-
import html
import pandas as pd

from .presenter import (
    format_result,
    format_result_lite,
    json_to_dataframe,
    flatten_trace_data,
    dict_to_str,
    select_questions,
    topology_questions,
    NO_DATA,
)
from .plotting import get_topology, get_routing_topology, plot_plotly

TABLE_CSS = """
.bq-table-wrap { overflow-x: auto; margin: 0.5rem 0 1.5rem; }
table.bq-table { border-collapse: collapse; width: max-content; min-width: 100%; font-size: 0.9rem; }
table.bq-table th, table.bq-table td { border: 1px solid #ddd; padding: 6px 10px; text-align: left; white-space: nowrap; }
table.bq-table th { background: #f4f4f4; }
table.bq-table tr:nth-child(even) { background: #fafafa; }
"""


def _df_to_html(df):
    return f'<div class="bq-table-wrap">{df.to_html(classes="bq-table", index=False, na_rep="", border=0)}</div>'


def _table_block(df, removed):
    if df.empty:
        return f"<p class='bq-warning'>{html.escape(NO_DATA)}</p>"
    out = _df_to_html(df)
    if removed:
        out += (
            "<p class='bq-note'><strong>Empty columns removed:</strong> "
            f"{html.escape(', '.join(sorted(removed)))}</p>"
        )
    return out


def _trace_html(answer_row):
    count = len(answer_row)
    parts = []
    for idx in range(count):
        trace = answer_row[idx]
        label = f"Trace {idx + 1}" if count > 1 else "Trace"
        fr = json_to_dataframe(trace)
        parts.append(
            f"<p><strong>{label} — Disposition:</strong> "
            f"{html.escape(str(trace['disposition']))}</p>" + _df_to_html(fr)
        )
    return "".join(parts)


def render_result_html(question, answer):
    """
    Mirrors presenter.display_result's branching, but returns an HTML
    fragment instead of drawing Streamlit widgets. `question` is the
    question's `fun` name (q["fun"]), same as display_result expects.
    """
    if not answer:
        return "<p class='bq-warning'>The answer set is empty.</p>"

    try:
        body = ""

        if question in ["traceroute", "reachability"]:
            body += f"<p><strong>Trace status:</strong> {html.escape(str(answer['status']))}</p>"
            body += _trace_html(answer.rows[0]["Traces"])

        elif question == "bidirectionalTraceroute":
            body += f"<p><strong>Trace status:</strong> {html.escape(str(answer['status']))}</p>"
            body += f"<p><strong>Forward Flow:</strong> {html.escape(dict_to_str(answer.rows[0]['Forward_Flow']))}</p>"
            body += "<p><strong>Forward Trace(s):</strong></p>"
            body += _trace_html(answer.rows[0]["Forward_Traces"])
            body += f"<p><strong>Reverse Flow:</strong> {html.escape(dict_to_str(answer.rows[0]['Reverse_Flow']))}</p>"
            body += "<p><strong>Reverse Trace(s):</strong></p>"
            body += _trace_html(answer.rows[0]["Reverse_Traces"])

        elif question == "testFilters":
            flattened = pd.DataFrame(flatten_trace_data(answer.rows))
            body += _df_to_html(flattened)

        elif question in select_questions:
            filtered_df, removed = format_result(answer.frame())
            body += _table_block(filtered_df, removed)

        else:
            filtered_df, removed = format_result_lite(answer.frame())
            body += _table_block(filtered_df, removed)

        if question in topology_questions:
            fig = plot_plotly(get_topology(answer.frame()))
            body += fig.to_html(full_html=False, include_plotlyjs="cdn")

        elif question == "bgpEdges":
            fig = plot_plotly(get_routing_topology(answer.frame()))
            body += fig.to_html(full_html=False, include_plotlyjs="cdn")

        return body

    except Exception as e:
        return f"<p class='bq-error'>Unable to render this result. Error: {html.escape(str(e))}</p>"


def build_report_html(sections, snapshot_name, generated_at):
    """sections: list of {"name": str, "options": dict|None, "html": str}"""
    section_html = []
    for s in sections:
        opts = ""
        if s.get("options"):
            opts = f"<p class='bq-note'><strong>Options:</strong> {html.escape(dict_to_str(s['options']))}</p>"
        section_html.append(
            f"<section class='bq-section'><h2>{html.escape(s['name'])}</h2>{opts}{s['html']}</section>"
        )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Bat-Q Report — {html.escape(snapshot_name)}</title>
<style>
body {{ font-family: -apple-system, Segoe UI, Roboto, Arial, sans-serif; margin: 2rem; color: #1a1a1a; }}
h1 {{ margin-bottom: 0.2rem; }}
.bq-meta {{ color: #555; margin-bottom: 2rem; }}
.bq-section {{ margin-bottom: 2.5rem; border-top: 1px solid #eee; padding-top: 1.5rem; }}
.bq-warning {{ color: #7a5b00; background: #fff8e1; padding: 8px 12px; border-radius: 4px; }}
.bq-error {{ color: #7a0000; background: #ffecec; padding: 8px 12px; border-radius: 4px; }}
.bq-note {{ color: #666; font-size: 0.85rem; }}
{TABLE_CSS}
</style>
</head>
<body>
<h1>Bat-Q Network Analysis Report</h1>
<p class="bq-meta">Snapshot: <strong>{html.escape(snapshot_name)}</strong> &middot; Generated: {html.escape(generated_at)}</p>
{''.join(section_html)}
</body>
</html>
"""