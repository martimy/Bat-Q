"""
Headless tests of the Snapshots & Setup page: connecting, networks, snapshot
upload, rename/delete and snapshot selection. Uses a fake Batfish session and
a fake socket, so no server is needed.
"""

import socket

import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

from common.assertions import AssertionResult
from fakes import FakeBatfish, page_path

REAL_SOCKET = socket.socket


class FakeSocket(REAL_SOCKET):
    """
    A real socket whose connection attempt to the Batfish port is faked
    (anything else, such as asyncio's internal sockets, behaves normally).
    `outcome` is the connect_ex result, or an exception class to raise.
    """

    outcome = 0
    attempts = []

    def connect_ex(self, address):
        if not (isinstance(address, tuple) and address[1] == 9996):
            return super().connect_ex(address)
        FakeSocket.attempts.append(address)
        if isinstance(FakeSocket.outcome, type):
            raise FakeSocket.outcome()
        return FakeSocket.outcome


@pytest.fixture
def server(monkeypatch):
    """A reachable fake Batfish server; returns the fake session."""
    st.cache_data.clear()
    st.cache_resource.clear()
    bf = FakeBatfish()
    hosts = []
    monkeypatch.setattr(
        "pybatfish.client.session.Session",
        lambda host=None, **kw: hosts.append(host) or bf,
    )
    monkeypatch.setattr(socket, "socket", FakeSocket)
    monkeypatch.delenv("BATFISH_SERVER", raising=False)
    monkeypatch.setattr(st, "image", lambda *a, **k: None)  # needs the repo's logo
    FakeSocket.outcome, FakeSocket.attempts = 0, []
    bf.hosts = hosts
    yield bf
    st.cache_data.clear()
    st.cache_resource.clear()


@pytest.fixture
def editor(monkeypatch):
    """
    AppTest cannot edit a data_editor, so st.data_editor is replaced by a
    function that applies `edits` = {snapshot: {"Rename to": ..., "Delete": ...}}.
    """
    edits = {}

    def fake_editor(table, **kwargs):
        out = table.copy()
        for name, changes in edits.items():
            for column, value in changes.items():
                out.loc[out["Snapshot"] == name, column] = value
        return out

    monkeypatch.setattr(st, "data_editor", fake_editor)
    return edits


def open_page(**state):
    at = AppTest.from_file(page_path("net_setup"), default_timeout=30)
    for key, value in state.items():
        at.session_state[key] = value
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    return at


def box(at, label):
    return next(s for s in at.selectbox if s.label == label)


def field(at, label):
    return next(t for t in at.text_input if t.label == label)


def click(at, label):
    [b for b in at.button if b.label == label][0].click().run()
    assert not at.exception, [e.value for e in at.exception]


def upload(at, name="net.zip", content=b"PK-fake"):
    at.file_uploader[0].set_value((name, content, "application/zip")).run()
    assert not at.exception, [e.value for e in at.exception]


def result(snapshot):
    return AssertionResult("pass", snapshot=snapshot)


# ============================================================== connecting
def test_unreachable_server_shows_an_error_and_nothing_else(server):
    FakeSocket.outcome = 111
    at = open_page()
    assert [e.value for e in at.error] == ["Host 127.0.0.1 is not reachable!"]
    assert server.calls == [] and server.hosts == []
    assert not at.selectbox


@pytest.mark.parametrize(
    "outcome, message",
    [
        (socket.gaierror, "Hostname could not be resolved!"),
        (socket.timeout, "Connection attempt timed out!"),
    ],
)
def test_connection_problems_are_explained(server, outcome, message):
    FakeSocket.outcome = outcome
    at = open_page()
    assert [e.value for e in at.error] == [message]


def test_the_default_server_is_the_local_one(server):
    open_page()
    assert FakeSocket.attempts == [("127.0.0.1", 9996)]
    assert server.hosts == ["127.0.0.1"]


