"""Headless tests of the Questions page (selection, parameters, YAML files)."""

import pytest
import yaml
from streamlit.testing.v1 import AppTest

from common.bfqs import read_questions
from fakes import page_path

CATEGORIES = [c["category"] for c in read_questions()["Batfish"]]
SCHEMA = {
    q["name"]: {"fun": q["fun"], "input": q.get("input", []), "category": c["category"]}
    for c in read_questions()["Batfish"]
    for q in c["questions"]
}
NODE_PROPS = "Node Properties"
BGP_EDGES = "BGP Edges"
TRACEROUTE = "Traceroute"  # has required parameters


@pytest.fixture
def fragment_reruns(monkeypatch):
    """
    AppTest always reruns the whole script, where st.rerun(scope="fragment")
    is an error (in the real app the click only reruns the fragment). Make that
    call a no-op: the state change has already happened, and the next run()
    renders it.
    """
    import streamlit as st

    real_rerun = st.rerun

    def rerun(scope="app"):
        if scope != "fragment":
            real_rerun(scope=scope)

    monkeypatch.setattr(st, "rerun", rerun)


def open_page(**state):
    at = AppTest.from_file(page_path("questions"), default_timeout=30)
    for key, value in state.items():
        at.session_state[key] = value
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    return at


def pick(at, name):
    at.checkbox(key=name).check().run()
    assert not at.exception, [e.value for e in at.exception]


def sidebar_text(at):
    return "\n".join(m.value for m in at.sidebar.markdown)


def upload(at, content, name="select_questions.yaml"):
    if isinstance(content, str):
        content = content.encode("utf-8")
    at.file_uploader[0].set_value((name, content, "text/yaml")).run()


def yaml_of(names):
    return yaml.dump(
        {
            "questions": {
                n: {"category": SCHEMA[n]["category"], "fun": SCHEMA[n]["fun"]}
                for n in names
            }
        }
    )


# ----------------------------------------------------------------- the page
def test_page_lists_every_schema_question_once():
    at = open_page()
    assert {c.key for c in at.checkbox} == set(SCHEMA)
    assert len(at.checkbox) == len(SCHEMA)
    assert {e.label for e in at.expander} == set(CATEGORIES)
    assert "No questions selected yet." in sidebar_text(at)


def test_questions_with_required_parameters_are_marked():
    at = open_page()
    assert at.checkbox(key=TRACEROUTE).label == f"{TRACEROUTE} *"
    assert at.checkbox(key=NODE_PROPS).label == NODE_PROPS


def test_there_is_a_save_button_even_with_nothing_selected():
    at = open_page()
    assert len(at.get("download_button")) == 1


# ---------------------------------------------------------------- selecting
def test_selecting_a_question_adds_it_with_its_category_and_function():
    at = open_page()
    pick(at, NODE_PROPS)
    entry = at.session_state["qlist"][NODE_PROPS]
    assert entry["fun"] == "nodeProperties"
    assert entry["category"] == SCHEMA[NODE_PROPS]["category"]
    text = sidebar_text(at)
    assert SCHEMA[NODE_PROPS]["category"] in text and NODE_PROPS in text


def test_unselecting_removes_the_question():
    at = open_page()
    pick(at, NODE_PROPS)
    at.checkbox(key=NODE_PROPS).uncheck().run()
    assert at.session_state["qlist"] == {}
    assert "No questions selected yet." in sidebar_text(at)


def test_selection_is_kept_in_schema_order():
    at = open_page()
    pick(at, BGP_EDGES)
    pick(at, NODE_PROPS)  # picked second, but earlier in the schema
    names = list(SCHEMA)
    assert list(at.session_state["qlist"]) == sorted(
        [BGP_EDGES, NODE_PROPS], key=names.index
    )


def test_deselect_all_clears_selection_and_checkboxes():
    at = open_page()
    pick(at, NODE_PROPS)
    pick(at, BGP_EDGES)
    [b for b in at.button if b.label == "Deselect All"][0].click().run()
    assert at.session_state["qlist"] == {}
    assert not any(c.value for c in at.checkbox)


def test_expand_and_collapse_all_categories():
    at = open_page()
    [b for b in at.button if b.label == "Expand All"][0].click().run()
    assert at.session_state["cats_expander"] == CATEGORIES
    [b for b in at.button if b.label == "Collapse All"][0].click().run()
    assert at.session_state["cats_expander"] == []


# --------------------------------------------------------------- parameters
def test_a_selected_question_with_parameters_gets_a_parameter_form():
    at = open_page()
    assert "Node Properties_0_nodes" not in {t.key for t in at.text_input}
    pick(at, NODE_PROPS)
    assert "Node Properties_0_nodes" in {t.key for t in at.text_input}


def test_entered_parameters_are_stored_with_the_question():
    at = open_page()
    pick(at, NODE_PROPS)
    at.text_input(key="Node Properties_0_nodes").set_value("r1").run()
    assert at.session_state["qlist"][NODE_PROPS]["variants"] == [{"nodes": "r1"}]


