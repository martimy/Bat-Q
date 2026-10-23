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

import logging

import pandas as pd
import streamlit as st

from common.assertion_io import (
    dump_assertions,
    load_assertions,
    new_assertion_id,
    validate_assertion,
)
from common.assertion_specs import (
    ASSERTION_SPECS,
    DEFAULT_SCOPE,
    get_spec,
    needs_question,
)
from common.assertions import (
    ERROR,
    FAIL,
    PASS,
    result_key,
    run_assertion_item,
)
from common.bfqs import read_questions
from common.inputs import generate_input_fields
from common.presenter import display_result
from common.utils import init_session_state

logging.getLogger("pybatfish").setLevel(logging.WARNING)

#STATUS_ICON = {PASS: "✅", FAIL: "❌", ERROR: "⚠️", None: "⏺️"}
STATUS_ICON = {PASS: ":material/check:", FAIL: ":material/close:", ERROR: ":material/error_outline:", None: ":material/check_box_outline_blank:"}
STATUS_TEXT = {PASS: "Passed", FAIL: "Failed", ERROR: "Error", None: "Not run"}
MAX_MESSAGE_CHARS = 5000
MAX_LOAD_ERRORS_SHOWN = 20

init_session_state()


# ------------------------------------------------------------------ helpers
def _questions():
    """{question name: {"fun", "input", "category"}} from the Batfish schema."""
    return {
        q["name"]: {"fun": q["fun"], "input": q.get("input") or []}
        for cat in read_questions()["Batfish"]
        for q in cat["questions"]
    }


def _assertion_types():
    return list(ASSERTION_SPECS)


def _find(assertion_id):
    for a in st.session_state.alist:
        if a["id"] == assertion_id:
            return a
    return None


def _drop_results(assertion_id):
    prefix = f"{assertion_id}@"
    st.session_state.assertion_results = {
        k: v
        for k, v in st.session_state.assertion_results.items()
        if not k.startswith(prefix)
    }


def _reset_form():
    st.session_state["assertion_editing"] = None
    st.session_state["assertion_form_n"] = (
        st.session_state.get("assertion_form_n", 0) + 1
    )


# ---------------------------------------------------------------- callbacks
def _cb_delete(assertion_id):
    st.session_state.alist = [
        a for a in st.session_state.alist if a["id"] != assertion_id
    ]
    _drop_results(assertion_id)
    if st.session_state.get("assertion_editing") == assertion_id:
        _reset_form()


def _cb_move(assertion_id, delta):
    alist = st.session_state.alist
    i = next((n for n, a in enumerate(alist) if a["id"] == assertion_id), None)
    j = None if i is None else i + delta
    if i is not None and 0 <= j < len(alist):
        alist[i], alist[j] = alist[j], alist[i]


def _cb_edit(assertion_id):
    st.session_state["assertion_editing"] = assertion_id
    st.session_state["assertion_form_n"] = (
        st.session_state.get("assertion_form_n", 0) + 1
    )


def _cb_run(target):
    st.session_state["assertion_run_request"] = target


def _cb_clear_all():
    st.session_state.alist = []
    st.session_state.assertion_results = {}
    _reset_form()


