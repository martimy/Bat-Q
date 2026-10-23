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
from dataclasses import dataclass
from typing import Any, Optional

from pybatfish.client import asserts as bf_asserts
from pybatfish.exception import BatfishAssertException
from pybatfish.client.session import Asserts

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


@dataclass
class AssertionResult:
    """Outcome of a single assertion run."""

    status: str  # PASS, FAIL or ERROR
    message: str = ""
    runtime: float = 0.0  # seconds


def list_assertions():
    """
    Returns the assertion names available in the installed pybatfish,
    grouped by how they are called.

    {"snapshot": [...], "answer": [...]}
    """
    session_bound = sorted(
        n for n in dir(Asserts) if n.startswith("assert_")
    )
    answer_based = sorted(
        n
        for n, f in inspect.getmembers(bf_asserts, inspect.isfunction)
        if n in ANSWER_BASED
    )
    return {"snapshot": session_bound, "answer": answer_based}


def run_assertion(name: str, snapshot: Optional[str] = None, **params: Any):
    """
    Runs one pybatfish assertion and returns an AssertionResult.

    - Session-bound assertions (e.g., assert_no_forwarding_loops) are called
      through the active Batfish session, with the snapshot passed explicitly.
    - Answer-based assertions (assert_zero_results, assert_num_results,
      assert_has_route, assert_has_no_route) are called with the params given
      (e.g., answer=..., num=...) and ignore `snapshot`.

    Assertions are always run as hard assertions (soft=False), so a failed
    assertion raises BatfishAssertException, which is reported as FAIL. Any
    other exception (bad parameters, lost connection, ...) is reported as
    ERROR, so a broken run is never mistaken for a pass.
    """
    start = time.perf_counter()
    try:
        if name in ANSWER_BASED:
            fun = getattr(bf_asserts, name)
            fun(soft=False, **params)
        else:
            bf = get_bf_session()
            fun = getattr(bf.asserts, name)
            if snapshot is not None:
                params["snapshot"] = snapshot
            fun(soft=False, **params)
        status, message = PASS, ""
    except BatfishAssertException as e:
        status, message = FAIL, str(e)
    except Exception as e:
        status, message = ERROR, f"{type(e).__name__}: {e}"
    return AssertionResult(status, message, time.perf_counter() - start)
