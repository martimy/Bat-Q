"""Helpers shared by the integration tests."""

import io
import json
import zipfile

from conftest import NETWORKS


def hostnames(snapshot):
    """Device names of an example snapshot, from its config file names."""
    return sorted(p.stem for p in (NETWORKS / snapshot / "configs").glob("*.cfg"))


def host_ip(host, snapshot="live"):
    """Address of a host in the example network (from its JSON description)."""
    data = json.loads((NETWORKS / snapshot / "hosts" / f"{host}.json").read_text())
    return data["hostInterfaces"]["eth0"]["prefix"].split("/")[0]


def snapshot_zip(snapshot, top=None):
    """An example snapshot as zip bytes with one top-level folder."""
    top = top or snapshot
    root = NETWORKS / snapshot
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(root.rglob("*")):
            if path.is_file():
                zf.write(path, f"{top}/{path.relative_to(root).as_posix()}")
    return buffer.getvalue()


def rows(bf, fun, snapshot="live", **options):
    """Number of rows Batfish returns for a question (the oracle for checks)."""
    return len(answer_frame(bf, fun, snapshot, **options))


def answer_frame(bf, fun, snapshot="live", **options):
    return getattr(bf.q, fun)(**options).answer(snapshot=snapshot).frame()


def page_path(name):
    """Absolute path of a Bat-Q page script, for AppTest.from_file."""
    return str(NETWORKS.parents[2] / "views" / f"{name}.py")
