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
        fun = question_data.get("fun", "")
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
