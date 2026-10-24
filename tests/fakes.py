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


# ---------------------------------------------------------------- full session
def default_answers():
    return {
        "nodeProperties": FakeAnswer(pd.DataFrame({"Node": ["r1", "r2"]})),
        "interfaceProperties": FakeAnswer(
            pd.DataFrame({"Interface": ["r1[Gi0]", "r2[Gi0]"]})
        ),
    }


class _Question:
    def __init__(self, bf, fun):
        self.bf, self.fun, self.options = bf, fun, {}

    def __call__(self, **options):
        self.options = options
        return self

    def answer(self, **kwargs):
        self.bf.calls.append(("answer", self.fun, dict(self.options), kwargs))
        result = self.bf.answers.get(self.fun)
        if result is None:
            result = FakeAnswer(pd.DataFrame({"Node": ["r1", "r2"], "Value": [1, 2]}))
        if isinstance(result, Exception):
            raise result
        return result


class _Questions:
    def __init__(self, bf):
        self._bf = bf

    def __getattr__(self, fun):
        if fun.startswith("_"):
            raise AttributeError(fun)
        if fun in self._bf.missing_questions:
            raise AttributeError(fun)
        return _Question(self._bf, fun)


class FakeBatfish:
    """
    A fake pybatfish Session with networks, snapshots and questions.

    answers:  {question function: FakeAnswer | Exception} (a default table is
              returned for questions not listed)
    calls:    everything the app did, as tuples:
              ("set_network", name), ("set_snapshot", name),
              ("init_snapshot", name, overwrite), ("delete_snapshot", name),
              ("fork_snapshot", kwargs), ("answer", fun, options, kwargs)
    """

    def __init__(self, snapshots=("snapA", "snapB"), answers=None):
        self.networks = {"NETWORK": list(snapshots)}
        self.network = "NETWORK"
        self.current = None
        self.calls = []
        self.answers = {**default_answers(), **(answers or {})}
        self.missing_questions = set()
        self.reject_uploads = False
        self.fail_delete = set()
        self.q = _Questions(self)

    def set_network(self, name):
        self.calls.append(("set_network", name))
        self.networks.setdefault(name, [])
        self.network = name

    def list_snapshots(self):
        return list(self.networks[self.network])

    def set_snapshot(self, name):
        self.calls.append(("set_snapshot", name))
        self.current = name
        return name

    def init_snapshot(self, file, name=None, overwrite=False):
        self.calls.append(("init_snapshot", name, overwrite))
        if self.reject_uploads:
            raise ValueError("not a valid snapshot")
        snaps = self.networks[self.network]
        if name in snaps and not overwrite:
            raise ValueError(f"snapshot {name} exists")
        if name not in snaps:
            snaps.append(name)
        self.current = name
        return name

    def delete_snapshot(self, name):
        self.calls.append(("delete_snapshot", name))
        if name in self.fail_delete:
            raise RuntimeError(f"cannot delete {name}")
        self.networks[self.network].remove(name)

    def fork_snapshot(self, **kwargs):
        self.calls.append(("fork_snapshot", dict(kwargs)))
        snaps = self.networks[self.network]
        if kwargs["name"] not in snaps:
            snaps.append(kwargs["name"])
        self.current = kwargs["name"]

    def calls_named(self, name):
        return [c for c in self.calls if c[0] == name]

    def answers_for(self, fun):
        """[(options, answer kwargs)] for every time `fun` was answered."""
        return [(c[2], c[3]) for c in self.calls if c[0] == "answer" and c[1] == fun]
