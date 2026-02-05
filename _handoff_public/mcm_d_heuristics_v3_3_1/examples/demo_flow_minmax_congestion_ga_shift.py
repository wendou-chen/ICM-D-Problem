"""\
Example: Min-Max congestion (load balancing) using GA + domain-specific flow shifting.

This example demonstrates a contest-grade trick for min-max flow objectives:
- Decision variables: x_p = flow on candidate path p (path-based formulation).
- Demands are treated as hard requirements.
- Objective: minimize max_e load_e(x)/cap_e.

To speed up convergence, we inject a domain-specific mutation operator:
  op_congestion_shift(...)
which directly targets the current bottleneck edge.
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import numpy as np
import networkx as nx

from mcm_d_heuristics_v3_3 import GAConfig, GeneticAlgorithm
from mcm_d_heuristics_v3_3.flow import (
    Commodity,
    build_path_flow_model,
    make_min_max_congestion_problem,
    op_congestion_shift,
)


def main() -> None:
    # Build a directed graph with (weight, capacity)
    G = nx.DiGraph()
    edges = [
        (0, 1, 1.0, 6.0),
        (0, 2, 1.0, 6.0),
        (1, 3, 1.0, 4.0),
        (2, 3, 1.0, 4.0),
        (1, 2, 0.2, 2.0),
        (2, 1, 0.2, 2.0),
    ]
    for u, v, w, c in edges:
        G.add_edge(u, v, weight=w, capacity=c)

    # Two commodities compete for shared capacity
    commodities = [
        Commodity(0, 3, demand=5.0, name="A"),
        Commodity(0, 3, demand=5.0, name="B"),
    ]

    model = build_path_flow_model(G, commodities, k_paths=8, weight_attr="weight", capacity_attr="capacity")
    if model.n_paths == 0:
        raise RuntimeError("No candidate paths found.")

    problem = make_min_max_congestion_problem(model, penalty_weight=1e6, overload_penalty=0.0)

    lb = np.zeros(model.n_paths, dtype=float)
    ub = np.array([model.commodities[m].demand for m in model.path_commodity], dtype=float)

    # Domain-specific operator + stagnation trigger (defibrillator)
    cfg = GAConfig(
        encoding="real",
        n_pop=140,
        max_gen=250,
        cx_rate=0.9,
        mut_rate=0.15,
        elitism_k=4,
        tournament_k=3,
        seed=11,
        n_genes=model.n_paths,
        lb=lb,
        ub=ub,
        # keep early-stage expensive calls low
        custom_mutation_prob=0.02,
        custom_mutation=lambda genome, rng: op_congestion_shift(genome, model, rng, shift_ratio=0.10, max_tries=12),
        # stagnation trigger (contest-grade)
        stagnation_patience=12,
        stagnation_tol=1e-8,
        stagnation_reset=True,
        stagnation_elite_fraction=1.0,
        stagnation_aggressive_steps=2,
        custom_mutation_aggressive=lambda genome, rng: op_congestion_shift(
            genome, model, rng, shift_ratio=0.20, max_tries=25
        ),
    )

    ga = GeneticAlgorithm(problem, cfg)
    best_x, best_cost = ga.run()

    best_x = np.asarray(best_x, dtype=float)
    best_x = model.repair_demand_only(best_x)

    loads = model.edge_loads(best_x)
    caps = model.capacities
    util = np.zeros_like(loads)
    ok = np.isfinite(caps) & (caps > 1e-12)
    util[ok] = loads[ok] / caps[ok]
    worst = float(np.max(util)) if util.size else 0.0

    print("Best min-max congestion objective:", best_cost)
    print("Worst utilization (recomputed):", worst)
    print("Path flows:")
    for p, x in enumerate(best_x):
        if x > 1e-6:
            print(f"  path#{p} (comm={model.path_commodity[p]}): {x:.3f}  {model.paths[p]}")
    print(f"Max utilization: {util.max():.2%}")

    # --- 新增可视化 ---
    import mcm_d_heuristics_v3_3.viz as viz

    # 1) 收敛曲线
    viz.plot_convergence(
        ga.history_best,
        title="Min-Max Congestion GA (with Shift Operator)",
    )

    # 2) 拥塞边高亮（通用汇总：由 paths+flows 计算 edge_flow）
    edge_flow = {}
    for p, x in enumerate(best_x):
        if x <= 1e-6:
            continue
        path = model.paths[p]
        for u, v in zip(path[:-1], path[1:]):
            edge_flow[(u, v)] = edge_flow.get((u, v), 0.0) + float(x)

    congested_edges = []
    for (u, v), load in edge_flow.items():
        cap = float(G[u][v].get("capacity", np.inf))
        if np.isfinite(cap) and cap > 1e-9 and (load / cap) > 0.8:
            congested_edges.append((u, v))

    # 注意：不要在外部 plt.figure()/plt.show()，viz.draw_network 内部会托管 figure+show
    pos = nx.spring_layout(G, seed=12)
    viz.draw_network(
        list(G.edges(data="weight", default=1.0)),
        pos=pos,
        highlight_edges=congested_edges,
        title="Congestion Heatmap (Red edges: Util > 80%)",
    )

    # --- export (append-only) ---
    import time
    from src.exporters import export_metrics_row, export_solution_flows

    run_id_str = time.strftime("flow_minmax_%Y%m%d_%H%M%S")
    export_metrics_row({
        "run_id": run_id_str,
        "method": "GA_MinMaxCong",
        "objective": float(best_cost),
        "total_cost": float(np.dot(best_x, model.path_costs)),
        "max_congestion": float(worst),
        "makespan": None,
        "resilience_score": None,
        "feasible": bool(float(worst) <= 1.0 + 1e-6),
        "runtime_sec": None,
        "seed": getattr(cfg, "seed", None),
        "note": "",
    })

    export_solution_flows(G, flow=edge_flow, capacity=None, out_csv="outputs/exports/solution_flows.csv")


if __name__ == "__main__":
    main()
