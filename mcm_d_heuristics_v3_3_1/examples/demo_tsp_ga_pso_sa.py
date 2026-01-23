"""
examples/demo_tsp_ga_pso_sa.py
TSP/巡检类（排列决策）示例：同一 objective/constraints，替换 GA/PSO/SA 直接跑。
- GA: permutation encoding
- PSO: random-keys decode -> permutation
- SA: 多邻域算子 swap/insert/reverse

这就是 D题“架构解耦”的最小可复用例子。
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import numpy as np

from mcm_d_heuristics_v3_3 import OptimizationProblem, Penalty
from mcm_d_heuristics_v3_3.problem import decode_random_keys_to_permutation
from mcm_d_heuristics_v3_3.ga import GeneticAlgorithm, GAConfig
from mcm_d_heuristics_v3_3.pso import ParticleSwarmOptimizer, PSOConfig
from mcm_d_heuristics_v3_3.sa import SimulatedAnnealing, SAConfig, op_swap, op_insert, op_reverse
from mcm_d_heuristics_v3_3.viz import Visualizer

np.random.seed(0)

N = 30
coords = np.random.rand(N, 2)

dist = np.zeros((N, N))
for i in range(N):
    for j in range(N):
        dist[i, j] = np.linalg.norm(coords[i] - coords[j])


def route_cost(route: np.ndarray) -> float:
    r = np.asarray(route, dtype=int).reshape(-1)
    s = 0.0
    for k in range(N - 1):
        s += dist[r[k], r[k + 1]]
    s += dist[r[-1], r[0]]
    return float(s)


problem_perm = OptimizationProblem(
    objective=route_cost,
    decoder=None,  # GA/SA already operate on permutation as solution
    constraints=[],
    penalty=Penalty(weight=1e9),
)

# ---------- GA ----------
ga = GeneticAlgorithm(problem_perm, GAConfig(encoding="permutation", perm_size=N, n_pop=160, max_gen=250,
                                            cx_rate=0.9, mut_rate=0.05, elitism_k=3, seed=1))
best_route_ga, best_cost_ga = ga.run()
print("[GA] best_cost:", best_cost_ga)

# ---------- PSO via Random-Keys ----------
# PSO searches in R^N, decode by argsort -> permutation
problem_rk = OptimizationProblem(
    objective=route_cost,
    decoder=decode_random_keys_to_permutation,
    constraints=[],
    penalty=Penalty(weight=1e9),
    lb=np.zeros(N),
    ub=np.ones(N),
)

pso = ParticleSwarmOptimizer(problem_rk, PSOConfig(num_particles=60, max_iter=220, topology="lbest",
                                                  adaptive=True, v_clamp_frac=0.3, seed=2))
best_route_pso, best_cost_pso = pso.run()
print("[PSO-RK] best_cost:", best_cost_pso)

# ---------- SA ----------
def init_route(rng: np.random.Generator):
    return rng.permutation(N)

sa = SimulatedAnnealing(problem_perm, init_route, neighbor_ops=[op_swap, op_insert, op_reverse],
                        config=SAConfig(T_start=10.0, T_end=1e-3, alpha=0.97, iters_per_T=80, seed=3))
best_route_sa, best_cost_sa = sa.run()
print("[SA] best_cost:", best_cost_sa)

histories = {
    "PSO (Particle Swarm)": pso.history_best,
    "GA (Genetic Algo)": ga.history_best,
    "SA (Simulated Annealing)": sa.history_best,
}

Visualizer.plot_convergence(
    histories,
    title="TSP Optimization: Algorithm Comparison",
    ylabel="Total Distance (km)",
)

# --- export (append-only) ---
import time
from src.exporters import export_metrics_row

run_id_base = time.strftime("tsp_%Y%m%d_%H%M%S")
export_metrics_row({
    "run_id": f"{run_id_base}_GA",
    "method": "GA_TSP",
    "objective": float(best_cost_ga),
    "total_cost": float(best_cost_ga),
    "max_congestion": None,
    "makespan": None,
    "resilience_score": None,
    "feasible": True,
    "runtime_sec": None,
    "seed": 1,
    "note": "",
})
export_metrics_row({
    "run_id": f"{run_id_base}_PSO",
    "method": "PSO_TSP",
    "objective": float(best_cost_pso),
    "total_cost": float(best_cost_pso),
    "max_congestion": None,
    "makespan": None,
    "resilience_score": None,
    "feasible": True,
    "runtime_sec": None,
    "seed": 2,
    "note": "",
})
export_metrics_row({
    "run_id": f"{run_id_base}_SA",
    "method": "SA_TSP",
    "objective": float(best_cost_sa),
    "total_cost": float(best_cost_sa),
    "max_congestion": None,
    "makespan": None,
    "resilience_score": None,
    "feasible": True,
    "runtime_sec": None,
    "seed": 3,
    "note": "",
})
