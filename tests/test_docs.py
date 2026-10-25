"""
Keeps the documentation honest: its examples must load, and it must mention
every assertion the app offers.
"""

import re

import pytest

from common.assertion_io import load_assertions
from common.assertion_specs import ASSERTION_SPECS
from common.bfqs import read_questions
from fakes import ROOT

ASSERTIONS_GUIDE = (ROOT / "docs" / "assertions.md").read_text()
FUNS = {q["fun"] for c in read_questions()["Batfish"] for q in c["questions"]}


def test_yaml_examples_in_the_guide_load():
    blocks = re.findall(r"```yaml\n(.*?)```", ASSERTIONS_GUIDE, re.S)
    assert blocks, "the guide should contain at least one YAML example"
    for block in blocks:
        assertions, errors = load_assertions(block, known_funs=FUNS)
        assert errors == [] and assertions


@pytest.mark.parametrize("name", list(ASSERTION_SPECS))
def test_the_guide_lists_every_assertion(name):
    assert f"`{name}`" in ASSERTIONS_GUIDE


def test_the_guide_lists_the_header_fields_batfish_accepts():
    import attr
    from pybatfish.datamodel.flow import HeaderConstraints

    for field in attr.fields(HeaderConstraints):
        assert f"`{field.name}`" in ASSERTIONS_GUIDE, field.name


def test_the_shipped_example_file_loads():
    text = (ROOT / "examples" / "assertions.yaml").read_text()
    assertions, errors = load_assertions(text, known_funs=FUNS)
    assert errors == [] and len(assertions) == 9
