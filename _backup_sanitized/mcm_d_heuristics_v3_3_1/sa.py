"""
sa.py
通用模拟退火（SA），支持多邻域算子（随机选择）。
- 目标/约束由 OptimizationProblem 注入
- 邻域算子 neighbor_ops: List[Callable[[solution, rng], new_solution]]
- 支持“解修复”(repair)可在 problem.decoder 或 objective 内处理；这里保持纯净。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, List, Optional, Tuple

import numpy as np

from .problem import OptimizationProblem


NeighborOp = Callable[[object, np.random.Generator], object]


@dataclass
class SAConfig:
    T_start: float = 50.0
    T_end: float = 1e-3
    alpha: float = 0.98
    iters_per_T: int = 50
    seed: Optional[int] = 42


# ----------------- common neighborhood operators -----------------

def op_swap(sol: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    y = sol.copy()
    n = len(y)
    i, j = rng.integers(0, n, size=2)
    y[i], y[j] = y[j], y[i]
    return y


def op_insert(sol: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    y = sol.copy()
    n = len(y)
    i, j = rng.integers(0, n, size=2)
    if i == j:
        return y
    node = y[i]
    y = np.delete(y, i)
    y = np.insert(y, j, node)
    return y


def op_reverse(sol: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    y = sol.copy()
    n = len(y)
    a, b = sorted(rng.integers(0, n, size=2))
    y[a:b] = y[a:b][::-1]
    return y


def op_gaussian(sol: np.ndarray, rng: np.random.Generator, sigma: float = 0.1) -> np.ndarray:
    y = np.asarray(sol, dtype=float).copy()
    y = y + rng.normal(0.0, sigma, size=y.shape)
    return y


class SimulatedAnnealing:
    def __init__(
        self,
        problem: OptimizationProblem,
        init_solution: Callable[[np.random.Generator], object],
        neighbor_ops: List[NeighborOp],
        config: SAConfig,
    ):
        if not neighbor_ops:
            raise ValueError("neighbor_ops must be non-empty.")
        self.problem = problem
        self.init_solution_fn = init_solution
        self.neighbor_ops = neighbor_ops
        self.cfg = config
        self.rng = np.random.default_rng(config.seed)

        self.history_best: list[float] = []
        self.best_solution = None
        self.best_cost: float = float("inf")

    def run(self) -> Tuple[object, float]:
        sol = self.init_solution_fn(self.rng)
        cost = self.problem.evaluate_solution(sol)

        best_sol = sol
        best_cost = float(cost)

        T = float(self.cfg.T_start)
        self.history_best = [best_cost]

        while T > self.cfg.T_end:
            for _ in range(self.cfg.iters_per_T):
                op = self.neighbor_ops[int(self.rng.integers(0, len(self.neighbor_ops)))]
                cand = op(sol, self.rng)
                cand_cost = self.problem.evaluate_solution(cand)

                delta = float(cand_cost - cost)
                if delta < 0:
                    sol, cost = cand, cand_cost
                else:
                    if self.rng.random() < np.exp(-delta / T):
                        sol, cost = cand, cand_cost

                if float(cost) < best_cost:
                    best_cost = float(cost)
                    best_sol = sol

            T *= self.cfg.alpha
            self.history_best.append(best_cost)

        self.best_solution = best_sol
        self.best_cost = best_cost
        return best_sol, best_cost
