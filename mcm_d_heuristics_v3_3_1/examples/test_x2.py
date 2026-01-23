"""
examples/test_x2.py
Checklist: 算法类在“不改内部代码”的情况下，能否解决 min f(x)=x^2 ？
这里用 1D 连续优化验证 PSO / GA(real) / SA(gaussian) 都能跑通。
"""
import os
import sys

# Allow running this file directly without installing the package
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import numpy as np

from mcm_d_heuristics_v3_3 import OptimizationProblem, Penalty
from mcm_d_heuristics_v3_3.pso import ParticleSwarmOptimizer, PSOConfig
from mcm_d_heuristics_v3_3.ga import GeneticAlgorithm, GAConfig
from mcm_d_heuristics_v3_3.sa import SimulatedAnnealing, SAConfig, op_gaussian
from mcm_d_heuristics_v3_3.viz import plot_convergence


def objective(sol: np.ndarray) -> float:
    x = float(np.asarray(sol).reshape(-1)[0])
    return x * x


problem = OptimizationProblem(
    objective=objective,
    decoder=None,  # identity
    constraints=[],
    penalty=Penalty(weight=1e9),
    lb=np.array([-10.0]),
    ub=np.array([+10.0]),
)

# ---- PSO ----
pso = ParticleSwarmOptimizer(problem, PSOConfig(num_particles=30, max_iter=80, seed=1))
best_sol_pso, best_cost_pso = pso.run()
print("[PSO] best_sol:", best_sol_pso, "best_cost:", best_cost_pso)
plot_convergence(pso.history_best, "PSO on x^2")

# ---- GA (real) ----
ga = GeneticAlgorithm(problem, GAConfig(encoding="real", n_genes=1, lb=np.array([-10.0]), ub=np.array([10.0]),
                                       n_pop=80, max_gen=120, elitism_k=2, seed=2))
best_sol_ga, best_cost_ga = ga.run()
print("[GA-real] best_sol:", best_sol_ga, "best_cost:", best_cost_ga)
plot_convergence(ga.history_best, "GA(real) on x^2")

# ---- SA (gaussian) ----
def init_sol(rng: np.random.Generator):
    return rng.uniform(-10.0, 10.0, size=(1,))

sa = SimulatedAnnealing(problem, init_sol, neighbor_ops=[lambda s, rng: op_gaussian(s, rng, sigma=0.5)],
                        config=SAConfig(T_start=10.0, T_end=1e-3, alpha=0.95, iters_per_T=30, seed=3))
best_sol_sa, best_cost_sa = sa.run()
print("[SA] best_sol:", best_sol_sa, "best_cost:", best_cost_sa)
plot_convergence(sa.history_best, "SA on x^2")
