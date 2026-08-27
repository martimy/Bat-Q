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

import streamlit as st
import pandas as pd

# import matplotlib.pyplot as plt
from common.plotting import get_topology, get_routing_topology, plot_plotly

NO_DATA = """No data available!
This usually means that the query is not applicable to the network.
"""
nan = float("NaN")

select_questions = [
    "layer3Edges",
    "Routes",
    "fileParseStatus",
    "userProvidedLayer1Edges",
]

topology_questions = ["layer3Edges", "userProvidedLayer1Edges"]

default_frame_options = {"width": "stretch", "hide_index": True}


def build_column_config(df):
    """
    Infers st.column_config settings from a dataframe's dtypes so that
    st.dataframe's native toolbar (search, sort, download) renders each
    column with an appropriate type instead of plain text.
    """
    config = {}
    for col in df.columns:
        series = df[col]
        if pd.api.types.is_bool_dtype(series):
            config[col] = st.column_config.CheckboxColumn(col)
        elif pd.api.types.is_numeric_dtype(series):
            config[col] = st.column_config.NumberColumn(col)
        else:
            # Batfish frequently returns list/dict-like values that were
            # already stringified upstream; render them as wrapped text
            # so long content doesn't get clipped.
            config[col] = st.column_config.TextColumn(col)
    return config


# def show_dataframe(df, **overrides):
#     """
#     Thin wrapper around st.dataframe that applies the default display
#     options plus an inferred column_config, relying on st.dataframe's
#     built-in search/sort/download toolbar instead of custom filter widgets.
#     """
#     options = {**default_frame_options, **overrides}
#     st.dataframe(df, column_config=build_column_config(df), **options)


def show_dataframe(df, **overrides):
    """
    Thin wrapper around st.dataframe that applies default display options
    and converts custom object columns to strings so PyArrow can serialize them.
    """
    df_clean = df.copy()

    # Convert non-primitive/object columns (like PyBatfish Interface/Node) to strings
    for col in df_clean.columns:
        if df_clean[col].dtype == "object":
            df_clean[col] = df_clean[col].astype(str)

    options = {**default_frame_options, **overrides}
    st.dataframe(df_clean, column_config=build_column_config(df_clean), **options)


def _is_empty_value(y):
    """
    Treat None/NaN, empty (or whitespace-only) strings, and empty
    list/tuple/set/dict values as "empty" so they can be caught when
    deciding whether a whole column is empty. Batfish frequently returns
    empty lists or blank strings instead of None, which plain isna()
    checks miss.
    """
    if y is None:
        return True
    if isinstance(y, (list, tuple, set, dict)):
        return len(y) == 0
    if isinstance(y, str):
        return y.strip() == ""
    try:
        return bool(pd.isna(y))
    except (TypeError, ValueError):
        return False


def format_result(result):
    """
    Format Pandas dataframe to eliminate empty columns.
    """
    for c in result.columns:
        result[c] = result[c].apply(lambda y: nan if _is_empty_value(y) else y)

    filtered_df = result.dropna(axis=1, how="all")
    filtered_df = filtered_df.replace(nan, "")
    removed = set(result.columns) - set(filtered_df.columns)
    return filtered_df, removed


def format_result_lite(df):
    all_empty = df.apply(lambda col: col.map(_is_empty_value).all())
    filtered_df = df.loc[:, ~all_empty]
    removed = set(df.columns) - set(filtered_df.columns)
    return filtered_df, removed


def dict_to_str(data: dict):
    if data:
        st_str = ""
        for key, value in data.items():
            st_str += f"{key} = {value}, "
        return st_str[:-2]
    return ""


def display_options(d):
    st.info(dict_to_str(d), title="Options")


def json_to_dataframe(trace):
    traces_table = pd.DataFrame(columns=["Node", "Type", "Action", "Detail"])
    for hop in trace["hops"]:
        node = hop["node"]["name"]
        for step in hop["steps"]:
            new_trace = pd.DataFrame(
                {
                    "Node": node,
                    "Type": step["type"],
                    "Action": step["action"],
                    "Detail": step["detail"],
                }
            )
            traces_table = pd.concat([traces_table, new_trace], ignore_index=True)
    return traces_table


def display_trace(answer_row):
    """
    Displays traces of reachability and traceroute questions.
    """
    count = len(answer_row)
    if count > 1:
        tabs = st.tabs([f"Trace {idx+1}" for idx in range(count)])
        for idx, tab in enumerate(tabs):
            with tab:
                trace = answer_row[idx]
                st.write(f"**Disposition:** {trace['disposition']}")
                fr = json_to_dataframe(trace)
                show_dataframe(fr)
    else:
        st.write(f"**Disposition:** {answer_row[0]['disposition']}")
        fr = json_to_dataframe(answer_row[0])
        show_dataframe(fr)


