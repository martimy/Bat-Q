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
from pages.common.formatter import format_result, json_to_dataframe, dict_to_str

NO_DATA = """No data available!
This usually means that the query is not applicable to the network.
"""


def display_result(answer):
    """
    Formats the Panads dataframe

    """
    try:
        filtered_df, removed = format_result(answer.frame())

        # Print the result
        if filtered_df.empty:
            st.warning(NO_DATA)
        else:
            st.dataframe(filtered_df, use_container_width=True)

        # Print removed columns
        if removed:
            removed_str = ", ".join(list(removed))
            st.markdown(f"The query returned these empty columns:  \n{removed_str}.")
    # TODO: Rewrite to eleminate dependency on exception to handle special cases
    except:
        # st.write(answer.rows[0])
        # markdown_table = json_to_markdown_table(answer.rows[0]["Traces"])
        if answer.rows[0].get("Traces"):
            fr = json_to_dataframe(answer.rows[0]["Traces"])
            st.dataframe(fr)
        elif answer.rows[0].get("Forward_Traces"):

            st.markdown("**Forward Flow:**  \n" + dict_to_str(answer.rows[0]["Forward_Flow"]))

            st.markdown("**Forward Trace:**")

            fr1 = json_to_dataframe(answer.rows[0]["Forward_Traces"])
            st.dataframe(fr1)

            st.write("**Reverse Flow:**  \n" + dict_to_str(answer.rows[0]["Reverse_Flow"]))

            st.markdown("**Reverse Trace:**")
            
            fr2 = json_to_dataframe(answer.rows[0]["Reverse_Traces"])
            st.dataframe(fr2)
            
