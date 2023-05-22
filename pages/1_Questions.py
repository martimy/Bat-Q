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

import yaml
import streamlit as st


@st.cache_data
def upload_questions():
    """
    Upload previously saved questions.
    """

    with open("questions.yaml") as f:
        return yaml.safe_load(f)


@st.cache_data
def get_questions_dict(questions_data):
    """
    Returns all questions dict with question full name as key.

    """
    return {
        q["name"]: {
            "fun": q["fun"],
            "input": q.get("input"),
            "category": cat["category"],
        }
        for cat in questions_data
        for q in cat["questions"]
    }


@st.cache_data
def get_categories_dict(dict_data):
    """
    Returns all categories dict with category name as key.

    """
    result = {}
    for question in dict_data:
        qdata = dict_data[question]
        cat_qlist = result.setdefault(qdata["category"], [])
        cat_qlist.append(
            {
                "name": question,
                "input": qdata["input"],
                "fun": qdata["fun"],
            }
        )
    return result


def update_list(key):
    st.session_state.cats[key] = st.session_state[key]


# Initialize the session state
# qlist saves the current selection of questions
if "qlist" not in st.session_state:
    st.session_state.qlist = {}

# cats holds the former selection of questions
if "cats" not in st.session_state:
    st.session_state.cats = {}

# The page starts here
st.header("Select Questions")
questions_help = st.checkbox("Full Help", value=False, key="qshelp")

# Load the YAML file containing all questions
bf_questions = upload_questions()["Batfish"]
quest_dict = get_questions_dict(bf_questions)
# st.write(quest_dict)
cat_dict = get_categories_dict(quest_dict)
# st.write(cat_dict)

# Display category selection dropdown
category_list = [item["category"] for item in bf_questions]

# Load previously user-saved questions
saved_questions = st.sidebar.file_uploader(
    "Upload Questions", type="yaml", help="Load saved questions."
)

# alldata inlcudes all data releated to saved questions
if saved_questions:
    alldata = yaml.safe_load(saved_questions)["questions"]
    st.session_state.cats = {d: [q["name"] for q in alldata[d]] for d in alldata}
else:
    alldata = st.session_state.get("qlist", {})

all_selected = []

# Split the screen into two columns
col1, col2 = st.columns(2, gap="medium")

with col1:
    st.subheader("All Questions")

    for selected_category in bf_questions:

        category_name = selected_category.get("category", "")
        st.markdown(f"**{category_name}**")

        if questions_help:
            category_desc = selected_category.get("description", "No description!")
            st.markdown(category_desc)

        # Get the question list to populate the multiselect widget
        questions_list = [
            item["name"]
            for item in selected_category.get("questions")
            if item.get("name")
        ]

        selected_quetions = st.multiselect(
            "Select a Question",
            questions_list,
            key=category_name,
            default=st.session_state.cats.get(category_name),
            on_change=update_list,
            kwargs={"key": category_name},  # do not change to 'args'
        )

        # Add the selected question to the displayed list
        all_selected.extend(selected_quetions)
        alldata[category_name] = [
            item
            for item in selected_category.get("questions")
            if item["name"] in selected_quetions
        ]

with col2:
    st.subheader("Selected Questions")
    st.markdown("These are all the selected questions.")
    s = [f"{i+1}. {q}" for i, q in enumerate(all_selected)]
    st.markdown("\n".join(s))


yaml_list = yaml.dump({"questions": alldata})

st.sidebar.download_button(
    label="Save Seletions",
    data=yaml_list,
    file_name="select_questions.yaml",
    mime="text/yaml",
    help="Save selected questions to a local YAML file.",
)

st.session_state.qlist = alldata