def test_the_server_can_be_set_with_an_environment_variable(server, monkeypatch):
    monkeypatch.setenv("BATFISH_SERVER", "batfish.example.org")
    at = open_page()
    assert FakeSocket.attempts == [("batfish.example.org", 9996)]
    assert server.hosts == ["batfish.example.org"]
    assert "batfish.example.org" in "".join(m.value for m in at.markdown)


# ============================================================ snapshot choice
def test_the_first_snapshot_becomes_the_main_one(server):
    at = open_page()
    assert box(at, "Main Snapshot").options == ["snapA", "snapB"]
    assert at.session_state["activesnap"] == {
        "name": "snapA",
        "failednodes": [],
        "failedinfs": [],
    }
    assert ("set_snapshot", "snapA") in server.calls
    assert at.session_state["bf_session"] is server


def test_changing_the_main_snapshot_resets_its_failures_and_report_data(server):
    at = open_page()
    at.session_state["activesnap"]["failednodes"] = ["r1"]
    at.session_state["report_analysis_data"] = [{"name": "old"}]
    box(at, "Main Snapshot").select("snapB").run()
    assert at.session_state["activesnap"] == {
        "name": "snapB",
        "failednodes": [],
        "failedinfs": [],
    }
    assert at.session_state["report_analysis_data"] == []
    assert ("set_snapshot", "snapB") in server.calls


def test_the_alternate_snapshot_is_remembered(server):
    at = open_page()
    box(at, "Alternate Snapshot").select("snapB").run()
    assert at.session_state["altsnap"]["name"] == "snapB"
    assert box(at, "Alternate Snapshot").value == "snapB"


def test_an_empty_network_has_no_snapshot_choices(server):
    server.networks["NETWORK"] = []
    at = open_page()
    assert any("No snapshots yet" in i.value for i in at.info)
    assert not at.selectbox


# =================================================================== networks
def test_switching_network_clears_what_belonged_to_the_old_one(server):
    server.networks["LAB"] = ["labsnap"]
    at = open_page()
    at.session_state["altsnap"] = {"name": "snapB"}
    at.session_state["assertion_results"] = {"a1@snapA": result("snapA")}
    field(at, "Network Name").set_value("LAB").run()
    assert ("set_network", "LAB") in server.calls
    assert at.session_state["current_network"] == "LAB"
    assert at.session_state["assertion_results"] == {}
    assert box(at, "Main Snapshot").options == ["labsnap"]
    assert at.session_state["activesnap"]["name"] == "labsnap"


def test_a_new_network_name_creates_an_empty_network(server):
    at = open_page()
    field(at, "Network Name").set_value("BRAND_NEW").run()
    assert server.networks["BRAND_NEW"] == []
    assert any("No snapshots yet" in i.value for i in at.info)


def test_an_empty_network_name_keeps_the_current_one(server):
    at = open_page()
    field(at, "Network Name").set_value("   ").run()
    assert at.session_state["network_name"] == "NETWORK"
    assert server.calls_named("set_network") == [("set_network", "NETWORK")]


def test_staying_on_the_same_network_keeps_the_selection(server):
    at = open_page()
    at.session_state["assertion_results"] = {"a1@snapA": result("snapA")}
    at.run()
    assert "a1@snapA" in at.session_state["assertion_results"]


# =================================================================== uploads
def test_an_uploaded_snapshot_is_added_and_selected(server):
    at = open_page()
    upload(at, "net.zip")
    assert ("init_snapshot", "net", False) in server.calls
    assert at.session_state["activesnap"]["name"] == "net"
    assert box(at, "Main Snapshot").options == ["snapA", "snapB", "net"]
    assert box(at, "Main Snapshot").value == "net"


def test_an_uploaded_snapshot_never_overwrites_an_existing_one(server):
    at = open_page()
    upload(at, "snapA.zip")
    assert ("init_snapshot", "snapA_1", False) in server.calls
    assert box(at, "Main Snapshot").options == ["snapA", "snapB", "snapA_1"]


