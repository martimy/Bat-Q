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
from pybatfish.question import bfq

nan = float("NaN")
NO_DATA = """No data available!
This usually means that the query is not applicable to the network.
"""


def run_query(question, snapshots=None):
    """
    Run Batfish question.
    """

    question_name = question["fun"]
    try:
        # Run query
        fun = getattr(bfq, question_name)
        if snapshots:
            result = (
                fun()
                .answer(snapshot=snapshots[1], reference_snapshot=snapshots[0])
                .frame()
            )
        else:
            result = fun().answer().frame()

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
        removed_str = ", ".join(list(removed))

        # Print the result
        if filtered_df.empty:
            st.warning(NO_DATA)
        else:
            st.dataframe(filtered_df, use_container_width=True)
            # st.session_state.previous.insert(
            #     0, {"name": question_name, "result": filtered_df, "removed": removed_str, "favorite": False})

        # Print removed columns
        if removed:
            st.markdown(f"The query returned these empty columns:  \n{removed_str}.")

    except Exception as e:
        st.error(f"Error running query: {e}")


def run_query_ext(question, snapshots=None):
    """
    Run Batfish question.
    """

    question_name = question["fun"]
    try:
        # Run query
        fun = getattr(bfq, question_name)
        if snapshots:
            result = (
                fun()
                .answer(snapshot=snapshots[1], reference_snapshot=snapshots[0])
                .frame()
            )
        else:
            qargs = {}
            if question.get("input"):
                for param in question["input"]:
                    if param.get("name") and param.get("value"):
                        qargs[param["name"]] = param["value"]
            if qargs:
                result = fun(**qargs).answer().frame()
            else:
                result = fun().answer().frame()

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
        removed_str = ", ".join(list(removed))

        # Print the result
        if filtered_df.empty:
            st.warning(NO_DATA)
        else:
            st.dataframe(filtered_df, use_container_width=True)
            # st.session_state.previous.insert(
            #     0, {"name": question_name, "result": filtered_df, "removed": removed_str, "favorite": False})

        # Print removed columns
        if removed:
            st.markdown(f"The query returned these empty columns:  \n{removed_str}.")

    except Exception as e:
        st.exception(e)  # f"Error running query: {e}")
