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


def convert_template(input_data):
    output = []

    for question_name, question_data in input_data.items():
        # category = question_data.get("category", "")
        fun = question_data.get("fun", "")
        # input_fields = question_data.get("input", [])
        variants = question_data.get("variants", [])

        if variants:
            for idx, variant in enumerate(variants):
                variant_data = {
                    "name": f"{question_name}_{idx+1}",
                    "fun": fun,
                    "options": variant,
                }
                output.append(variant_data)
        else:
            variant_data = {"name": question_name, "fun": fun}
            output.append(variant_data)

    return output


# Example input data in the first template format
input_template = {
    "Routes": {
        "category": "Routing and Forwarding Tables",
        "fun": "routes",
        "input": [
            {"name": "nodes"},
            {"name": "network"},
            {"name": "prefixMatchType"},
            {"name": "protocols"},
            {"name": "vrfs"},
            {"name": "rib"},
        ],
        "variants": [{"nodes": "customer"}, {"network": "0.0.0.0/0"}],
    },
    "Snapshot Input File Parse Status": {
        "category": "Snapshot Input",
        "fun": "fileParseStatus",
    },
    "Traceroute": {
        "category": "Packet Forwarding",
        "fun": "traceroute",
        "input": [
            {"name": "startLocation", "optional": False},
            {"name": "headers", "optional": False, "type": "HeaderConstraints"},
            {"name": "maxTraces"},
            {"name": "ignoreFilters"},
        ],
        "variants": [
            {"startLocation": "@enter(customer[GigabitEthernet0/0])"},
            {"dstIps": "8.8.8.8", "srcIps": "192.168.1.10"},
        ],
    },
}

output_template = convert_template_1(input_template)
for item in output_template:
    print(item)
