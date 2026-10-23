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

"""
Reusable input widgets for Batfish question and assertion parameters.
"""

import ast
import json
import streamlit as st

TYPE_HINTS = {
    "HeaderConstraints": {
        "hint": "Dictionary / JSON object of packet header constraints.",
        "placeholder": "{'dstIps': '8.8.8.8', 'srcIps': '10.0.0.1'}",
        "example": "{'dstIps': '8.8.8.8', 'applications': ['HTTP']}",
        "fields": "srcIps, dstIps, srcPorts, dstPorts, ipProtocols, applications, icmpCodes, icmpTypes, tcpFlags",
    },
    "PathConstraints": {
        "hint": "Dictionary / JSON object of path routing constraints.",
        "placeholder": "{'startLocation': 'node1', 'endLocation': 'node2'}",
        "example": "{'startLocation': 'as1border1', 'endLocation': 'as2border1'}",
        "fields": "startLocation, endLocation, transitLocations, forbiddenLocations",
    },
    "BgpRoute": {
        "hint": "Dictionary or list of dictionaries defining BGP route attributes.",
        "placeholder": "[{'network': '10.0.0.0/24', 'originatorIp': '1.1.1.1', 'originType': 'egp', 'protocol': 'bgp'}]",
        "example": "[{'network': '10.0.0.0/24', 'originatorIp': '1.1.1.1', 'originType': 'egp', 'protocol': 'bgp'}]",
        "fields": "network, originatorIp, originType, protocol, asPath, communities, localPreference, metric",
    },
    "BgpSessionProperties": {
        "hint": "Dictionary defining BGP session properties.",
        "placeholder": "{'localAs': 65001, 'remoteAs': 65002, 'localIp': '1.1.1.1', 'remoteIp': '1.1.1.2'}",
        "example": "{'localAs': 65001, 'remoteAs': 65002, 'localIp': '1.1.1.1', 'remoteIp': '1.1.1.2'}",
        "fields": "localAs, remoteAs, localIp, remoteIp",
    },
    "NodeSpec": {
        "hint": "Batfish Node specifier pattern (node name, regex '/pattern/', or comma-separated).",
        "placeholder": "as1.* or node1,node2",
        "example": "as1.*",
    },
    "IpSpec": {
        "hint": "Batfish IP specifier (IP address or CIDR subnet prefix).",
        "placeholder": "10.0.0.1 or 10.0.0.0/24",
        "example": "10.0.0.0/24",
    },
    "RoutingPolicySpec": {
        "hint": "Routing policy name or regex pattern.",
        "placeholder": "policy_name or /regex/",
        "example": "my_policy",
    },
    "LocationSpec": {
        "hint": "Batfish location specifier: where the flow starts (see the Batfish documentation).",
        "placeholder": "node1",
        "example": "as1border1",
    },
    "FilterSpec": {
        "hint": "Batfish filter specifier: filter (ACL) name, /regex/, or comma-separated names.",
        "placeholder": "acl_name or /regex/",
        "example": "acl_in",
    },
    "RouteMatch": {
        "hint": (
            "Dictionary of columns of the Routes answer that the route must "
            "match. Only the keys given are compared, and values must match "
            "exactly."
        ),
        "placeholder": "{'Network': '10.0.0.0/24', 'Protocol': 'bgp'}",
        "example": "{'Network': '10.0.0.0/24', 'Protocol': 'bgp'}",
        "fields": "Network, Protocol, Next_Hop_IP, Next_Hop_Interface, Admin_Distance, Metric, Tag",
    },
    "bool": {
        "hint": "Boolean flag: True or False.",
        "placeholder": "True / False",
        "example": "True",
    },
}


def generate_input_fields(inputs, question_name, variant_idx=0, defaults=None):
    """
    Renders input fields for a question variant and returns the dictionary of values.
    """
    input_values = {}
    defaults = defaults or {}

    for input_data in inputs:
        name = input_data["name"]
        is_optional = input_data.get("optional", True)
        param_type = input_data.get("type", "str")

        req_mark = " *" if not is_optional else ""
        label = f"{name}{req_mark} ({param_type})"

        type_info = TYPE_HINTS.get(param_type, {})
        placeholder = type_info.get("placeholder", "")

        help_parts = [
            f"**Type:** `{param_type}`",
            f"**Required:** {'Yes' if not is_optional else 'No'}",
        ]
        if type_info.get("hint"):
            help_parts.append(type_info["hint"])
        if type_info.get("fields"):
            help_parts.append(f"**Supported keys:** `{type_info['fields']}`")
        if type_info.get("example"):
            help_parts.append(f"**Example:** `{type_info['example']}`")
        help_text = "\n\n".join(help_parts)

        current_val = str(defaults.get(name, "")) if name in defaults else ""

        param_val = st.text_input(
            label,
            value=current_val,
            placeholder=placeholder,
            key=f"{question_name}_{variant_idx}_{name}",
            help=help_text,
        )

        if param_val.strip():
            val = None
            if input_data.get("type"):
                try:
                    val = ast.literal_eval(param_val)
                except Exception:
                    try:
                        val = json.loads(param_val)
                    except Exception:
                        val = param_val
            else:
                val = param_val
            input_values[name] = val

    return input_values
