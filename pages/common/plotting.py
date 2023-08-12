# -*- coding: utf-8 -*-
"""
Copyright 2023 Maen Artimy

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
import matplotlib.pyplot as plt


def get_topology(edges):

    g = nx.Graph()

    l3edges_json = json.loads(edges.to_json(orient="index"))
    for k in l3edges_json:
        neighbor = l3edges_json[k]
        node_id = neighbor["Interface"]["hostname"]
        remote_node_id = neighbor["Remote_Interface"]["hostname"]
        g.add_edge(node_id, remote_node_id)

    return g


def get_figure(pframe):
    """
    Plots Pandas data frame

    """
    g = get_topology(pframe)

    # Calculate spring layout
    pos = nx.spring_layout(g)

    # Draw the graph using matplotlib within Streamlit
    fig, ax = plt.subplots()
    nx.draw(g, pos, with_labels=True, ax=ax, node_size=1000, font_color="white")

    return fig
