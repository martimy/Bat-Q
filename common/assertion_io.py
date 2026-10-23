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

# Assertion files (YAML), version 1:
#
#   version: 1
#   assertions:
#     - type: assert_no_forwarding_loops      # required; a key of ASSERTION_SPECS
#       name: Loop check                       # optional label
#       description: Core must be loop free    # optional
#       scope: active                          # optional: active|alternate|both|failed
#       params: {}                             # optional; keys from the spec
#     - type: assert_num_results
#       question:                              # required when the spec needs a question
#         fun: undefinedReferences
#         options: {}
#       params: {num: 0}
#
# In memory, each assertion is a dict with the same keys plus an "id" that is
# assigned on load and never written to the file.

import yaml

from common.assertion_specs import (
    DEFAULT_SCOPE,
    SCOPES,
    get_spec,
    needs_question,
)

SCHEMA_VERSION = 1

_ALLOWED_KEYS = {"type", "name", "description", "scope", "params", "question"}

# Python types accepted for each registry param type (default: anything).
_TYPE_CHECKS = {
    "str": (str,),
    "NodeSpec": (str,),
    "int": (int,),
    "bool": (bool,),
    "list": (list,),
    "dict": (dict,),
    "HeaderConstraints": (dict,),
}


def new_assertion_id(alist):
    """Returns an id not used by any assertion in alist (a1, a2, ...)."""
    used = {a.get("id") for a in alist}
    n = len(used) + 1
    while f"a{n}" in used:
        n += 1
    return f"a{n}"


def validate_assertion(item, known_funs=None):
    """
    Returns a list of problems with one assertion dict (empty if valid).

    known_funs: optional collection of valid question function names. When
    given, question.fun is checked against it.
    """
    if not isinstance(item, dict):
        return ["must be a mapping"]

    errors = []
    unknown = sorted(set(item) - _ALLOWED_KEYS - {"id"})
    if unknown:
        errors.append(f"unknown key(s): {', '.join(unknown)}")

    spec = get_spec(item.get("type"))
    if spec is None:
        errors.append(f"unknown assertion type: {item.get('type')!r}")
        return errors

    scope = item.get("scope", DEFAULT_SCOPE)
    if scope not in SCOPES:
        errors.append(f"scope must be one of {', '.join(SCOPES)} (got {scope!r})")

    for key in ("name", "description"):
        if key in item and not isinstance(item[key], str):
            errors.append(f"{key} must be text")

    # parameters
    params = item.get("params") or {}
    if not isinstance(params, dict):
        errors.append("params must be a mapping")
    else:
        spec_params = {p["name"]: p for p in spec["params"]}
        for name in sorted(set(params) - set(spec_params)):
            errors.append(f"unknown parameter: {name}")
        for name, p in spec_params.items():
            if name not in params:
                if not p.get("optional", True):
                    errors.append(f"missing required parameter: {name}")
                continue
            expected = _TYPE_CHECKS.get(p.get("type"))
            value = params[name]
            if expected and (
                not isinstance(value, expected)
                or (expected == (int,) and isinstance(value, bool))
            ):
                errors.append(
                    f"parameter {name} must be of type {p['type']} "
                    f"(got {type(value).__name__})"
                )

    # question
    question = item.get("question")
    if needs_question(spec):
        if not isinstance(question, dict) or not question.get("fun"):
            errors.append("question with a 'fun' is required")
        else:
            if known_funs is not None and question["fun"] not in known_funs:
                errors.append(f"unknown question: {question['fun']!r}")
            options = question.get("options")
            if options is not None and not isinstance(options, dict):
                errors.append("question.options must be a mapping")
    elif question is not None:
        errors.append("question is not allowed for this assertion type")

    return errors


def load_assertions(text, known_funs=None):
    """
    Parses assertion YAML text.

    Returns (alist, errors). It is all-or-nothing: if there are any errors,
    alist is empty, so a half-loaded suite is never silently used.
    """
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as e:
        return [], [f"Invalid YAML: {e}"]

    if not isinstance(data, dict) or "assertions" not in data:
        return [], ["File has no 'assertions' section."]

    version = data.get("version", SCHEMA_VERSION)
    if version != SCHEMA_VERSION:
        return [], [
            f"Unsupported assertion file version {version!r} "
            f"(this Bat-Q reads version {SCHEMA_VERSION})."
        ]

    items = data["assertions"]
    if not isinstance(items, list):
        return [], ["'assertions' must be a list."]

    errors = []
    alist = []
    for n, item in enumerate(items, start=1):
        problems = validate_assertion(item, known_funs)
        if problems:
            label = item.get("type", "?") if isinstance(item, dict) else "?"
            errors.extend(f"Assertion #{n} ({label}): {p}" for p in problems)
            continue
        entry = {
            "type": item["type"],
            "name": item.get("name", ""),
            "description": item.get("description", ""),
            "scope": item.get("scope", DEFAULT_SCOPE),
            "params": dict(item.get("params") or {}),
        }
        if item.get("question"):
            entry["question"] = {
                "fun": item["question"]["fun"],
                "options": dict(item["question"].get("options") or {}),
            }
        entry["id"] = new_assertion_id(alist)
        alist.append(entry)

    return ([] if errors else alist), errors


def dump_assertions(alist):
    """Serializes the in-memory assertion list to YAML text (no ids)."""
    out = []
    for a in alist:
        item = {"type": a["type"]}
        if a.get("name"):
            item["name"] = a["name"]
        if a.get("description"):
            item["description"] = a["description"]
        if a.get("scope", DEFAULT_SCOPE) != DEFAULT_SCOPE:
            item["scope"] = a["scope"]
        if a.get("question"):
            item["question"] = {"fun": a["question"]["fun"]}
            if a["question"].get("options"):
                item["question"]["options"] = a["question"]["options"]
        if a.get("params"):
            item["params"] = a["params"]
        out.append(item)
    return yaml.safe_dump(
        {"version": SCHEMA_VERSION, "assertions": out}, sort_keys=False
    )
