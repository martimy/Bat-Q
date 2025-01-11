# -*- coding: utf-8 -*-
"""
Copyright 2023 Maen Artimy

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
from pages.common.plotting import get_topology, get_routing_topology, plot_figure

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
# , "bgpEdges", "ospfEdges", "ipsecEdges"]

default_frame_options = {"use_container_width": True, "hide_index": True}


def format_result(result):
    """
    format Panadas dataframe to eliminate empty columns.
    """
    # Replace empty lists with NaN values
    for c in result.columns:
        result[c] = result[c].apply(
            lambda y: nan if isinstance(y, list) and len(y) == 0 else y
        )

    # Replace empty strings with NaN values
    result = result.replace("", nan)

    # Drop all empty columns
    filtered_df = result.dropna(axis=1, how="all")
    filtered_df = filtered_df.replace(nan, "")

    removed = set(result.columns) - set(filtered_df.columns)

    return filtered_df, removed


def format_result_lite(df):
    # Filter columns that include None values
    columns_without_none = df.columns[~df.isna().all()]

    # the filtered columns
    filtered_df = df.loc[:, columns_without_none]
    removed = set(df.columns) - set(filtered_df.columns)

    return filtered_df, removed


def dict_to_str(data: dict):
    if data:
        st = ""
        for key, value in data.items():
            st += f"{key} = {value}, "

        return st[:-2]
    return ""


def display_options(d):
    st.write(f"**Options:** {dict_to_str(d)}")


# def json_to_dataframe(traces):
#     traces_table = pd.DataFrame(
#         columns=["Disposition", "Node", "Type", "Action", "Detail"]
#     )
#     for trace in traces:
#         disposition = trace["disposition"]
#         hops = trace["hops"]
#         for hop in hops:
#             node = hop["node"]["name"]
#             steps = hop["steps"]
#             for step in steps:
#                 step_type = step["type"]
#                 step_action = step["action"]
#                 step_detail = step["detail"]
#                 # new_trace = pd.DataFrame(
#                 #     [disposition, node, step_type, step_action, step_detail],
#                 #     columns=["Disposition", "Node", "Type", "Action", "Detail"]
#                 # )
#                 new_trace = pd.DataFrame(
#                     {
#                         "Disposition": disposition,
#                         "Node": node,
#                         "Type": step_type,
#                         "Action": step_action,
#                         "Detail": step_detail,
#                     }
#                 )
#                 traces_table = pd.concat([traces_table, new_trace], ignore_index=True)

#     return traces_table


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


def filter_frame(df):
    # Sidebar with column selection
    with st.expander("Data Filters", expanded=False):

        selected_columns = st.multiselect("Select Columns", df.columns)

        # Display the selected columns in the DataFrame
        filtered_df = df[selected_columns] if selected_columns else df

        # Filtering the DataFrame based on user input
        string_columns = []
        for column in filtered_df.colmuns:
            if df[column].apply(lambda x: isinstance(x, str)).any():
                string_columns.append(column)

        selected_column = st.selectbox("Select Column to Filter", string_columns)
        filter_value = st.text_input(f"Enter {selected_column} value for filtering")

        if filter_value:
            filtered_df = filtered_df[
                filtered_df[selected_column].str.contains(filter_value, case=False)
            ]
        # else:
        #     filtered_df = df

    # Display filtered DataFrame
    # st.dataframe(filtered_df, **default_frame_options)
    return filtered_df


def display_trace(answer_row):
    """
    Displays traces of rechability and traceroute questions.
    """

    count = len(answer_row)
    if count > 1:
        tabs = st.tabs([f"Trace {idx+1}" for idx in range(count)])
        for idx, tab in enumerate(tabs):
            with tab:
                trace = answer_row[idx]
                st.write(f"**Disposition:** {trace['disposition']}")
                fr = json_to_dataframe(trace)
                st.dataframe(fr, **default_frame_options)
    else:
        st.write(f"**Disposition:** {answer_row[0]['disposition']}")
        fr = json_to_dataframe(answer_row[0])
        st.dataframe(fr, **default_frame_options)


def display_result(question, answer):
    """
    Dispaly answers to questions. The formatting depends on question type.
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

            flattened = flatten_trace_data(answer.rows)
            st.dataframe(flattened)

        elif question in select_questions:
            filtered_df, removed = format_result(answer.frame())

            # filtered_df = filter_frame(df)
            # Print the result
            if filtered_df.empty:
                st.warning(NO_DATA)
            else:
                st.dataframe(filtered_df, **default_frame_options)
                # filter_frame(filtered_df)

            # Print removed columns
            if removed:
                removed_str = ", ".join(list(removed))
                st.markdown(
                    f"The query returned these empty columns:  \n{removed_str}."
                )
        else:  # all other questions:
            # st.dataframe(answer.frame())
            filtered_df, removed = format_result_lite(answer.frame())
            # Print the result
            if filtered_df.empty:
                st.warning(NO_DATA)
            else:
                st.dataframe(filtered_df, **default_frame_options)
                # filter_frame(filtered_df)

            # Print removed columns
            if removed:
                removed_str = ", ".join(list(removed))
                st.markdown(
                    f"The query returned these empty columns:  \n{removed_str}."
                )

        # Plot some answers
        if question in topology_questions:
            _, col, _ = st.columns([1, 2, 1])
            fig = plot_figure(get_topology(answer.frame()))
            col.pyplot(fig)

        elif question == "bgpEdges":
            _, col, _ = st.columns([1, 2, 1])
            fig = plot_figure(get_routing_topology(answer.frame()))
            col.pyplot(fig)

    except Exception as e:
        st.error(f"Unable to display formatted answer. Error: {e}")
        st.write("The received answer:")
        st.write(answer)


def display_result_diff(question, answer):
    """
    Dispaly answers to differential questions. The formatting depends on
    question type.
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
    """
    Flattens the `Trace` list in a given data structure while retaining the rest of the dictionary intact.

    Args:
        data (list): List of dictionaries containing node, flow, and trace information.

    Returns:
        list: Flattened list of dictionaries with trace details extracted.
    """
    flattened_data = []

    for item in data:
        # Common fields that are preserved
        common_fields = {
            "Node": item.get("Node"),
            "Filter_Name": item.get("Filter_Name"),
            "Flow": item.get("Flow"),
            "Action": item.get("Action"),
            "Line_Content": item.get("Line_Content"),
        }

        # If Trace is empty, add the common fields directly
        if not item.get("Trace"):
            flattened_data.append(
                {**common_fields, "Trace_Text": None, "Trace_Vendor_Structure": None}
            )
            continue

        # Process each trace entry
        for trace in item.get("Trace", []):
            trace_element = trace.get("traceElement", {})
            fragments = trace_element.get("fragments", [])

            # Flatten trace fragments into text and vendor structure details
            trace_text = " ".join(f.get("text", "") for f in fragments if f.get("text"))
            vendor_structure = next(
                (
                    f.get("vendorStructureId")
                    for f in fragments
                    if "vendorStructureId" in f
                ),
                None,
            )

            # Append the flattened result
            flattened_data.append(
                {
                    **common_fields,
                    "Trace_Text": trace_text,
                    "Trace_Vendor_Structure": vendor_structure,
                }
            )

    return flattened_data
