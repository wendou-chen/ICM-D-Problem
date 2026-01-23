"""
Example: Path-based min-cost flow using GA (real encoding).

This demonstrates how to avoid edge-flow encoding by optimizing flows on a small set
of candidate s-t paths. Flow conservation is satisfied by construction; a repair
operator enforces capacities and tries to meet demands.
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import numpy as np
import networkx as nx

from mcm_d_heuristics_v3_3 import GAConfig, GeneticAlgorithm
from mcm_d_heuristics_v3_3.flow import Commodity, build_path_flow_model, make_min_cost_flow_problem


def main() -> None:
    # Build a directed graph with (weight, capacity)
    G = nx.DiGraph()
    edges = [
        (0, 1, 2.0, 8.0),
        (0, 2, 2.5, 6.0),
        (1, 3, 2.0, 5.0),
        (2, 3, 1.0, 6.0),
        (1, 2, 0.5, 3.0),
    ]
    for u, v, w, c in edges:
        G.add_edge(u, v, weight=w, capacity=c)

    commodities = [Commodity(0, 3, demand=9.0, name="0->3")]
    model = build_path_flow_model(G, commodities, k_paths=10, weight_attr="weight", capacity_attr="capacity")
    if model.n_paths == 0:
        raise RuntimeError("No candidate paths found.")

    problem = make_min_cost_flow_problem(model, unmet_penalty=1e5, meet_demands_in_repair=True)

    # GA real encoding: x_p in [0, demand_of_commodity(p)]
    lb = np.zeros(model.n_paths, dtype=float)
    ub = np.array([model.commodities[m].demand for m in model.path_commodity], dtype=float)

    cfg = GAConfig(
        encoding="real",
        n_pop=120,
        max_gen=200,
        cx_rate=0.9,
        mut_rate=0.2,
        elitism_k=3,
        tournament_k=3,
        seed=7,
        n_genes=model.n_paths,
        lb=lb,
        ub=ub,
    )

    ga = GeneticAlgorithm(problem, cfg)
    best_x, best_cost = ga.run()

    best_x = np.asarray(best_x, dtype=float)
    best_x = model.repair(best_x, meet_demands=True)
    print("Best objective:", best_cost)
    print("Path flows:")
    for p, x in enumerate(best_x):
        if x > 1e-6:
            print(
                f"  path#{p} (comm={model.path_commodity[p]} cost={model.path_costs[p]:.2f}): "
                f"{x:.3f}  {model.paths[p]}"
            )
    cap_vio = model.capacity_violation(best_x)
    unmet = model.demand_violation(best_x)
    print("Capacity violation:", cap_vio)
    print(f"Unmet demand: {unmet:.4f}")

    # --- 新增可视化 ---
    import mcm_d_heuristics_v3_3.viz as viz

    # 1) 收敛曲线：使用 ga.history_best（而非 ga.history）
    viz.plot_convergence(ga.history_best, title="Min-Cost Flow GA Convergence")

    # 2) 网络图：高亮有流量的边（通用做法：由 paths+flows 汇总 edge_flow）
    edge_flow = {}
    for p, x in enumerate(best_x):
        if x <= 1e-6:
            continue
        path = model.paths[p]
        for u, v in zip(path[:-1], path[1:]):
            edge_flow[(u, v)] = edge_flow.get((u, v), 0.0) + float(x)

    active_edges = [e for e, f in edge_flow.items() if f > 1e-6]
    edge_values = {}
    for (u, v), load in edge_flow.items():
        cap = float(G[u][v].get("capacity", np.inf))
        if np.isfinite(cap) and cap > 1e-9:
            edge_values[(u, v)] = load / cap

    # 注意：不要在外部 plt.figure()/plt.show()，viz.draw_network 内部会托管 figure+show
    pos = nx.spring_layout(G, seed=42)
    viz.draw_network(
        list(G.edges(data="weight", default=1.0)),
        pos=pos,
        highlight_edges=active_edges,
        edge_values=edge_values,
        title="Optimized Path Flows (Active Edges Highlighted)",
    )

    # --- export (append-only) ---
    import time
    from src.exporters import export_metrics_row, export_solution_flows

    max_cong = 0.0
    for (u, v), load in edge_flow.items():
        cap = float(G[u][v].get("capacity", np.inf))
        if np.isfinite(cap) and cap > 1e-12:
            max_cong = max(max_cong, float(load) / cap)

    run_id_str = time.strftime("flow_mincost_%Y%m%d_%H%M%S")
    export_metrics_row({
        "run_id": run_id_str,
        "method": "GA_MinCost",
        "objective": float(best_cost),
        "total_cost": float(np.dot(best_x, model.path_costs)),
        "max_congestion": float(max_cong),
        "makespan": None,
        "resilience_score": None,
        "feasible": bool((cap_vio <= 1e-6) and (unmet <= 1e-6)),
        "runtime_sec": None,
        "seed": getattr(cfg, "seed", None),
        "note": "",
    })

    export_solution_flows(G, flow=edge_flow, capacity=None, out_csv="outputs/exports/solution_flows.csv")


if __name__ == "__main__":
    main()
