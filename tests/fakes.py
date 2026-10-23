"""
Shared test doubles. Nothing here needs a running Batfish server.
"""

from pathlib import Path
from types import SimpleNamespace

import pandas as pd
from pybatfish.exception import BatfishAssertException

ROOT = Path(__file__).resolve().parent.parent


def page_path(name):
    """Absolute path of a page script, for AppTest.from_file."""
    return str(ROOT / "views" / f"{name}.py")


class FakeQuestion:
    """Stands in for bf.q.<question>: returns a fixed number of rows."""

    def __init__(self, rows=0, fail=False, log=None):
        self.rows, self.fail = rows, fail
        self.log = log if log is not None else []

    def __call__(self, **options):
        return self

    def answer(self, snapshot=None, **kwargs):
        self.log.append(snapshot)
        if self.fail:
            raise RuntimeError("boom")
        return pd.DataFrame({"x": range(self.rows)})


ROUTES = pd.DataFrame(
    [
        {"Node": "r1", "VRF": "default", "Network": "10.0.0.0/24", "Protocol": "bgp"},
        {
            "Node": "r1",
            "VRF": "mgmt",
            "Network": "192.168.0.0/24",
            "Protocol": "connected",
        },
        {
            "Node": "r2",
            "VRF": "default",
            "Network": "10.9.0.0/16",
            "Protocol": "static",
        },
    ]
)


class FakeRoutes:
    """Stands in for bf.q.routes: filters by node and VRF like the real one."""

    def __init__(self, calls):
        self.calls, self.kw = calls, {}

    def __call__(self, nodes=None, vrfs=None):
        self.kw = {"nodes": nodes, "vrfs": vrfs}
        self.calls.append(("routes", dict(self.kw)))
        return self

    def answer(self, snapshot=None):
        df = ROUTES
        if self.kw["nodes"]:
            df = df[df["Node"] == self.kw["nodes"]]
        if self.kw["vrfs"]:
            df = df[df["VRF"] == self.kw["vrfs"]]
        return SimpleNamespace(frame=lambda: df)


def fake_session(log, calls):
    """
    A fake Batfish session with the questions and assertions used by the
    assertion page tests. `log` collects snapshots passed to questions and
    `calls` collects (name, kwargs) of the assertions and routes queries.
    """

    def loops(**kw):
        raise BatfishAssertException("Found forwarding loops")

    def recorder(name, fail_if=None):
        def fun(**kw):
            calls.append((name, kw))
            if fail_if and fail_if(kw):
                raise BatfishAssertException(f"{name} failed")
            return True

        return fun

    return SimpleNamespace(
        q=SimpleNamespace(
            undefinedReferences=FakeQuestion(0, log=log),
            bgpEdges=FakeQuestion(3, log=log),
            unusedStructures=FakeQuestion(fail=True, log=log),
            routes=FakeRoutes(calls),
        ),
        asserts=SimpleNamespace(
            assert_no_forwarding_loops=loops,
            assert_no_undefined_references=lambda **kw: True,
            assert_flows_succeed=recorder(
                "flows_succeed", lambda kw: kw["startLocation"] == "bad"
            ),
            assert_flows_fail=recorder("flows_fail"),
            assert_filter_permits=recorder(
                "filter_permits", lambda kw: kw["filters"] == "deny_all"
            ),
            assert_filter_denies=recorder("filter_denies"),
            assert_filter_has_no_unreachable_lines=recorder(
                "no_unreachable", lambda kw: kw["filters"] == "shadowed"
            ),
        ),
    )


class FakeAnswer:
    """
    Stands in for a pybatfish Answer: truthy unless `empty`, has .frame(),
    .rows, and item access (answer["status"]).
    """

    def __init__(self, df=None, rows=None, extra=None, empty=False):
        self._df, self.rows = df, rows or []
        self.extra, self.empty = extra or {}, empty

    def frame(self):
        if isinstance(self._df, Exception):
            raise self._df
        return self._df

    def __getitem__(self, key):
        return self.extra[key]

    def __bool__(self):
        return not self.empty


def trace(disposition="ACCEPTED", node="r1", detail=None):
    """A one-hop Batfish trace as returned inside Answer rows."""
    return {
        "disposition": disposition,
        "hops": [
            {
                "node": {"name": node},
                "steps": [
                    {"type": "Step", "action": "ACT", "detail": detail or {"k": "v"}}
                ],
            }
        ],
    }
