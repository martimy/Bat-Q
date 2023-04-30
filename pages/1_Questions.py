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


if 'qlist' not in st.session_state:
    st.session_state.qlist = {}

st.header('Select Questions')
questions_help = st.checkbox("Full Help", False)

# Load the YAML file
data = upload_questions()
data = data["Batfish"]

saved_questions = st.sidebar.file_uploader(
    "Upload Questions", type='yaml', help="Load previously saved questions from YAML file.")

# Display category selection dropdown
category_list = [item['category'] for item in data]


if saved_questions:
    alldata = yaml.safe_load(saved_questions)
    alldata = alldata['questions']
else:
    alldata = st.session_state.get("qlist", {})
all_selected = []


# To save the list when navigating to another page
default = {category: [item["name"] for item in alldata[category] if item.get("name")] for category in alldata}


col1, col2 = st.columns(2, gap="medium")

with col1:
    st.subheader("All Questions")

    for selected_category in category_list:
        st.markdown(f"**{selected_category}**")

        # Filter the data based on the selected category
        category_data = [
            item for item in data if item['category'] == selected_category][0]

        if questions_help:
            st.markdown(category_data.get('description', ''))

        # Display name selection dropdown
        questions_list = [item['name'] for item in category_data['questions']]
        selected_quetions = st.multiselect(
            "Select a Question", questions_list, default=default.get(selected_category))

        all_selected.extend(selected_quetions)

        # Filter the data based on the selected question
        questions_data = [item for item in category_data['questions']
                          if item['name'] in selected_quetions]
        alldata[selected_category] = questions_data

with col2:
    st.subheader("Selected Questions")

    s = [f"{i+1}. {q}" for i, q in enumerate(all_selected)]
    st.markdown('\n'.join(s))

    yaml_list = yaml.dump({"questions": alldata})

st.sidebar.download_button(
    label="Save Seletions",
    data=yaml_list,
    file_name='my_selections.yaml',
    mime='text/yaml',
    help="Save selected questions to a local YAML file."
)

st.session_state.qlist = alldata