# --------------------------------------------------------------------- form
def render_form(questions):
    """Add / edit form. Returns nothing; mutates session state on submit."""
    editing = _find(st.session_state.get("assertion_editing"))
    n = st.session_state.get("assertion_form_n", 0)
    ns = f"asrt{n}"
    types = _assertion_types()

    with st.expander(
        "Edit assertion" if editing else "Add assertion",
        expanded=bool(editing) or not st.session_state.alist,
    ):
        default_type = editing["type"] if editing else types[0]
        if default_type not in types:  # e.g. loaded from a file, not offered yet
            types = types + [default_type]
        a_type = st.selectbox(
            "Assertion",
            types,
            index=types.index(default_type),
            format_func=lambda t: f"{ASSERTION_SPECS[t]['group']} · {ASSERTION_SPECS[t]['label']}",
            key=f"{ns}_type",
        )
        spec = get_spec(a_type)
        st.caption(spec["description"])

        same_type = editing is not None and editing["type"] == a_type
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input(
                "Name (optional)",
                value=editing["name"] if editing else "",
                key=f"{ns}_name",
            )
        with col2:
            description = st.text_input(
                "Description (optional)",
                value=editing["description"] if editing else "",
                key=f"{ns}_desc",
            )

        params = {}
        if spec["params"]:
            params = generate_input_fields(
                spec["params"],
                f"{ns}_{a_type}",
                defaults=editing["params"] if same_type else None,
            )

        question = None
        if needs_question(spec):
            st.markdown("**Question to check**")
            qnames = list(questions)
            default_q = None
            if same_type and editing.get("question"):
                default_q = next(
                    (
                        qn
                        for qn, q in questions.items()
                        if q["fun"] == editing["question"]["fun"]
                    ),
                    None,
                )
            qname = st.selectbox(
                "Question",
                qnames,
                index=qnames.index(default_q) if default_q else 0,
                key=f"{ns}_{a_type}_question",
            )
            q = questions[qname]
            options = {}
            if q["input"]:
                options = generate_input_fields(
                    q["input"],
                    f"{ns}_{a_type}_q_{q['fun']}",
                    defaults=(
                        editing["question"].get("options")
                        if default_q == qname
                        else None
                    ),
                )
            question = {"fun": q["fun"], "options": options}

        item = {
            "type": a_type,
            "name": name.strip(),
            "description": description.strip(),
            "scope": editing["scope"] if editing else DEFAULT_SCOPE,
            "params": params,
        }
        if question:
            item["question"] = question

        col_ok, col_cancel, _ = st.columns([1, 1, 3])
        with col_ok:
            submit = st.button(
                "Update" if editing else "Add",
                key=f"{ns}_submit",
                type="primary",
                icon=":material/check:",
            )
        with col_cancel:
            if editing and st.button("Cancel", key=f"{ns}_cancel"):
                _reset_form()
                st.rerun()

        if submit:
            problems = validate_assertion(
                item, known_funs={q["fun"] for q in questions.values()}
            )
            if problems:
                for p in problems:
                    st.error(p)
                return
            if editing:
                item["id"] = editing["id"]
                st.session_state.alist = [
                    item if a["id"] == editing["id"] else a
                    for a in st.session_state.alist
                ]
                _drop_results(editing["id"])
            else:
                item["id"] = new_assertion_id(st.session_state.alist)
                st.session_state.alist.append(item)
            _reset_form()
            st.rerun()


# -------------------------------------------------------------------- files
def render_files(questions):
    """Sidebar: load assertions from / save assertions to a YAML file."""
    n = st.session_state.get("assertion_upload_n", 0)
    with st.sidebar:
        st.subheader("Assertion file")
        uploaded = st.file_uploader(
            "Load assertions",
            type=["yaml", "yml"],
            key=f"assertion_upload_{n}",
            help="Replaces the current assertions with those in a YAML file.",
        )
        if uploaded is not None:
            try:
                text = uploaded.getvalue().decode("utf-8")
            except UnicodeDecodeError:
                text = None
                st.error(f"{uploaded.name} is not a UTF-8 text file.")
            if text is not None:
                known_funs = {q["fun"] for q in questions.values()}
                loaded, errors = load_assertions(text, known_funs)
                if errors:
                    st.error(
                        f"Could not load {uploaded.name}. "
                        "No assertions were changed."
                    )
                    for e in errors[:MAX_LOAD_ERRORS_SHOWN]:
                        st.markdown(f"- {e}")
                    if len(errors) > MAX_LOAD_ERRORS_SHOWN:
                        st.markdown(
                            f"- ...and {len(errors) - MAX_LOAD_ERRORS_SHOWN} more"
                        )
                else:
                    st.session_state.alist = loaded
                    st.session_state.assertion_results = {}
                    _reset_form()
                    # A new uploader key clears the widget, so the same file
                    # can be loaded again later.
                    st.session_state["assertion_upload_n"] = n + 1
                    st.toast(
                        f"Loaded {len(loaded)} assertion(s).",
                        icon=":material/folder:",
                    )
                    st.rerun()

        st.download_button(
            "Save assertions to YAML",
            data=dump_assertions(st.session_state.alist),
            file_name="assertions.yaml",
            mime="text/yaml",
            icon=":material/download:",
            disabled=not st.session_state.alist,
            help="Download the current assertions as a YAML file.",
        )


# ------------------------------------------------------------------ running
def run_requested(snapshot):
    """Runs the assertions requested by a Run button, if any."""
    target = st.session_state.pop("assertion_run_request", None)
    if target is None:
        return
    items = (
        list(st.session_state.alist)
        if target == "all"
        else [a for a in st.session_state.alist if a["id"] == target]
    )
    if not items:
        return
    bar = st.progress(0.0, text="Running assertions...")
    for i, a in enumerate(items, start=1):
        bar.progress((i - 1) / len(items), text=f"Running {_title(a)}...")
        st.session_state.assertion_results[result_key(a["id"], snapshot)] = (
            run_assertion_item(a, snapshot)
        )
    bar.empty()


# ------------------------------------------------------------------ display
def _title(a):
    return a["name"] or get_spec(a["type"])["label"]


