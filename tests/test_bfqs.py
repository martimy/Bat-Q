"""
Integrity checks for the question schema (common/bfqs.py) and the input
hints (common/inputs.py). Other code relies on these properties, so a bad
edit to the schema should fail here rather than in the app.
"""

from collections import Counter

import pytest

from common import inputs
from common.assertion_specs import ASSERTION_SPECS
from common.bfqs import read_questions

CATEGORIES = read_questions()["Batfish"]
QUESTIONS = [q for c in CATEGORIES for q in c["questions"]]
INPUTS = [i for q in QUESTIONS for i in q.get("input", [])]


def test_schema_has_categories_with_questions():
    assert CATEGORIES and QUESTIONS
    for c in CATEGORIES:
        assert c["category"] and c["questions"], c.get("category")


def test_every_question_has_a_name_and_a_function():
    for q in QUESTIONS:
        assert isinstance(q.get("name"), str) and q["name"].strip(), q
        assert isinstance(q.get("fun"), str) and q["fun"].isidentifier(), q


def test_names_and_functions_are_unique():
    assert [n for n, c in Counter(q["name"] for q in QUESTIONS).items() if c > 1] == []
    assert [n for n, c in Counter(q["fun"] for q in QUESTIONS).items() if c > 1] == []


def test_question_names_contain_no_underscore():
    """
    Variant naming ("<name>_<n>", see utils.get_next_item) assumes it.
    """
    assert [q["name"] for q in QUESTIONS if "_" in q["name"]] == []


def test_every_input_is_well_formed():
    for i in INPUTS:
        assert isinstance(i.get("name"), str) and i["name"], i
        assert set(i) <= {"name", "type", "optional"}, i
        if "optional" in i:
            assert isinstance(i["optional"], bool), i


def test_input_names_are_unique_within_a_question():
    for q in QUESTIONS:
        names = [i["name"] for i in q.get("input", [])]
        assert len(names) == len(set(names)), q["name"]


def test_every_input_type_has_a_hint():
    types = {i["type"] for i in INPUTS if i.get("type")}
    assert types <= set(inputs.TYPE_HINTS), types - set(inputs.TYPE_HINTS)


# ------------------------------------------------------------- input hints
def test_hints_have_the_fields_the_form_shows():
    for name, hint in inputs.TYPE_HINTS.items():
        assert {"hint", "placeholder", "example"} <= set(hint), name
        assert all(isinstance(v, str) and v for v in hint.values()), name


# ---------------------------------------------------- assertion registry links
def test_assertion_parameter_types_are_known_to_the_form_and_the_validator():
    from common.assertion_io import _TYPE_CHECKS

    plain = {"str", "int", "bool", "list"}  # no hint needed, shown as text
    for name, spec in ASSERTION_SPECS.items():
        for p in spec["params"]:
            t = p["type"]
            assert t in plain or t in inputs.TYPE_HINTS, (name, t)
            assert t in _TYPE_CHECKS, (name, t)


@pytest.mark.parametrize("fun", ["undefinedReferences", "unusedStructures", "bgpEdges"])
def test_example_assertion_files_use_real_questions(fun):
    assert fun in {q["fun"] for q in QUESTIONS}
