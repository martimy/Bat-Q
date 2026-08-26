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

import ast
import yaml
import streamlit as st
from common.bfqs import read_questions
from common.utils import init_session_state

QUESTIONS_HELP = """
For more details on parameter syntax, see the [Batfish Documentation](https://batfish.readthedocs.io/).
"""
QUESTIONS_INPUT = """
Enter question parameters below.
"""
QUESTIONS_CATEGORIES = """
Select questions from one of more categories below.
"""

init_session_state()


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


def get_cat_quest_dict(dict_data):
    """
    Returns all questions grouped in categories.
    """
    result = {}
    for question in dict_data:
        qdata = dict_data[question]
        cat_qlist = result.setdefault(qdata.get("category", "General"), [])
        cat_qlist.append(question)
    return result


def update_selected_questions(q_name):
    quest_dict = get_questions_dict(bf_questions)
    current_value = st.session_state[q_name]

    if q_name in st.session_state.qlist and not current_value:
        st.session_state.qlist.pop(q_name, None)
    elif q_name not in st.session_state.qlist and current_value:
        st.session_state.qlist[q_name] = {
            "category": quest_dict[q_name]["category"],
            "fun": quest_dict[q_name]["fun"],
        }


def update_expanded_cats(cat_name):
    states = st.session_state.get("cats_expander", [])
    expanded = st.session_state[cat_name]
    print(cat_name, expanded)
    if cat_name in states and not expanded:
        states.remove(cat_name)
    elif cat_name not in states and expanded:
        states.append(cat_name)
    st.session_state["cats_expander"] = states


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
        label = f"{name} *" if not is_optional else f"{name} ({param_type})"
        current_val = str(defaults.get(name, "")) if name in defaults else ""

        param_val = st.text_input(
            label,
            value=current_val,
            key=f"{question_name}_{variant_idx}_{name}",
            help=f"Type: {param_type}, Optional: {is_optional}",
        )

        if param_val.strip():
            if input_data.get("type"):
                try:
                    input_values[name] = ast.literal_eval(param_val)
                except Exception:
                    input_values[name] = param_val
            else:
                input_values[name] = param_val

    return input_values


@st.fragment
def render_question_config(question, data, input_fields):
    """
    Fragment-isolated component to configure parameters and variants for a single question.
    """
    with st.container(border=True):
        st.markdown(f"#### {question}")

        if not input_fields:
            st.info("This question runs without additional parameters.")
            return

        variants = data.setdefault("variants", [{}])

        for idx, variant_opts in enumerate(variants):
            variant_title = f"Variant #{idx + 1}" if len(variants) > 1 else "Parameters"
            with st.expander(variant_title, expanded=True):
                updated_values = generate_input_fields(
                    input_fields, question, variant_idx=idx, defaults=variant_opts
                )
                variants[idx] = updated_values

        col_btn1, col_btn2 = st.columns([1, 1])
        with col_btn1:
            if st.button("[+] Add Variant (Clone)", key=f"clone_{question}"):
                last_variant = variants[-1].copy() if variants else {}
                variants.append(last_variant)
                st.rerun(scope="fragment")

        with col_btn2:
            if len(variants) > 1 and st.button(
                "🗑️ Remove Variant", key=f"del_{question}"
            ):
                variants.pop()
                st.rerun(scope="fragment")


st.header("Questions", help=QUESTIONS_HELP)

# Load questions schema
bf_questions = read_questions()["Batfish"]
quest_dict = get_questions_dict(bf_questions)


left, right = st.columns(2, gap="xxsmall", width=260)
with left:
    if st.button(label="Expand All", icon=":material/expand_all:", width=120):
        st.session_state["cats_expander"] = [
            selected_category.get("category") for selected_category in bf_questions
        ]
with right:
    if st.button(label="Collapse All", icon=":material/collapse_all:", width=120):
        st.session_state["cats_expander"] = []


cats_expander = st.session_state.get("cats_expander", {})
qlist = st.session_state.get("qlist", {})
new_qlist = {}


with st.sidebar:
    st.subheader("Selected Questions")
    if qlist:
        st.markdown("- " + "\n- ".join(qlist.keys()))
    else:
        st.markdown("No questions selected yet.")

    st.subheader("Manage Selections")
    saved_questions = st.file_uploader(
        "Upload Questions", type="yaml", help="Load saved questions from a YAML file."
    )

if saved_questions:
    try:
        loaded = yaml.safe_load(saved_questions)
        if "questions" in loaded:
            st.session_state.qlist = loaded["questions"]
            st.session_state.cats = get_cat_quest_dict(loaded["questions"])
            st.toast("Questions loaded from file!", icon="📂")
    except Exception as e:
        with st.sidebar:
            st.error(f"Error loading questions: {e}")


col1, col2 = st.columns(2, gap="large")

with col1:
    st.subheader("Select Questions")
    st.markdown(QUESTIONS_CATEGORIES)
    for selected_category in bf_questions:
        category_name = selected_category.get("category")
        if category_name:
            with st.expander(
                category_name,
                key=category_name,
                expanded=category_name in cats_expander,
                on_change=update_expanded_cats,
                args=(category_name,),
            ):
                questions_list = [
                    item["name"]
                    for item in selected_category.get("questions", [])
                    if item.get("name")
                ]

                st.subheader("Select Questions")
                for question_name in questions_list:
                    st.checkbox(
                        question_name,
                        value=question_name in qlist,
                        on_change=update_selected_questions,
                        args=(question_name,),
                        key=question_name,
                    )


with col2:
    st.subheader("Configure Parameters")
    if qlist:
        st.markdown(QUESTIONS_INPUT)
        for question, data in qlist.items():
            input_fields = quest_dict.get(question, {}).get("input", [])
            if input_fields:
                render_question_config(question, data, input_fields)
    else:
        st.info("Select questions from the left column to configure their parameters.")


# Sidebar YAML export
yaml_output = yaml.dump({"questions": qlist})


def notify_saved():
    st.toast("Selections saved to select_questions.yaml", icon="💾")


with st.sidebar:
    st.download_button(
        label="💾 Save Selections to YAML",
        data=yaml_output,
        file_name="select_questions.yaml",
        mime="text/yaml",
        help="Download selected questions and parameters to a local YAML file.",
        on_click=notify_saved,
    )
