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


def update_list(key=None):
    print(key)
    st.session_state.cats[key] = st.session_state[key]


# def update_checkbox():
#     st.session_state.qqqhelp = not st.session_state.qqhelp


# Initialize the session state
if "qqqhelp" not in st.session_state:
    st.session_state.qqqhelp = False

if "qlist" not in st.session_state:
    st.session_state.qlist = {}

if "cats" not in st.session_state:
    st.session_state.cats = {}

# The page starts here
st.header("Select Questions")
questions_help = st.checkbox("Full Help", value=False, key="qshelp")

# Load the YAML file containing all questions
data = upload_questions()
data = data["Batfish"]

# Load previously user-saved questions
saved_questions = st.sidebar.file_uploader(
    "Upload Questions", type="yaml", help="Load saved questions."
)

# Display category selection dropdown
category_list = [item["category"] for item in data]

# alldata inlcudes all data releated to saved questions
if saved_questions:
    alldata = yaml.safe_load(saved_questions)
    alldata = alldata["questions"]
else:
    alldata = st.session_state.get("qlist", {})

all_selected = []

# Split the screen into two columns
col1, col2 = st.columns(2, gap="medium")

with col1:
    st.subheader("All Questions")

    for selected_category in data:

        category_name = selected_category.get("category", "")
        st.markdown(f"**{category_name}**")

        if category_name not in st.session_state.cats:
            st.session_state.cats["category_name"] = {}

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
            kwargs={"key": category_name},
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
    file_name="my_selections.yaml",
    mime="text/yaml",
    help="Save selected questions to a local YAML file.",
)

st.session_state.qlist = alldata
