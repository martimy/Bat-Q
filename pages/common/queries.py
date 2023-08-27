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

# import ast
from pybatfish.question import bfq

# from pybatfish.datamodel import PathConstraints, HeaderConstraints
from pybatfish.client.commands import bf_set_snapshot, bf_fork_snapshot


def get_node_properties():
    return bfq.nodeProperties().answer().frame()["Node"]


def get_interface_properties():
    return bfq.interfaceProperties().answer().frame()["Interface"]


def set_snapshot(active_snapshot):
    return bf_set_snapshot(active_snapshot)


def fork_snapshot(active_snapshot, failed_nodes=None, failed_interfaces=None):
    bf_fork_snapshot(
        active_snapshot,
        active_snapshot + "_Fail",
        deactivate_nodes=failed_nodes,
        deactivate_interfaces=failed_interfaces,
        overwrite=True,
    )


# def get_params(param_list):
#     """
#     Prepare Batfish question parameters

#     """
#     qargs = {}
#     for param in param_list:
#         # print(f"Param: {param}")
#         if param.get("name") and param.get("value"):
#             # we have a name an value
#             param_type = param.get("type")
#             if param_type:
#                 if param_type == "HeaderConstraints":
#                     header_obj = ast.literal_eval(param["value"])
#                     qargs[param["name"]] = HeaderConstraints(**header_obj)
#                 elif param_type == "PathConstraints":
#                     path_obj = ast.literal_eval(param["value"])
#                     qargs[param["name"]] = PathConstraints(**path_obj)
#                 elif param_type == "bool":
#                     qargs[param["name"]] = ast.literal_eval(param["value"])
#                 else:  # Unknown
#                     qargs[param["name"]] = ast.literal_eval(param["value"])
#             else:
#                 qargs[param["name"]] = param["value"]
#     return qargs


def run_query(question, snapshots=None):
    """
    Run Batfish question and get an answer.
    """

    answer = None
    question_fun = question["fun"]
    try:
        # Run query
        fun = getattr(bfq, question_fun)
        qargs = question.get("options")

        if snapshots:  # for comparisions
            if qargs:
                answer = fun(**qargs).answer(
                    snapshot=snapshots[1], reference_snapshot=snapshots[0]
                )
            else:
                answer = fun().answer(
                    snapshot=snapshots[1], reference_snapshot=snapshots[0]
                )
        else:  # for active snapshot
            if qargs:
                answer = fun(**qargs).answer()
            else:
                answer = fun().answer()

    except Exception as e:
        print(e)
    finally:
        return answer