@pytest.mark.parametrize(
    "filename, snapshot",
    [
        ("my network.zip", "my_network"),
        ("net (1).zip", "net_1"),
        ("campus.v2.zip", "campus_v2"),
        ("résumé.zip", "resume"),
        ("日本語.zip", "snapshot"),
    ],
)
def test_the_snapshot_name_is_made_valid_for_batfish(server, filename, snapshot):
    """The snapshot is named after the file, but Batfish only accepts
    letters, digits, '-' and '_', so the name is cleaned up."""
    at = open_page()
    upload(at, filename)
    assert not at.error, [e.value for e in at.error]
    assert ("init_snapshot", snapshot, False) in server.calls
    assert server.networks["NETWORK"] == ["snapA", "snapB", snapshot]
    assert at.session_state["activesnap"]["name"] == snapshot


def test_a_cleaned_up_name_that_is_taken_gets_a_number(server):
    server.networks["NETWORK"].append("my_net")
    at = open_page()
    upload(at, "my net.zip")
    assert ("init_snapshot", "my_net_1", False) in server.calls
    assert at.session_state["activesnap"]["name"] == "my_net_1"


def test_the_same_upload_is_not_added_twice(server):
    at = open_page()
    upload(at, "net.zip")
    at.run()
    at.run()
    assert len(server.calls_named("init_snapshot")) == 1


def test_a_snapshot_that_batfish_rejects_shows_an_error(server):
    server.reject_uploads = True
    at = open_page()
    upload(at, "broken.zip")
    assert any("broken.zip is not recognized" in e.value for e in at.error)
    assert "broken" not in box(at, "Main Snapshot").options
    assert at.session_state["activesnap"]["name"] == "snapA"


# ================================================================ rename/delete
def test_applying_without_changes_does_nothing(server, editor):
    at = open_page()
    click(at, "Apply Snapshot Changes")
    assert not server.calls_named("delete_snapshot")
    assert not server.calls_named("fork_snapshot")


def test_deleting_a_snapshot_removes_it_and_what_referred_to_it(server, editor):
    at = open_page()
    at.session_state["assertion_results"] = {
        "a1@snapA": result("snapA"),
        "a1@snapB": result("snapB"),
    }
    at.session_state["report_analysis_data"] = [{"name": "x"}]
    editor["snapA"] = {"Delete": True}
    click(at, "Apply Snapshot Changes")
    assert ("delete_snapshot", "snapA") in server.calls
    assert server.networks["NETWORK"] == ["snapB"]
    assert set(at.session_state["assertion_results"]) == {"a1@snapB"}
    # the main snapshot was deleted, so the page selects the next one
    assert at.session_state["activesnap"]["name"] == "snapB"


def test_deleting_the_alternate_snapshot_clears_it(server, editor):
    at = open_page()
    box(at, "Alternate Snapshot").select("snapB").run()
    editor["snapB"] = {"Delete": True}
    click(at, "Apply Snapshot Changes")
    assert at.session_state["altsnap"].get("name") != "snapB"
    assert server.networks["NETWORK"] == ["snapA"]


def test_renaming_forks_to_the_new_name_then_deletes_the_old_one(server, editor):
    at = open_page()
    at.session_state["assertion_results"] = {"a1@snapA": result("snapA")}
    editor["snapA"] = {"Rename to": "baseline"}
    click(at, "Apply Snapshot Changes")
    calls = [c[0] for c in server.calls if c[0] in ("fork_snapshot", "delete_snapshot")]
    assert calls == ["fork_snapshot", "delete_snapshot"]
    assert server.calls_named("fork_snapshot")[0][1] == {
        "base_name": "snapA",
        "name": "baseline",
        "overwrite": True,
    }
    assert ("delete_snapshot", "snapA") in server.calls
    assert server.networks["NETWORK"] == ["snapB", "baseline"]
    # the main snapshot follows the rename and its assertion results with it
    assert at.session_state["activesnap"]["name"] == "baseline"
    assert set(at.session_state["assertion_results"]) == {"a1@baseline"}
    assert at.session_state["assertion_results"]["a1@baseline"].snapshot == "baseline"


