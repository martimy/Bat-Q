"""
Fixtures for the integration tests, which run against a real Batfish server.

Start one with Docker (see README.md in this directory), then run:

    python -m pytest tests/integration

Without a server the tests are skipped, so a plain `python -m pytest` still
passes. Set BATFISH_INTEGRATION=1 (as the CI job does) to make a missing
server an error instead of a skip.
"""

import os
import socket
import time
import uuid
from pathlib import Path

import pytest
from pybatfish.client.session import Session

HERE = Path(__file__).resolve().parent
NETWORKS = HERE / "networks"
HOST = os.environ.get("BATFISH_SERVER", "localhost")
PORT = 9996
REQUIRED = os.environ.get("BATFISH_INTEGRATION") == "1"
SNAPSHOTS = ("live", "candidate")


def _reachable(host, port, timeout=3):
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


@pytest.fixture(scope="session")
def server():
    """The address of a running Batfish server, or a skip/failure."""
    if _reachable(HOST, PORT):
        return HOST
    message = (
        f"No Batfish server at {HOST}:{PORT}. Start one with "
        "'docker run -d -p 9996:9996 batfish/batfish' "
        "(set BATFISH_SERVER for another host)."
    )
    if REQUIRED:
        pytest.fail(message)
    pytest.skip(message)


@pytest.fixture(scope="session")
def bf(server):
    """
    A real session on a throw-away network holding the example snapshots
    "live" and "candidate". The network is deleted at the end.
    """
    session = Session(host=server)
    # the port can open before the service is ready to answer
    for attempt in range(30):
        try:
            session.list_networks()
            break
        except Exception:
            if attempt == 29:
                raise
            time.sleep(2)
    network = f"batq_it_{uuid.uuid4().hex[:8]}"
    session.set_network(network)
    for name in SNAPSHOTS:
        session.init_snapshot(str(NETWORKS / name), name=name, overwrite=True)
    session.set_snapshot("live")
    session.batq_network = network
    yield session
    try:
        session.delete_network(network)
    except Exception:
        pass  # leaving a test network behind is harmless


@pytest.fixture
def bf_state(bf, bf_session_state):
    """
    Bat-Q's session state holding the real session, with the "live" snapshot
    current (earlier tests, such as failure tests, may have changed it).
    """
    bf.set_snapshot("live")
    bf_session_state["bf_session"] = bf
    bf_session_state["activesnap"] = {"name": "live"}
    return bf_session_state
