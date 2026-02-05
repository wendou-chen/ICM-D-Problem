"""
pso.py
通用 PSO（支持连续/离散：离散通过 problem.decoder 实现）。
- 解耦 objective/constraints：全部由 OptimizationProblem 提供 evaluate_position()
- 支持 gbest / ring-lbest
- 自适应参数：w线性递减 + c1递减/c2递增（可关闭）
- 速度上限 + 反射边界
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Literal, Optional, Tuple

import numpy as np
import sys

from .problem import OptimizationProblem

try:
    from tqdm import tqdm
except Exception:  # pragma: no cover
    tqdm = None


def _linear_schedule(t: int, T: int, start: float, end: float) -> float:
    if T <= 1:
        return float(end)
    return float(start + (end - start) * (t / (T - 1)))


def _reflect_bounds(X: np.ndarray, V: np.ndarray, lb: np.ndarray, ub: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    for d in range(X.shape[1]):
        low, high = lb[d], ub[d]

        mask = X[:, d] < low
        if np.any(mask):
            X[mask, d] = low + (low - X[mask, d])
            V[mask, d] *= -1.0

        mask = X[:, d] > high
        if np.any(mask):
            X[mask, d] = high - (X[mask, d] - high)
            V[mask, d] *= -1.0

        X[:, d] = np.clip(X[:, d], low, high)

    return X, V


def _ring_lbest(p_best: np.ndarray, p_best_scores: np.ndarray) -> np.ndarray:
    N = p_best.shape[0]
    idx = np.arange(N)
    neigh = np.stack([(idx - 1) % N, idx, (idx + 1) % N], axis=1)  # (N,3)
    neigh_scores = p_best_scores[neigh]  # (N,3)
    best_j = np.argmin(neigh_scores, axis=1)  # (N,)
    best_idx = neigh[idx, best_j]  # (N,)
    return p_best[best_idx]


@dataclass
class PSOConfig:
    num_particles: int = 40
    max_iter: int = 200
    topology: Literal["gbest", "lbest"] = "gbest"
    adaptive: bool = True
    enable_progress_bar: bool = False
    progress_position: Optional[int] = None
    progress_leave: bool = False

    # inertia and acceleration
    w_max: float = 0.9
    w_min: float = 0.4
    c1_max: float = 2.5
    c1_min: float = 0.5
    c2_min: float = 0.5
    c2_max: float = 2.5

    # velocity clamp: fraction of (ub-lb)
    v_clamp_frac: float = 0.2

    seed: Optional[int] = 7


class ParticleSwarmOptimizer:
    def __init__(self, problem: OptimizationProblem, config: PSOConfig):
        problem.check_bounds()
        if problem.lb is None or problem.ub is None:
            raise ValueError("PSO requires problem.lb and problem.ub for position bounds.")
        self.problem = problem
        self.cfg = config
        self.rng = np.random.default_rng(config.seed)

        self.history_best: list[float] = []
        self.best_position: Optional[np.ndarray] = None
        self.best_solution = None
        self.best_cost: float = float("inf")

    def _init_swarm(self) -> Tuple[np.ndarray, np.ndarray]:
        lb = np.asarray(self.problem.lb, dtype=float).reshape(-1)
        ub = np.asarray(self.problem.ub, dtype=float).reshape(-1)
        D = lb.size

        X = self.rng.uniform(lb, ub, (self.cfg.num_particles, D))
        v_max = self.cfg.v_clamp_frac * (ub - lb)
        # Avoid zero v_max on fixed dims
        v_max = np.where(v_max <= 1e-12, 1.0, v_max)
        V = self.rng.uniform(-v_max, v_max, (self.cfg.num_particles, D))
        return X, V

    def run(self, step_callback: Optional[Callable[..., None]] = None) -> Tuple[object, float]:
        lb = np.asarray(self.problem.lb, dtype=float).reshape(-1)
        ub = np.asarray(self.problem.ub, dtype=float).reshape(-1)

        X, V = self._init_swarm()
        p_best = X.copy()
        eval_pos = None if self.cfg.progress_position is None else self.cfg.progress_position + 1

        # Initial particle evaluation
        if self.cfg.enable_progress_bar and tqdm is not None:
            p_best_scores = np.array(
                [
                    self.problem.evaluate_position(x)
                    for x in tqdm(
                        X,
                        desc="PSO init",
                        file=sys.stderr,
                        leave=self.cfg.progress_leave,
                        position=eval_pos,
                        dynamic_ncols=True,
                        mininterval=0.5,
                    )
                ],
                dtype=float,
            )
        else:
            p_best_scores = np.array([self.problem.evaluate_position(x) for x in X], dtype=float)

        g_idx = int(np.argmin(p_best_scores))
        g_best = p_best[g_idx].copy()
        g_best_score = float(p_best_scores[g_idx])

        self.history_best = [g_best_score]
        self.history_solutions = [self.problem.decode(g_best)]  # Record decoded solution
        self.best_position = g_best.copy()
        self.best_solution = self.problem.decode(g_best)
        self.best_cost = g_best_score

        v_max = self.cfg.v_clamp_frac * (ub - lb)
        v_max = np.where(v_max <= 1e-12, 1.0, v_max)

        iter_range = range(self.cfg.max_iter)
        pbar = None
        if self.cfg.enable_progress_bar and tqdm is not None:
            pbar = tqdm(
                total=self.cfg.max_iter,
                desc=f"PSO best={self.best_cost:.4f}",
                disable=False,
                file=sys.stderr,
                dynamic_ncols=True,
                mininterval=0.0,
                miniters=1,
                leave=True,
                position=self.cfg.progress_position,
            )

        for t in iter_range:
            if self.cfg.adaptive:
                w = _linear_schedule(t, self.cfg.max_iter, self.cfg.w_max, self.cfg.w_min)
                c1 = _linear_schedule(t, self.cfg.max_iter, self.cfg.c1_max, self.cfg.c1_min)
                c2 = _linear_schedule(t, self.cfg.max_iter, self.cfg.c2_min, self.cfg.c2_max)
            else:
                w = self.cfg.w_min
                c1, c2 = 2.0, 2.0

            if self.cfg.topology == "lbest":
                social_best = _ring_lbest(p_best, p_best_scores)
            else:
                social_best = g_best[None, :]

            r1 = self.rng.random(X.shape)
            r2 = self.rng.random(X.shape)

            V = w * V + c1 * r1 * (p_best - X) + c2 * r2 * (social_best - X)
            V = np.clip(V, -v_max, v_max)

            X = X + V
            X, V = _reflect_bounds(X, V, lb, ub)

            # Particle evaluation
            if self.cfg.enable_progress_bar and tqdm is not None:
                scores = np.array(
                    [
                        self.problem.evaluate_position(x)
                        for x in tqdm(
                            X,
                            desc=f"PSO iter {t+1}/{self.cfg.max_iter}",
                            file=sys.stderr,
                            leave=self.cfg.progress_leave,
                            position=eval_pos,
                            dynamic_ncols=True,
                            mininterval=0.5,
                        )
                    ],
                    dtype=float,
                )
            else:
                scores = np.array([self.problem.evaluate_position(x) for x in X], dtype=float)
            avg_cost = float(np.mean(scores)) if scores.size else float("nan")
            diversity = float(np.std(scores)) if scores.size else float("nan")

            improved = scores < p_best_scores
            p_best[improved] = X[improved]
            p_best_scores[improved] = scores[improved]

            min_idx = int(np.argmin(p_best_scores))
            if float(p_best_scores[min_idx]) < g_best_score:
                g_best = p_best[min_idx].copy()
                g_best_score = float(p_best_scores[min_idx])

                self.best_position = g_best.copy()
                self.best_solution = self.problem.decode(g_best)
                self.best_cost = g_best_score

            self.history_best.append(self.best_cost)
            self.history_solutions.append(self.best_solution) # Append best solution at this step
            if pbar is not None:
                pbar.set_description(f"PSO best={self.best_cost:.4f}")
                pbar.update(1)
            if step_callback is not None:
                step_callback(
                    current_iter=t,
                    best_cost=float(self.best_cost),
                    avg_cost=avg_cost,
                    diversity=diversity,
                    phase="PSO",
                )

        if pbar is not None:
            pbar.close()

        return self.best_solution, self.best_cost
