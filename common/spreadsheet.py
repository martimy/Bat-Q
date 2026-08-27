# -*- coding: utf-8 -*-
import io
import re
import pandas as pd
from .presenter import json_to_dataframe, flatten_trace_data, select_questions, format_result, format_result_lite

INVALID_SHEET_CHARS = r'[]:*?/\\'


def _safe_sheet_name(name, used):
    """Excel sheet names: <=31 chars, no []:*?/\\, must be unique."""
    name = re.sub(f"[{re.escape(INVALID_SHEET_CHARS)}]", "_", name)[:31]
    base, i = name, 1
    while name in used:
        suffix = f"_{i}"
        name = base[: 31 - len(suffix)] + suffix
        i += 1
    used.add(name)
    return name


def _traces_to_dataframe(answer_row):
    frames = []
    for idx, trace in enumerate(answer_row):
        fr = json_to_dataframe(trace)
        fr.insert(0, "Trace", idx + 1)
        fr.insert(1, "Disposition", trace["disposition"])
        frames.append(fr)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def question_to_dataframe(question, answer):
    """
    Flattens a single question's answer into one DataFrame for spreadsheet
    export. Returns None when there's nothing tabular to write.
    """
    if not answer:
        return None
    try:
        if question in ["traceroute", "reachability"]:
            return _traces_to_dataframe(answer.rows[0]["Traces"])

        elif question == "bidirectionalTraceroute":
            fwd = _traces_to_dataframe(answer.rows[0]["Forward_Traces"])
            fwd.insert(0, "Direction", "Forward")
            rev = _traces_to_dataframe(answer.rows[0]["Reverse_Traces"])
            rev.insert(0, "Direction", "Reverse")
            return pd.concat([fwd, rev], ignore_index=True)

        elif question == "testFilters":
            return pd.DataFrame(flatten_trace_data(answer.rows))

        elif question in select_questions:
            df, _ = format_result(answer.frame())
            return df

        else:
            df, _ = format_result_lite(answer.frame())
            return df

    except Exception:
        return None


def build_report_xlsx(sections):
    """
    sections: same list you already build for the HTML report
    (each with "name", "fun", "answer"). Returns .xlsx bytes, or None
    if there's nothing to export.
    """
    buffer = io.BytesIO()
    used_names = set()
    wrote_any = False

    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        for item in sections:
            df = question_to_dataframe(item["fun"], item["answer"])
            if df is None or df.empty:
                continue
            sheet_name = _safe_sheet_name(item["name"], used_names)
            df.to_excel(writer, sheet_name=sheet_name, index=False)
            wrote_any = True

    if not wrote_any:
        return None
    buffer.seek(0)
    return buffer.getvalue()