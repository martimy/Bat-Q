"""The test setup itself: example data, and a real server holding it."""

import io
import zipfile

import pytest

from it_helpers import host_ip, hostnames, snapshot_zip

pytestmark = pytest.mark.integration


# ---- these need no server: they check the example data and the zip builder
def test_example_network_has_the_expected_devices():
    assert len(hostnames("live")) == 13
    assert {"as1border1", "as2dept1", "as3core1"} <= set(hostnames("live"))
    assert hostnames("live") == hostnames("candidate")


def test_hosts_have_addresses():
    assert host_ip("host1") == "2.128.0.101"
    assert host_ip("host2") == "2.128.1.101"


def test_snapshot_zip_has_one_top_level_folder_with_configs():
    with zipfile.ZipFile(io.BytesIO(snapshot_zip("live", "mynet"))) as zf:
        names = zf.namelist()
    assert zipfile.is_zipfile(io.BytesIO(snapshot_zip("live")))
    assert {n.split("/")[0] for n in names} == {"mynet"}
    assert "mynet/configs/as1border1.cfg" in names
    assert "mynet/hosts/host1.json" in names


# ---- these need the server
def test_both_snapshots_are_loaded(bf):
    assert {"live", "candidate"} <= set(bf.list_snapshots())


def test_every_device_is_a_node(bf):
    nodes = set(
        bf.q.nodeProperties().answer(snapshot="live").frame()["Node"].str.lower()
    )
    assert set(hostnames("live")) <= nodes
    assert {"host1", "host2"} <= nodes
