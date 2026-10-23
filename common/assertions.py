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

import inspect
import time
import warnings
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

from pandas import DataFrame
from pybatfish.client import asserts as bf_asserts
from pybatfish.client.session import Asserts
from pybatfish.datamodel.answer import Answer, TableAnswer
from pybatfish.datamodel.flow import HeaderConstraints
from pybatfish.exception import BatfishAssertException, BatfishAssertWarning

from common.assertion_specs import FROM_QUESTION, FROM_ROUTES, get_spec
from common.queries import get_bf_session

PASS = "pass"
FAIL = "fail"
ERROR = "error"

# Assertions that operate on an existing answer/DataFrame (or routes table)
# rather than on a snapshot. They are module-level functions in
# pybatfish.client.asserts and are NOT available on Session.asserts.
ANSWER_BASED = (
    "assert_zero_results",
    "assert_num_results",
    "assert_has_route",
    "assert_has_no_route",
)


def batq_min_results(answer, num=1, soft=False):
    """
    Bat-Q's own assertion: the answer has at least `num` rows (default 1).
    Mirrors pybatfish's hard/soft behavior and answer handling.
    """
    if isinstance(answer, DataFrame):
        actual = len(answer)
    elif isinstance(answer, TableAnswer):
        actual = len(answer.frame())
    elif isinstance(answer, Answer):
        actual = answer["summary"]["numResults"]
    else:
        raise TypeError("Unrecognized answer type")
    if actual < num:
        return bf_asserts._raise_common(
            f"Expected at least {num} results, found: {actual}", soft
        )
    return True


# Assertions implemented by Bat-Q itself (spec source == "batq").
CUSTOM = {"batq_min_results": batq_min_results}


@dataclass
class AssertionResult:
    """Outcome of a single assertion run."""

    status: str  # PASS, FAIL or ERROR
    message: str = ""
    runtime: float = 0.0  # seconds
    snapshot: str = ""
    ran_at: str = ""
    fun: Optional[str] = None  # question the assertion was applied to, if any
    answer: Any = None  # that question's answer, kept to show failing rows


def result_key(assertion_id, snapshot):
    """Key of an assertion's result in session_state["assertion_results"]."""
    return f"{assertion_id}@{snapshot}"


def list_assertions():
    """
    Returns the assertion names available in the installed pybatfish,
    grouped by how they are called.

    {"snapshot": [...], "answer": [...]}
    """
    session_bound = sorted(n for n in dir(Asserts) if n.startswith("assert_"))
    answer_based = sorted(
        n
        for n, f in inspect.getmembers(bf_asserts, inspect.isfunction)
        if n in ANSWER_BASED
    )
    return {
        "snapshot": session_bound,
        "answer": answer_based + sorted(CUSTOM),
    }


def _prepare_params(params):
    """Converts parameters from their file/form form to what pybatfish expects."""
    params = dict(params)
    if isinstance(params.get("headers"), dict):
        # Also rejects unknown header fields with a clear TypeError.
        params["headers"] = HeaderConstraints(**params["headers"])
    return params


def run_assertion(name: str, snapshot: Optional[str] = None, **params: Any):
    """
    Runs one pybatfish assertion and returns an AssertionResult.

    - Session-bound assertions (e.g., assert_no_forwarding_loops) are called
      through the active Batfish session, with the snapshot passed explicitly.
    - Answer-based assertions (assert_zero_results, assert_num_results,
      assert_has_route, assert_has_no_route, batq_min_results) are called with
      the params given (e.g., answer=..., num=...) and ignore `snapshot`.

    Assertions are always run as hard assertions (soft=False), so a failed
    assertion raises BatfishAssertException, which is reported as FAIL. Any
    other exception (bad parameters, lost connection, ...) is reported as
    ERROR, so a broken run is never mistaken for a pass.

    pybatfish also emits a BatfishAssertWarning when an assertion could not
    really be evaluated (for example, assert_has_no_route "passes" when the
    node or VRF does not exist). Such a run is reported as ERROR too.
    """
    start = time.perf_counter()
    try:
        params = _prepare_params(params)
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            if name in CUSTOM:
                CUSTOM[name](soft=False, **params)
            elif name in ANSWER_BASED:
                fun = getattr(bf_asserts, name)
                fun(soft=False, **params)
            else:
                bf = get_bf_session()
                fun = getattr(bf.asserts, name)
                if snapshot is not None:
                    params["snapshot"] = snapshot
                fun(soft=False, **params)
        notes = [
            str(w.message)
            for w in caught
            if issubclass(w.category, BatfishAssertWarning)
        ]
        if notes:
            status, message = ERROR, "Not evaluated: " + "; ".join(notes)
        else:
            status, message = PASS, ""
    except BatfishAssertException as e:
        status, message = FAIL, str(e)
    except Exception as e:
        status, message = ERROR, f"{type(e).__name__}: {e}"
    return AssertionResult(status, message, time.perf_counter() - start)


def _fetch_answer(spec, item, params, snapshot):
    """
    Runs the question an answer-based assertion needs.
    Returns (question function name, answer). Raises on failure.
    """
    bf = get_bf_session()
    if spec["answer_from"] == FROM_QUESTION:
        question = item.get("question") or {}
        fun = question["fun"]
        options = question.get("options") or {}
        return fun, getattr(bf.q, fun)(**options).answer(snapshot=snapshot)
    if spec["answer_from"] == FROM_ROUTES:
        # Only the routes of the node/VRF being checked are retrieved.
        vrf = params.setdefault("vrf", "default")
        answer = bf.q.routes(nodes=params["node"], vrfs=vrf).answer(snapshot=snapshot)
        return "routes", answer.frame()
    raise ValueError(f"Unsupported answer source: {spec['answer_from']!r}")


def run_assertion_item(item, snapshot):
    """
    Runs one assertion from the assertion list (see common/assertion_io.py)
    on a snapshot and returns an AssertionResult.

    For assertions that check an answer (a chosen question, or the routes of
    a node), the question is run first. If that fails, the result is ERROR
    (never PASS or FAIL), since nothing was actually checked.
    """
    start = time.perf_counter()
    spec = get_spec(item.get("type"))
    params = dict(item.get("params") or {})
    fun = answer = None
    result = None

    if spec is None:
        result = AssertionResult(ERROR, f"Unknown assertion type: {item.get('type')!r}")
    elif spec["call"] == "answer":
        try:
            fun, answer = _fetch_answer(spec, item, params, snapshot)
        except Exception as e:
            fun = fun or (item.get("question") or {}).get("fun") or "routes"
            result = AssertionResult(
                ERROR, f"Question '{fun}' failed: {type(e).__name__}: {e}"
            )
        else:
            params[spec["answer_param"]] = answer

    if result is None:
        result = run_assertion(item["type"], snapshot=snapshot, **params)

    result.runtime = time.perf_counter() - start
    result.snapshot = snapshot
    result.ran_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    result.fun = fun
    result.answer = answer
    return result
