"""
examples/demo_network_analysis.py
Network analysis demo with Visualizer integration.
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import numpy as np
import networkx as nx

from mcm_d_heuristics_v3_3.network_algo import NetworkSolver
from mcm_d_heuristics_v3_3.viz import Visualizer


def main() -> None:
    G_raw = nx.random_geometric_graph(20, 0.3)
    for (u, v) in G_raw.edges():
        G_raw.edges[u, v]["weight"] = np.random.randint(5, 50)

    solver = NetworkSolver(G_raw, directed=False)

    print(">>> Calculating Centralities...")
    top_nodes = solver.calculate_centralities(top_k=20)
    print(top_nodes)

    print("\n>>> Calculating MST...")
    mst_graph, mst_cost = solver.get_mst()
    print(f"Total MST Cost: {mst_cost}")

    node_vals = top_nodes["Betweenness"].to_dict()
    highlight_edges = list(mst_graph.edges())

    Visualizer.plot_network_analysis(
        solver.G,
        node_values=node_vals,
        highlight_edges=highlight_edges,
        title="Network Backbone & Critical Nodes",
    )


if __name__ == "__main__":
    main()
