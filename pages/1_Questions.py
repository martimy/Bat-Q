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

import ast
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


def get_cat_quest_dict(dict_data):
    """
    Returns all questions grouped in categories.
    """
    result = {}
    for question in dict_data:
        qdata = dict_data[question]
        cat_qlist = result.setdefault(qdata["category"], [])
        cat_qlist.append(question)
    return result


def update_list(key):
    st.session_state.cats[key] = st.session_state[key]

def generate_input_fields(inputs):
    input_values = {}

    for input_data in inputs:
        name = input_data["name"]
        optional = input_data.get("optional", True)
        mandatory = '*' if not optional else ''
        value = input_data.get("value", "")

        input_values[name] = st.text_input(name+mandatory, value)

    return input_values


# Initialize the session state
# qlist saves the current selection of questions
if "qlist" not in st.session_state:
    st.session_state.qlist = {}

# cats holds the former selection of questions
if "cats" not in st.session_state:
    st.session_state.cats = {}

# The page starts here
st.set_page_config(layout="wide")
st.header("Select Questions")


# Load the YAML file containing all questions
bf_questions = upload_questions()["Batfish"]
quest_dict = get_questions_dict(bf_questions)
# st.write(quest_dict)
# cat_dict = get_categories_dict(quest_dict)
# st.write(cat_dict)

# Display category selection dropdown
category_list = [item["category"] for item in bf_questions]

# Load previously user-saved questions
saved_questions = st.sidebar.file_uploader(
    "Upload Questions", type="yaml", help="Load saved questions."
)

# qlist inlcudes all data releated to saved questions
if saved_questions:
    qlist = yaml.safe_load(saved_questions)["questions"]
    st.session_state.cats = get_cat_quest_dict(qlist)
else:
    qlist = st.session_state.get("qlist", {})

all_selected = []
new_qlist = {}


# all_tab, input_tab = st.tabs(["Questions", "Options"])

option = st.selectbox(
    'Tasks',
    ('Select Questions', 'Enter Input Parameters'))

if option == 'Select Questions':

    st.subheader("All Questions")
    st.write("Select questions by category:")
    questions_help = st.checkbox("Category Description", value=False, key="qshelp")
    # Dispplay a multiselect list for each question category
    for selected_category in bf_questions:
    
        category_name = selected_category.get("category", "")
        st.markdown(f"#### {category_name}")
    
        # Show description of the category if required
        if questions_help:
            category_desc = selected_category.get("description", "No description!")
            st.markdown(category_desc)
    
        # Get the question list to populate the multiselect widget
        # from the main questions database
        questions_list = [
            item["name"]
            for item in selected_category.get("questions")
            if item.get("name")
        ]
    
        # Get the selected questions
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
        for question in selected_quetions:
            if question in qlist:
                new_qlist[question] = qlist[question]
            else:
                new_qlist[question] = quest_dict[question]

    qlist = new_qlist    

elif option == 'Enter Input Parameters':
    st.subheader("Input Paramters")
    st.markdown(
        "Enter questions' input paramters here. \
            For more information, see the [docs](https://batfish.readthedocs.io/). \
                Note: Only questions that take input parameters are listed.")

    
    for question, data in qlist.items():
        input_fields = data.get("input", [])
    
        
        if input_fields:
            st.write(f"##### Q: {question}")
            
            # create a form for a the input parameters
            input_values = generate_input_fields(input_fields)
            # st.write(input_values)
            for v in input_values:
                for fld in input_fields:
                    if fld["name"] == v:
                        if input_values[v]:
                            if fld.get("type") == "HeaderConstraints":
                                fld["value"] = ast.literal_eval(input_values[v])
                            else:
                                fld["value"] = input_values[v]
                        elif fld.get("value"):
                            del fld["value"]
                        break


else:
    st.write("Please select an option.")
        
# st.subheader("Selected Questions")
# # st.markdown("These are all the selected questions.")
# s = [f"{i+1}. {q}" for i, q in enumerate(all_selected)]
# st.markdown("\n".join(s))

yaml_list = yaml.dump({"questions": qlist})

st.sidebar.download_button(
    label="Save Seletions",
    data=yaml_list,
    file_name="select_questions.yaml",
    mime="text/yaml",
    help="Save selected questions to a local YAML file.",
)


    
st.session_state.qlist = qlist
# st.session_state.cats = qlist
