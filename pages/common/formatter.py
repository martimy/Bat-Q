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

import pandas as pd

nan = float("NaN")
NO_DATA = """No data available!
This usually means that the query is not applicable to the network.
"""


def format_result(result):
    """
    format dataframe
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
