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

import re
import streamlit as st


def init_session_state():
    """
    Initializes default session state variables if they do not exist.
    """
    defaults = {
        "bf_session": None,
        "network_name": "NETWORK",
        "current_network": None,
        "activesnap": {},
        "altsnap": {},
        "qlist": {},
        "cats": {},
        "cats_expander": [],
        "report_analysis_data": [],
        "alist": [],  # assertions (see common/assertion_io.py)
        "assertion_results": {},  # "<assertion id>@<snapshot>" -> result
        "assertion_editing": None,  # id of the assertion in the form, if any
        "assertion_form_n": 0,  # bumped to reset the form widgets
        "assertion_upload_n": 0,  # bumped to clear the assertion file uploader
        "last_uploaded_file": None,
        "last_uploaded_questions_file": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def get_same_prefix(input_item, item_list):
    prefix = input_item.split("_")[0]  # Extract the prefix before any trailing number
    matching_items = [item for item in item_list if item.startswith(prefix)]
    return prefix, matching_items


def get_highest_number(input_item, item_list):
    prefix, matching_items = get_same_prefix(input_item, item_list)
    highest_item = None
    highest_number = -1

    for item in matching_items:
        match = re.match(rf"{input_item}_\d+", item)
        if match:
            trailing_number = int(item[len(input_item) + 1 :])
            if trailing_number > highest_number:
                highest_number = trailing_number
                highest_item = item

    return highest_item


def get_next_item(input_item, item_list):
    prefix, _ = get_same_prefix(input_item, item_list)
    highest_item = get_highest_number(prefix, item_list)

    if highest_item:
        highest_number = int(highest_item.split("_")[1])
        next_available_number = highest_number + 1
        next_available_item = f"{prefix}_{next_available_number}"
        return next_available_item
    else:
        return f"{input_item}_1"


def sort_qlist_by_schema(qlist, questions_data=None):
    """
    Sorts a qlist dictionary according to the order of categories and questions
    as they appear in the Batfish questions schema.
    """
    if not qlist:
        return {}

    if questions_data is None:
        try:
            from common.bfqs import read_questions
            questions_data = read_questions()["Batfish"]
        except Exception:
            return qlist

    order = {}
    idx = 0
    for cat in questions_data:
        for q in cat.get("questions", []):
            name = q.get("name")
            if name and name not in order:
                order[name] = idx
                idx += 1

    return dict(sorted(qlist.items(), key=lambda item: order.get(item[0], 9999)))


def convert_template(input_data):
    """
    Returns a list of option sets for a question
    """
    output = []
    sorted_data = sort_qlist_by_schema(input_data)

    for question_name, question_data in sorted_data.items():
        fun = question_data.get("fun", "")
        variants = question_data.get("variants", [])

        if variants:
            for idx, variant in enumerate(variants):
                name = f"{question_name}_{idx}" if idx > 0 else question_name
                variant_data = {"name": name, "fun": fun, "options": variant}
                output.append(variant_data)
        else:
            variant_data = {"name": question_name, "fun": fun}
            output.append(variant_data)

    return output


if __name__ == "__main__":
    items = ["How", "Why", "Why_3", "Why_12", "What"]
    for item in items:
        next_available_item = get_next_item(item, items)
        print(f"{item}: {next_available_item}")
