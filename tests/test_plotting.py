"""Tests for the topology graph builders and figure in common/plotting.py."""

from types import SimpleNamespace

import networkx as nx
import pandas as pd

from common import plotting as PL


def iface(host, name, as_dict):
    return (
        {"hostname": host, "interface": name}
        if as_dict
        else SimpleNamespace(hostname=host, interface=name)
    )


def test_get_topology_accepts_dict_and_object_interfaces():
    edges = pd.DataFrame(
        {
            "Interface": [iface("r1", "Gi0", True), iface("r2", "Gi1", False)],
            "Remote_Interface": [iface("r2", "Gi0", False), iface("r3", "Gi2", True)],
        }
    )
    g = PL.get_topology(edges)
    assert sorted(g.nodes) == ["r1", "r2", "r3"]
    assert g.edges["r1", "r2"]["title"] == "r1 (Gi0) <---> r2 (Gi0)"
    assert g.edges["r2", "r3"]["title"] == "r2 (Gi1) <---> r3 (Gi2)"


def test_get_topology_merges_parallel_links_between_the_same_nodes():
    edges = pd.DataFrame(
        {
            "Interface": [iface("r1", "Gi0", True), iface("r2", "Gi1", True)],
            "Remote_Interface": [iface("r2", "Gi0", True), iface("r1", "Gi1", True)],
        }
    )
    assert PL.get_topology(edges).number_of_edges() == 1


def test_get_topology_of_no_edges_is_empty():
    g = PL.get_topology(pd.DataFrame({"Interface": [], "Remote_Interface": []}))
    assert g.number_of_nodes() == 0


def test_get_routing_topology_uses_node_columns():
    edges = pd.DataFrame({"Node": ["a", "b", "a"], "Remote_Node": ["b", "a", "c"]})
    g = PL.get_routing_topology(edges)
    assert sorted(g.nodes) == ["a", "b", "c"]
    assert g.number_of_edges() == 2  # a-b listed twice, counted once


def test_plot_plotly_draws_edges_then_labelled_nodes():
    fig = PL.plot_plotly(nx.Graph([("a", "b"), ("b", "c")]))
    edges, nodes = fig.data
    assert edges.mode == "lines" and nodes.mode == "markers+text"
    assert list(nodes.text) == ["<b>a</b>", "<b>b</b>", "<b>c</b>"]
    assert len(nodes.x) == 3
    # each edge is x0, x1, None
    assert len(edges.x) == 6 and edges.x[2] is None and edges.x[5] is None
    assert fig.layout.showlegend is False


def test_plot_plotly_layout_is_stable_between_runs():
    g = nx.Graph([("a", "b"), ("b", "c")])
    first, second = PL.plot_plotly(g), PL.plot_plotly(g)
    assert list(first.data[1].x) == list(second.data[1].x)
    assert list(first.data[1].y) == list(second.data[1].y)


def test_plot_plotly_of_an_empty_graph_still_returns_a_figure():
    fig = PL.plot_plotly(nx.Graph())
    assert len(fig.data) == 2 and len(fig.data[1].x) == 0
