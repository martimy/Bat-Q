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

import streamlit as st
from pybatfish.question import load_questions, list_questions
from pybatfish.question import bfq
from pybatfish.client.commands import (
    bf_session,
    bf_set_network,
    bf_init_snapshot,
)

NO_DATA = """No data available!
This usually means that the query is not applicable to the network.
"""

APP = """This is a Streamlit app that enables the user to run network analysis 
queries using [Batfish](https://www.batfish.org/). 
The app allows the user to select a Batfish question by category and name. 
The app runs the selected question and displays the results in a table. 
All answered questions are saved.

Find more information about Batfish questions
[here](https://batfish.readthedocs.io/en/latest/index.html).
"""

nan = float("NaN")


@st.cache_data
def load_data(SNAPSHOT_DIR):
    bf_session.host = "192.168.2.4"
    bf_set_network("SOME_NAME")

    bf_init_snapshot(SNAPSHOT_DIR, name="SNAPSHOT", overwrite=True)
    load_questions()

    # Creat a dict of all questions
    questions_list = list_questions()
    questions_dict = {q['name']: q for q in questions_list}

    # Create a list of all unique tags
    all_tags = list(set(tag for q in questions_list for tag in q['tags']))

    # Create a mapping between a tag and the corresponding names
    tag_to_names = {tag: [q['name']
                          for q in questions_list if tag in q['tags']] for tag in all_tags}

    return questions_dict, all_tags, tag_to_names


st.set_page_config(layout="wide")
st.title('Network Analysis')
st.markdown(APP)

if 'previous' not in st.session_state:
    st.session_state.previous = []

# Get directory path from user
SNAPSHOT_DIR = st.sidebar.text_input(
    'Enter directory path:', '/path/to/configs')

try:
    questions_dict, all_tags, tag_to_names = load_data(SNAPSHOT_DIR)
except Exception as e:
    st.error(e)

tag = st.sidebar.selectbox("Select a Category", all_tags)
question_name = st.sidebar.selectbox("Select a Question", tag_to_names[tag])
st.sidebar.write(questions_dict[question_name]['description'])

st.header(f"Selected Question: {question_name}")

# Check if the question has been answered
answered = any(
    [item['name'] == question_name for item in st.session_state.previous])

if answered:
    st.info("This question is answered below.")

# Run Batfish query and display results
if st.button('Run Query', disabled=answered):
    try:
        # Run query
        fun = getattr(bfq, question_name)
        result = fun().answer().frame()

        # Replace empty lists with NaN values
        for c in result.columns:
            result[c] = result[c].apply(
                lambda y: nan if isinstance(y, list) and len(y) == 0 else y)

        # Replace empty strings with NaN values
        result = result.replace('', nan)

        # Drop all empty columns
        filtered_df = result.dropna(axis=1, how='all')
        filtered_df = filtered_df.replace(nan, '')

        removed = set(result.columns) - set(filtered_df.columns)
        removed_str = ', '.join(list(removed))

        # Print the result
        if filtered_df.empty:
            st.warning(NO_DATA)
        else:
            st.dataframe(filtered_df, use_container_width=True)
            st.session_state.previous.insert(
                0, {"name": question_name, "result": filtered_df, "removed": removed_str, "favorite": False})

        # Print removed columns
        if removed:
            st.write(f"The query returned these empty columns: {removed_str}.")

    except Exception as e:
        st.error(f'Error running query {e}')


# st.header("Answered Questions")
# for item in st.session_state.previous:
#     question = item['name']
#     st.subheader(question)
#     with st.expander("Description", expanded=False):
#         st.markdown(questions_dict[question]['description'])
#     st.dataframe(item['result'], use_container_width=True)
#     if item['removed']:
#         with st.expander("Removed Columns", expanded=False):
#             st.markdown(item['removed'])

for item in st.session_state.previous:
    question = item['name']
    st.subheader(question)

    # Add checkbox for marking as favorite
    # fave = st.checkbox(label='Mark as favorite', value=item['favorite'])
    # item['favorite'] = fave

    with st.expander("Description", expanded=False):
        st.markdown(questions_dict[question]['description'])
    st.dataframe(item['result'], use_container_width=True)
    if item['removed']:
        with st.expander("Removed Columns", expanded=False):
            st.markdown(item['removed'])


if not st.session_state.previous:
    st.write("No answered questions yet.")

# Create the search widget
# search_string = st.sidebar.text_input('Search for a question:', '')
# Filter the list based on the search string
# filtered_items = [item for item in questions_dict.keys() if search_string.lower() in item.lower()]
# Display the filtered items
# selected_items = st.sidebar.selectbox('Select an item:', filtered_items)
# Do something with the selected items
# if selected_items:
#     st.write('You selected:', selected_items)
# else:
#     st.write('No items selected.')