def display_result(question, answer):
    """
    Display answers to questions. The formatting depends on question type.
    """
    if not answer:
        st.write("The answer set is empty.")
        return

    try:
        if question in ["traceroute", "reachability"]:
            st.write(f"**Trace status:** {answer['status']}")
            display_trace(answer.rows[0]["Traces"])

        elif question == "bidirectionalTraceroute":
            st.write(f"**Trace status:** {answer['status']}")
            st.markdown(
                "**Forward Flow:**  \n" + dict_to_str(answer.rows[0]["Forward_Flow"])
            )
            st.markdown("**Forward Trace(s):**")
            display_trace(answer.rows[0]["Forward_Traces"])

            st.write(
                "**Reverse Flow:**  \n" + dict_to_str(answer.rows[0]["Reverse_Flow"])
            )
            st.markdown("**Reverse Trace(s):**")
            display_trace(answer.rows[0]["Reverse_Traces"])

        elif question == "testFilters":
            flattened = pd.DataFrame(flatten_trace_data(answer.rows))
            show_dataframe(flattened)

        elif question in select_questions:
            filtered_df, removed = format_result(answer.frame())
            if filtered_df.empty:
                st.warning(NO_DATA)
            else:
                show_dataframe(filtered_df)

            if removed:
                removed_str = ", ".join(list(removed))
                st.info(removed_str, title="Empty Columns")
        else:
            filtered_df, removed = format_result_lite(answer.frame())
            if filtered_df.empty:
                st.warning(NO_DATA)
            else:
                show_dataframe(filtered_df)

            if removed:
                removed_str = ", ".join(list(removed))
                st.info(removed_str, title="Empty Columns")

        # if question in topology_questions:
        #     _, col, _ = st.columns([1, 2, 1])
        #     fig = plot_figure(get_topology(answer.frame()))
        #     col.pyplot(fig, clear_figure=True)
        #     plt.close(fig)

        # elif question == "bgpEdges":
        #     _, col, _ = st.columns([1, 2, 1])
        #     fig = plot_figure(get_routing_topology(answer.frame()))
        #     col.pyplot(fig, clear_figure=True)
        #     plt.close(fig)

        # --- Using (Plotly) ---
        if question in topology_questions:
            fig = plot_plotly(get_topology(answer.frame()))
            st.plotly_chart(fig, width="stretch")

        elif question == "bgpEdges":
            fig = plot_plotly(get_routing_topology(answer.frame()))
            st.plotly_chart(fig, width="stretch")

        # --- Using (Pyvis) ---
        # if question in topology_questions:
        #     g = get_topology(answer.frame())
        #     plot_pyvis(g)

        # elif question == "bgpEdges":
        #     g = get_routing_topology(answer.frame())
        #     plot_pyvis(g)

    except Exception as e:
        st.error(f"Unable to display formatted answer. Error: {e}")
        st.write("The received answer:")
        st.write(answer)


def display_result_diff(question, answer):
    """
    Display answers to differential questions.
    """
    try:
        if question in ["traceroute", "differentialReachability"]:
            st.markdown("**Reference Trace:**")
            st.write(f"**Trace status:** {answer['status']}")
            if answer.rows:
                display_trace(answer.rows[0]["Reference_Traces"])

            st.markdown("**Snapshot Trace:**")
            st.write(f"**Trace status:** {answer['status']}")
            if answer.rows:
                display_trace(answer.rows[0]["Snapshot_Traces"])

        elif question == "bidirectionalTraceroute":
            st.markdown(
                "**Forward Flow:**  \n" + dict_to_str(answer.rows[0]["Forward_Flow"])
            )
            st.markdown("**Snapshot Forward Trace:**")
            display_trace(answer.rows[0]["Snapshot_Forward_Traces"])

            st.markdown("**Reference Forward Trace:**")
            display_trace(answer.rows[0]["Reference_Forward_Traces"])

            st.write(
                "**Reverse Flow:**  \n" + dict_to_str(answer.rows[0]["Reverse_Flow"])
            )
            st.markdown("**Snapshot Reverse Trace:**")
            display_trace(answer.rows[0]["Snapshot_Reverse_Traces"])

            st.markdown("**Reference Reverse Trace:**")
            display_trace(answer.rows[0]["Reference_Reverse_Traces"])

        else:
            display_result(question, answer)

    except Exception as e:
        st.error(f"Unable to display formatted answer. Error: {e}")
        st.write("The received answer:")
        st.write(answer)


def flatten_trace_data(data):
    flattened_data = []

    for item in data:
        common_fields = {
            "Node": item.get("Node"),
            "Filter_Name": item.get("Filter_Name"),
            "Flow": item.get("Flow"),
            "Action": item.get("Action"),
            "Line_Content": item.get("Line_Content"),
        }

        if not item.get("Trace"):
            flattened_data.append(
                {**common_fields, "Trace_Text": None, "Trace_Vendor_Structure": None}
            )
            continue

        for trace in item.get("Trace", []):
            trace_element = trace.get("traceElement", {})
            fragments = trace_element.get("fragments", [])

            trace_text = " ".join(f.get("text", "") for f in fragments if f.get("text"))
            vendor_structure = next(
                (
                    f.get("vendorStructureId")
                    for f in fragments
                    if "vendorStructureId" in f
                ),
                None,
            )

            flattened_data.append(
                {
                    **common_fields,
                    "Trace_Text": trace_text,
                    "Trace_Vendor_Structure": vendor_structure,
                }
            )

    return flattened_data