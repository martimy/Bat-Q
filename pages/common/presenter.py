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


def format_result(result):
    """
    format Panadas dataframe to eleminate empty columns.
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


def json_to_dataframe(traces):
    traces_table = pd.DataFrame(
        columns=["Disposition", "Node", "Type", "Action", "Detail"]
    )
    for trace in traces:
        disposition = trace["disposition"]
        hops = trace["hops"]
        for hop in hops:
            node = hop["node"]["name"]
            steps = hop["steps"]
            for step in steps:
                step_type = step["type"]
                step_action = step["action"]
                step_detail = step["detail"]
                traces_table = traces_table.append(
                    {
                        "Disposition": disposition,
                        "Node": node,
                        "Type": step_type,
                        "Action": step_action,
                        "Detail": step_detail,
                    },
                    ignore_index=True,
                )

    return traces_table


def json_to_markdown_table(traces):
    traces_table = pd.DataFrame(
        columns=["Disposition", "Node", "Type", "Action", "Detail"]
    )
    for trace in traces:
        disposition = trace["disposition"]
        hops = trace["hops"]
        for hop in hops:
            node = hop["node"]["name"]
            steps = hop["steps"]
            for step in steps:
                step_type = step["type"]
                step_action = step["action"]
                step_detail = step["detail"]
                traces_table = traces_table.append(
                    {
                        "Disposition": disposition,
                        "Node": node,
                        "Type": step_type,
                        "Action": step_action,
                        "Detail": step_detail,
                    },
                    ignore_index=True,
                )

    markdown_table = ""
    markdown_table += "| Disposition | Node | Type | Action | Detail |\n"
    markdown_table += "| --- | --- | --- | --- | --- |\n"
    for _, row in traces_table.iterrows():
        disposition = row["Disposition"]
        node = row["Node"]
        step_type = row["Type"]
        step_action = row["Action"]
        step_detail = row["Detail"]
        markdown_table += f"| {disposition} | {node} | {step_type} | {step_action} | {step_detail} |\n"

    return markdown_table


def filter_frame(df):
    # Sidebar with column selection
    with st.expander("Data Filters", expanded=False):

        selected_columns = st.multiselect("Select Columns", df.columns)

        # Display the selected columns in the DataFrame
        filtered_df = df[selected_columns] if selected_columns else df

        selected_column = st.selectbox("Select Column to Filter", filtered_df.columns)
        filter_value = st.text_input(f"Enter {selected_column} value for filtering")

        # Filtering the DataFrame based on user input
        if filter_value:
            filtered_df = filtered_df[
                filtered_df[selected_column].str.contains(filter_value, case=False)
            ]
        # else:
        #     filtered_df = df

    # Display filtered DataFrame
    st.dataframe(filtered_df, use_container_width=True, hide_index=True)


def display_result(question, answer):
    if not answer:
        st.write("There is no answer to this question.")
        return

    try:
        if question in ["traceroute", "reachability"]:
            fr = json_to_dataframe(answer.rows[0]["Traces"])
            st.dataframe(fr)
        elif question == "bidirectionalTraceroute":
            st.markdown(
                "**Forward Flow:**  \n" + dict_to_str(answer.rows[0]["Forward_Flow"])
            )

            st.markdown("**Forward Trace:**")

            fr1 = json_to_dataframe(answer.rows[0]["Forward_Traces"])
            st.dataframe(fr1)

            st.write(
                "**Reverse Flow:**  \n" + dict_to_str(answer.rows[0]["Reverse_Flow"])
            )

            st.markdown("**Reverse Trace:**")

            fr2 = json_to_dataframe(answer.rows[0]["Reverse_Traces"])
            st.dataframe(fr2)
        elif question in select_questions:
            filtered_df, removed = format_result(answer.frame())

            # Print the result
            if filtered_df.empty:
                st.warning(NO_DATA)
            else:
                st.dataframe(filtered_df, use_container_width=True, hide_index=True)
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
                st.dataframe(filtered_df, use_container_width=True, hide_index=True)
                # filter_frame(filtered_df)

            # Print removed columns
            if removed:
                removed_str = ", ".join(list(removed))
                st.markdown(
                    f"The query returned these empty columns:  \n{removed_str}."
                )

    except Exception as e:
        st.error(f"Unable to display answer. Error: {e}")
        st.write("The received answer:")
        st.write(answer)


def display_result_org(answer):
    """
    Formats the Panads dataframe

    """
    try:
        filtered_df, removed = format_result(answer.frame())

        # Print the result
        if filtered_df.empty:
            st.warning(NO_DATA)
        else:
            st.dataframe(filtered_df, use_container_width=True, hide_index=True)
            # filter_frame(filtered_df)

        # Print removed columns
        if removed:
            removed_str = ", ".join(list(removed))
            st.markdown(f"The query returned these empty columns:  \n{removed_str}.")
    # TODO: Rewrite to eleminate dependency on exception to handle special cases
    except Exception as e:
        # st.write(answer.rows[0])
        # markdown_table = json_to_markdown_table(answer.rows[0]["Traces"])
        if answer.rows[0].get("Traces"):
            fr = json_to_dataframe(answer.rows[0]["Traces"])
            st.dataframe(fr)
        elif answer.rows[0].get("Forward_Traces"):

            st.markdown(
                "**Forward Flow:**  \n" + dict_to_str(answer.rows[0]["Forward_Flow"])
            )

            st.markdown("**Forward Trace:**")

            fr1 = json_to_dataframe(answer.rows[0]["Forward_Traces"])
            st.dataframe(fr1)

            st.write(
                "**Reverse Flow:**  \n" + dict_to_str(answer.rows[0]["Reverse_Flow"])
            )

            st.markdown("**Reverse Trace:**")

            fr2 = json_to_dataframe(answer.rows[0]["Reverse_Traces"])
            st.dataframe(fr2)
        else:
            # st.dataframe(answer.frame())
            filtered_df, removed = format_result_lite(answer.frame())
            # Print the result
            if filtered_df.empty:
                st.warning(NO_DATA)
            else:
                st.dataframe(filtered_df, use_container_width=True, hide_index=True)
                # filter_frame(filtered_df)

            # Print removed columns
            if removed:
                removed_str = ", ".join(list(removed))
                st.markdown(
                    f"The query returned these empty columns:  \n{removed_str}."
                )