def _summary(a):
    """One-line summary of what the assertion checks."""
    parts = []
    if a.get("question"):
        parts.append(f"question: `{a['question']['fun']}`")
    parts.extend(f"{k} = `{v}`" for k, v in a["params"].items())
    return " · ".join(parts)


def render_metrics(results):
    counts = {
        s: sum(1 for r in results if r and r.status == s) for s in (PASS, FAIL, ERROR)
    }
    not_run = sum(1 for r in results if r is None)
    cols = st.columns(4)
    cols[0].metric("Passed", counts[PASS])
    cols[1].metric("Failed", counts[FAIL])
    cols[2].metric("Errors", counts[ERROR])
    cols[3].metric("Not run", not_run)


def render_details(result):
    """Shows why an assertion failed or errored."""
    if result.status == ERROR:
        st.error(result.message[:MAX_MESSAGE_CHARS])
        return
    st.write("**Why it failed**")
    if result.answer is not None:
        st.write(f"Answer of `{result.fun}`:")
        if isinstance(result.answer, pd.DataFrame):
            st.dataframe(result.answer)
        else:
            display_result(result.fun, result.answer)
        with st.expander("Assertion message"):
            st.code(result.message[:MAX_MESSAGE_CHARS], language=None)
    else:
        st.code(result.message[:MAX_MESSAGE_CHARS], language=None)


def render_list(snapshot):
    for a in st.session_state.alist:
        aid = a["id"]
        result = st.session_state.assertion_results.get(result_key(aid, snapshot))
        status = result.status if result else None
        with st.container(border=True):
            c_icon, c_text, c_btn = st.columns(
                [0.5, 6, 3.5], vertical_alignment="center"
            )
            c_icon.markdown(f"## {STATUS_ICON[status]}")
            with c_text:
                st.markdown(f"**{_title(a)}**")
                st.caption(
                    "  \n".join(
                        x
                        for x in (a["description"], f"`{a['type']}`", _summary(a))
                        if x
                    )
                )
            with c_btn:
                b = st.columns(5)
                b[0].button(
                    ":material/play_arrow:",
                    key=f"run_{aid}",
                    help="Run",
                    on_click=_cb_run,
                    args=(aid,),
                )
                b[1].button(
                    ":material/edit:",
                    key=f"edit_{aid}",
                    help="Edit",
                    on_click=_cb_edit,
                    args=(aid,),
                )
                b[2].button(
                    ":material/arrow_upward:",
                    key=f"up_{aid}",
                    help="Move up",
                    on_click=_cb_move,
                    args=(aid, -1),
                )
                b[3].button(
                    ":material/arrow_downward:",
                    key=f"down_{aid}",
                    help="Move down",
                    on_click=_cb_move,
                    args=(aid, 1),
                )
                b[4].button(
                    ":material/delete:",
                    key=f"del_{aid}",
                    help="Delete",
                    on_click=_cb_delete,
                    args=(aid,),
                )
            if result and status in (FAIL, ERROR):
                with st.expander(f"{STATUS_TEXT[status]} · details", expanded=False):
                    render_details(result)


def results_table(snapshot):
    rows = []
    for a in st.session_state.alist:
        r = st.session_state.assertion_results.get(result_key(a["id"], snapshot))
        if r:
            rows.append(
                {
                    "Status": f"{STATUS_ICON[r.status]} {STATUS_TEXT[r.status]}",
                    "Assertion": _title(a),
                    "Type": a["type"],
                    "Runtime (s)": round(r.runtime, 2),
                    "Ran at": r.ran_at,
                }
            )
    return pd.DataFrame(rows)


# --------------------------------------------------------------------- page
st.title("Assertions", text_alignment="center")

if "activesnap" in st.session_state and "name" in st.session_state.activesnap:
    snapshot = st.session_state.activesnap["name"]
    st.subheader(f"Snapshot: {snapshot}")

    questions = _questions()
    render_files(questions)
    run_requested(snapshot)
    render_form(questions)

    if not st.session_state.alist:
        st.info("No assertions yet. Add one above.")
    else:
        col_run, col_clear, _ = st.columns([1, 1, 4])
        col_run.button(
            "Run all",
            icon=":material/play_arrow:",
            type="primary",
            on_click=_cb_run,
            args=("all",),
        )
        col_clear.button(
            "Remove all", icon=":material/delete_sweep:", on_click=_cb_clear_all
        )

        results = [
            st.session_state.assertion_results.get(result_key(a["id"], snapshot))
            for a in st.session_state.alist
        ]
        render_metrics(results)
        table = results_table(snapshot)
        if not table.empty:
            with st.expander("Results table"):
                st.dataframe(table, hide_index=True)
        render_list(snapshot)
else:
    st.warning("Please add a snapshot on the Home page to continue.")