def test_renaming_to_a_name_in_use_is_refused(server, editor):
    at = open_page()
    editor["snapA"] = {"Rename to": "snapB"}
    click(at, "Apply Snapshot Changes")
    assert any("'snapB' is already in use" in e.value for e in at.error)
    assert not server.calls_named("fork_snapshot")
    assert server.networks["NETWORK"] == ["snapA", "snapB"]


def test_swapping_two_names_in_one_go_is_refused_safely(server, editor):
    at = open_page()
    editor["snapA"] = {"Rename to": "snapB"}
    editor["snapB"] = {"Rename to": "snapA"}
    click(at, "Apply Snapshot Changes")
    assert len([e for e in at.error if "already in use" in e.value]) == 2
    assert server.networks["NETWORK"] == ["snapA", "snapB"]


def test_a_blank_new_name_is_ignored(server, editor):
    at = open_page()
    editor["snapA"] = {"Rename to": "   "}
    click(at, "Apply Snapshot Changes")
    assert not server.calls_named("fork_snapshot") and not at.error


def test_a_name_freed_by_a_delete_in_the_same_go_cannot_be_reused(server, editor):
    """Rows are applied in table order, so the name is still taken when snapA is renamed."""
    at = open_page()
    editor["snapB"] = {"Delete": True}
    editor["snapA"] = {"Rename to": "snapB"}
    click(at, "Apply Snapshot Changes")
    assert not server.calls_named("fork_snapshot")  # the rename was refused
    assert server.networks["NETWORK"] == ["snapA"]  # the delete went through


def test_a_failed_delete_is_reported(server, editor):
    server.fail_delete.add("snapA")
    at = open_page()
    editor["snapA"] = {"Delete": True}
    click(at, "Apply Snapshot Changes")
    assert [e.value for e in at.error] == ["Delete 'snapA': cannot delete snapA"]
    assert server.networks["NETWORK"] == ["snapA", "snapB"]
    assert at.session_state["activesnap"]["name"] == "snapA"  # not cleared


def test_the_other_changes_are_still_applied_when_one_fails(server, editor):
    server.fail_delete.add("snapA")
    at = open_page()
    editor["snapA"] = {"Delete": True}
    editor["snapB"] = {"Rename to": "renamed"}
    click(at, "Apply Snapshot Changes")
    assert server.networks["NETWORK"] == ["snapA", "renamed"]


def test_errors_stay_visible_when_part_of_the_changes_succeeded(server, editor):
    server.fail_delete.add("snapA")
    at = open_page()
    editor["snapA"] = {"Delete": True}
    editor["snapB"] = {"Rename to": "renamed"}
    click(at, "Apply Snapshot Changes")
    assert [e.value for e in at.error] == ["Delete 'snapA': cannot delete snapA"]
    assert server.networks["NETWORK"] == ["snapA", "renamed"]  # the rename went through
    at.run()  # the message is shown once, not on every later rerun
    assert not at.error


@pytest.mark.parametrize("name", ["My Lab", "a/b", "settings", "x" * 151, "lab.1"])
def test_an_invalid_network_name_is_reported_and_the_old_network_is_kept(server, name):
    at = open_page()
    field(at, "Network Name").set_value(name).run()
    assert not at.exception, [e.value for e in at.exception]
    assert any("Invalid network name" in e.value for e in at.error)
    assert at.session_state["network_name"] == "NETWORK"
    assert server.calls_named("set_network") == [("set_network", "NETWORK")]
    # the page still works on the old network
    assert box(at, "Main Snapshot").options == ["snapA", "snapB"]


def test_a_valid_network_name_works_after_an_invalid_one(server):
    server.networks["LAB"] = ["labsnap"]
    at = open_page()
    field(at, "Network Name").set_value("My Lab").run()
    assert at.error
    field(at, "Network Name").set_value("LAB").run()
    assert not at.error
    assert box(at, "Main Snapshot").options == ["labsnap"]