def test_a_variant_clones_the_last_one_and_can_be_removed(fragment_reruns):
    at = open_page()
    pick(at, NODE_PROPS)
    at.text_input(key="Node Properties_0_nodes").set_value("r1").run()
    at.button(key=f"clone_{NODE_PROPS}").click().run()
    at.run()
    assert at.session_state["qlist"][NODE_PROPS]["variants"] == [
        {"nodes": "r1"},
        {"nodes": "r1"},
    ]
    at.text_input(key="Node Properties_1_nodes").set_value("r2").run()
    assert at.session_state["qlist"][NODE_PROPS]["variants"][1] == {"nodes": "r2"}
    at.button(key=f"del_{NODE_PROPS}").click().run()
    at.run()
    assert at.session_state["qlist"][NODE_PROPS]["variants"] == [{"nodes": "r1"}]
    assert "Node Properties_1_nodes" not in {t.key for t in at.text_input}


def test_questions_without_parameters_say_so():
    at = open_page()
    name = "Snapshot Initialization Issues"
    assert not SCHEMA[name]["input"]
    pick(at, name)
    assert not at.exception  # nothing to configure, so no parameter form


# ---------------------------------------------------------------- YAML load
def test_loading_a_file_selects_its_questions_and_ticks_the_boxes():
    at = open_page()
    upload(at, yaml_of([NODE_PROPS, BGP_EDGES]))
    assert not at.exception
    assert set(at.session_state["qlist"]) == {NODE_PROPS, BGP_EDGES}
    assert at.checkbox(key=NODE_PROPS).value and at.checkbox(key=BGP_EDGES).value
    assert not at.checkbox(key=TRACEROUTE).value
    assert set(at.session_state["cats"]) == {
        SCHEMA[NODE_PROPS]["category"],
        SCHEMA[BGP_EDGES]["category"],
    }


def test_loading_a_file_replaces_the_previous_selection():
    at = open_page()
    pick(at, TRACEROUTE)
    upload(at, yaml_of([NODE_PROPS]))
    assert set(at.session_state["qlist"]) == {NODE_PROPS}
    assert not at.checkbox(key=TRACEROUTE).value


def test_loaded_parameters_show_up_in_the_form():
    content = yaml.dump(
        {
            "questions": {
                NODE_PROPS: {
                    "category": SCHEMA[NODE_PROPS]["category"],
                    "fun": "nodeProperties",
                    "variants": [{"nodes": "r1"}, {"nodes": "r2"}],
                }
            }
        }
    )
    at = open_page()
    upload(at, content)
    assert at.text_input(key="Node Properties_0_nodes").value == "r1"
    assert at.text_input(key="Node Properties_1_nodes").value == "r2"


def test_the_same_file_is_not_loaded_twice():
    at = open_page()
    upload(at, yaml_of([NODE_PROPS, BGP_EDGES]))
    at.checkbox(key=BGP_EDGES).uncheck().run()  # the user changes their mind
    assert set(at.session_state["qlist"]) == {NODE_PROPS}  # file is not re-applied


def test_a_file_with_unknown_questions_does_not_break_the_page():
    at = open_page()
    upload(at, yaml.dump({"questions": {"Ghost": {"fun": "ghost"}}}))
    assert not at.exception
    assert "Ghost" in at.session_state["qlist"]
    assert "Ghost" in sidebar_text(at)


@pytest.mark.parametrize(
    "content",
    ["questions: [unclosed", "", "questions: [Node Properties]"],
)
def test_unusable_files_show_an_error_and_keep_the_selection(content):
    at = open_page()
    pick(at, NODE_PROPS)
    upload(at, content)
    assert not at.exception
    assert any("Error loading questions" in e.value for e in at.sidebar.error)
    assert set(at.session_state["qlist"]) == {NODE_PROPS}


@pytest.mark.parametrize(
    "content",
    [
        "assertions:\n  - type: assert_no_forwarding_loops\n",  # an assertions file
        "- just\n- a list\n",
        "other: 1\n",
    ],
)
def test_a_file_without_a_questions_section_is_ignored_silently(content):
    """Documents current behaviour: no message, selection unchanged."""
    at = open_page()
    pick(at, NODE_PROPS)
    upload(at, content)
    assert not at.exception and not at.sidebar.error
    assert set(at.session_state["qlist"]) == {NODE_PROPS}


# ---------------------------------------------------------------- YAML save
def test_the_saved_file_loads_back_to_the_same_selection():
    """The page saves yaml.dump({'questions': qlist}); loading must restore it."""
    at = open_page()
    pick(at, NODE_PROPS)
    at.text_input(key="Node Properties_0_nodes").set_value("r1").run()
    pick(at, BGP_EDGES)
    saved = yaml.dump({"questions": at.session_state["qlist"]})
    fresh = open_page()
    upload(fresh, saved)
    assert fresh.session_state["qlist"] == at.session_state["qlist"]
    assert fresh.text_input(key="Node Properties_0_nodes").value == "r1"
