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
from common.questions import read_questions
from common.utils import init_session_state

QUESTIONS_INPUT = """
Enter question parameters below. For more details on parameter syntax, 
see the [Batfish Documentation](https://batfish.readthedocs.io/).
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


def update_list(key):
    st.session_state.cats[key] = st.session_state[key]


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
        st.markdown(f"#### ❓ {question}")

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
            if st.button("➕ Add Variant (Clone)", key=f"clone_{question}"):
                last_variant = variants[-1].copy() if variants else {}
                variants.append(last_variant)
                st.rerun(scope="fragment")

        with col_btn2:
            if len(variants) > 1 and st.button("🗑️ Remove Variant", key=f"del_{question}"):
                variants.pop()
                st.rerun(scope="fragment")


st.header("Questions")

# Load questions schema
bf_questions = read_questions()["Batfish"]
quest_dict = get_questions_dict(bf_questions)

with st.sidebar:
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

qlist = st.session_state.get("qlist", {})
new_qlist = {}

col1, col2 = st.columns(2, gap="large")

with col1:
    st.subheader("Select Questions")
    show_desc = st.checkbox("Show Category Descriptions", value=False, key="qshelp")

    for selected_category in bf_questions:
        category_name = selected_category.get("category", "")
        st.markdown(f"### {category_name}")

        if show_desc:
            category_desc = selected_category.get("description", "No description available.")
            st.caption(category_desc)

        questions_list = [
            item["name"]
            for item in selected_category.get("questions", [])
            if item.get("name")
        ]

        selected_questions = st.multiselect(
            f"Questions in {category_name}",
            questions_list,
            key=category_name,
            default=st.session_state.cats.get(category_name, []),
            on_change=update_list,
            kwargs={"key": category_name},
            label_visibility="collapsed",
        )

        for q_name in selected_questions:
            if q_name in qlist:
                new_qlist[q_name] = qlist[q_name]
            else:
                new_qlist[q_name] = {
                    "category": quest_dict[q_name]["category"],
                    "fun": quest_dict[q_name]["fun"],
                }

st.session_state.qlist = new_qlist
qlist = new_qlist

with col2:
    st.subheader("Configure Parameters")
    if qlist:
        st.markdown(QUESTIONS_INPUT)
        for question, data in qlist.items():
            input_fields = quest_dict.get(question, {}).get("input", [])
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
