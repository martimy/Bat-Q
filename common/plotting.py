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

import json
import networkx as nx

# import matplotlib.pyplot as plt
# from pyvis.network import Network
# import streamlit.components.v1 as components # replace with st.iframe
import plotly.graph_objects as go

# def get_topology(edges):
#     g = nx.Graph()
#     l3edges_json = json.loads(edges.to_json(orient="index"))
#     for k in l3edges_json:
#         neighbor = l3edges_json[k]
#         node_id = neighbor["Interface"]["hostname"]
#         remote_node_id = neighbor["Remote_Interface"]["hostname"]
#         g.add_edge(node_id, remote_node_id)
#     return g


def get_topology(edges):
    g = nx.Graph()
    # Iterate DataFrame rows directly instead of JSON serialization
    for row in edges.itertuples():
        src = (
            row.Interface["hostname"]
            if isinstance(row.Interface, dict)
            else row.Interface.hostname
        )
        dst = (
            row.Remote_Interface["hostname"]
            if isinstance(row.Remote_Interface, dict)
            else row.Remote_Interface.hostname
        )

        src_iface = (
            row.Interface.get("interface", "")
            if isinstance(row.Interface, dict)
            else getattr(row.Interface, "interface", "")
        )
        dst_iface = (
            row.Remote_Interface.get("interface", "")
            if isinstance(row.Remote_Interface, dict)
            else getattr(row.Remote_Interface, "interface", "")
        )

        g.add_edge(src, dst, title=f"{src} ({src_iface}) <---> {dst} ({dst_iface})")
    return g


def get_routing_topology(edges):
    g = nx.Graph()
    l3edges_json = json.loads(edges.to_json(orient="index"))
    for k in l3edges_json:
        neighbor = l3edges_json[k]
        node_id = neighbor["Node"]
        remote_node_id = neighbor["Remote_Node"]
        g.add_edge(node_id, remote_node_id)
    return g


# def plot_figure(g):
#     """
#     Plots Pandas data frame topology graph.
#     """
#     pos = nx.spring_layout(g)
#     fig, ax = plt.subplots(figsize=(6, 4))
#     nx.draw(g, pos, with_labels=True, ax=ax, node_size=1000, font_color="white")
#     return fig

# def plot_pyvis(g, height="450px"):
#     net = Network(height=height, width="100%", bgcolor="#0e1117", font_color="white", notebook=False)
#     net.from_nx(g)

#     # Physics settings for smooth node separation
#     net.barnes_hut(gravity=-3000, central_gravity=0.3, spring_length=100)

#     # Render physics toggle & generate HTML
#     net.toggle_physics(True)
#     html_str = net.generate_html()

#     # Display directly in Streamlit
#     components.html(html_str, height=470, scrolling=False)


def plot_plotly(g):
    pos = nx.spring_layout(g, seed=42)

    # Draw Edges
    edge_x, edge_y = [], []
    for edge in g.edges():
        x0, y0 = pos[edge[0]]
        x1, y1 = pos[edge[1]]
        edge_x.extend([x0, x1, None])
        edge_y.extend([y0, y1, None])

    edge_trace = go.Scatter(
        x=edge_x,
        y=edge_y,
        line=dict(width=1.5, color="#888"),
        hoverinfo="none",
        mode="lines",
    )

    # Draw Nodes
    node_x = [pos[node][0] for node in g.nodes()]
    node_y = [pos[node][1] for node in g.nodes()]
    node_text = [f"<b>{node}</b>" for node in g.nodes()]

    node_trace = go.Scatter(
        x=node_x,
        y=node_y,
        mode="markers+text",
        text=node_text,
        textposition="top center",
        hoverinfo="text",
        marker=dict(size=24, color="#0068c9", line=dict(width=2, color="white")),
    )

    fig = go.Figure(
        data=[edge_trace, node_trace],
        layout=go.Layout(
            showlegend=False,
            margin=dict(b=10, l=10, r=10, t=10),
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        ),
    )
    return fig
