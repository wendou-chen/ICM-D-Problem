"""
problem.py
A minimal, O奖级可复用的“问题-算法”解耦接口层。

核心思想：
- 算法只维护“搜索空间表示”(position/genotype)，通过 decoder 映射为“实际方案”(solution/phenotype)。
- 约束通过 violations + penalty 统一接入（大M / 自适应权重都可以扩展）。
- D题常见“不可行解占绝大多数”：提供可选的 repair 机制，在评估前把解映射回可行域/近可行域。
- 多目标（Multi-objective）：支持 weighted-sum 标量化，并提供轻量 ParetoArchive（可选）。

约定：
- minimize
- constraint g_k(solution) 返回 0 表示满足，>0 表示违反程度（越大越不可行）
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, List, Optional, Sequence, Tuple, Union

import numpy as np

Solution = Any
Position = Union[np.ndarray, Sequence[float]]

ObjectiveOut = Union[float, Sequence[float], np.ndarray]
ObjectiveFunc = Callable[[Solution], ObjectiveOut]
Decoder = Callable[[Position], Solution]
ConstraintFunc = Callable[[Solution], float]
RepairFunc = Callable[[Solution], Solution]


def _as_1d(x: Union[Sequence[float], np.ndarray]) -> np.ndarray:
    return np.asarray(x, dtype=float).reshape(-1)


@dataclass
class Penalty:
    """
    Big-M penalty. Default: penalty(v) = weight * v^power, only when v>0.
    """
    weight: float = 1e9
    power: float = 1.0

    def __call__(self, violation: float) -> float:
        if violation <= 0:
            return 0.0
        return float(self.weight * (float(violation) ** self.power))


def _dominates(a: np.ndarray, b: np.ndarray) -> bool:
    """Minimization dominance: a dominates b if a<=b elementwise and exists strict <."""
    return bool(np.all(a <= b) and np.any(a < b))


@dataclass
class ParetoArchive:
    """
    A lightweight Pareto archive for feasible solutions.
    Keeps a list of non-dominated (solution, obj_vector).

    Notes:
    - This is intentionally simple for contest use.
    - For large archives, consider crowding-distance truncation.
    """
    max_size: int = 200
    items: List[Tuple[Solution, np.ndarray]] = field(default_factory=list)

    def add(self, solution: Solution, obj_vector: np.ndarray) -> None:
        obj_vector = _as_1d(obj_vector)
        # Remove any items dominated by the new one; skip if new is dominated.
        new_items: List[Tuple[Solution, np.ndarray]] = []
        for sol, vec in self.items:
            if _dominates(vec, obj_vector):
                # existing dominates new -> discard new
                return
            if not _dominates(obj_vector, vec):
                new_items.append((sol, vec))
        new_items.append((solution, obj_vector))
        # Truncate if necessary (simple: keep best by sum)
        if len(new_items) > self.max_size:
            new_items.sort(key=lambda t: float(np.sum(t[1])))
            new_items = new_items[: self.max_size]
        self.items = new_items

    def __len__(self) -> int:
        return len(self.items)


@dataclass
class OptimizationProblem:
    """
    通用优化问题容器。

    Parameters
    ----------
    objective:
        f(solution) -> float or vector-like
    decoder:
        position -> solution（用于 PSO 等连续表示映射离散解）
    constraints:
        g_k(solution) -> violation >= 0
    penalty:
        penalty(violation) -> float
    repair:
        repair(solution) -> solution，用于把不可行解“拉回”可行域/近可行域
    weights:
        多目标标量化权重（仅当 objective 返回向量时需要）
    lb/ub:
        position 的边界（连续/整数/随机键等）
    """
    objective: ObjectiveFunc
    decoder: Optional[Decoder] = None
    constraints: List[ConstraintFunc] = field(default_factory=list)
    penalty: Penalty = field(default_factory=Penalty)
    repair: Optional[RepairFunc] = None
    weights: Optional[np.ndarray] = None
    lb: Optional[np.ndarray] = None
    ub: Optional[np.ndarray] = None

    # optional: store a Pareto archive for feasible solutions
    pareto_archive: Optional[ParetoArchive] = None

    def check_bounds(self) -> None:
        """Validate lb/ub bounds when provided."""
        if self.lb is None and self.ub is None:
            return
        if self.lb is None or self.ub is None:
            raise ValueError('Both lb and ub must be provided together.')
        lb = _as_1d(self.lb)
        ub = _as_1d(self.ub)
        if lb.size != ub.size:
            raise ValueError(f'lb size {lb.size} must match ub size {ub.size}.')
        if np.any(lb > ub):
            raise ValueError('Bounds must satisfy lb <= ub elementwise.')
        # store back as numpy arrays
        self.lb = lb
        self.ub = ub

    def decode(self, position: Position) -> Solution:
        if self.decoder is None:
            return position  # type: ignore
        return self.decoder(position)

    def repair_solution(self, solution: Solution) -> Solution:
        if self.repair is None:
            return solution
        return self.repair(solution)

    def violation(self, solution: Solution) -> float:
        if not self.constraints:
            return 0.0
        v = 0.0
        for g in self.constraints:
            val = float(g(solution))
            if val > 0:
                v += val
        return float(v)

    def objective_vector(self, solution: Solution) -> np.ndarray:
        out = self.objective(solution)
        if isinstance(out, (list, tuple, np.ndarray)) and not np.isscalar(out):
            return _as_1d(out)  # multi objective
        return np.asarray([float(out)], dtype=float)

    @property
    def is_multiobjective(self) -> bool:
        # cannot know without calling objective; keep soft check based on weights
        return self.weights is not None and _as_1d(self.weights).size > 1

    def scalarize(self, obj_vec: np.ndarray) -> float:
        obj_vec = _as_1d(obj_vec)
        if obj_vec.size == 1:
            return float(obj_vec[0])
        if self.weights is None:
            raise ValueError("Multi-objective detected but weights is None. Provide weights for weighted-sum scalarization.")
        w = _as_1d(self.weights)
        if w.size != obj_vec.size:
            raise ValueError(f"weights size {w.size} must match objective vector size {obj_vec.size}.")
        return float(np.dot(w, obj_vec))

    def evaluate_solution(
        self,
        solution: Solution,
        return_vector: bool = False,
        add_to_archive: bool = True,
    ) -> Union[float, Tuple[float, np.ndarray, float]]:
        """
        Evaluate solution with optional repair, constraints and penalty.

        Returns
        -------
        scalar_cost or (scalar_cost, obj_vector, violation)
        """
        sol = self.repair_solution(solution)
        v = self.violation(sol)
        obj_vec = self.objective_vector(sol)
        scalar_obj = self.scalarize(obj_vec)
        cost = scalar_obj + self.penalty(v)

        if add_to_archive and self.pareto_archive is not None and v <= 0:
            self.pareto_archive.add(sol, obj_vec)

        if return_vector:
            return cost, obj_vec, v
        return cost

    def evaluate_position(
        self,
        position: Position,
        return_vector: bool = False,
        add_to_archive: bool = True,
    ) -> Union[float, Tuple[float, np.ndarray, float]]:
        sol = self.decode(position)
        return self.evaluate_solution(sol, return_vector=return_vector, add_to_archive=add_to_archive)


# ------------------------ Ready-to-use decoders ------------------------

def decode_random_keys_to_permutation(position: Position) -> np.ndarray:
    """
    Random-Keys (排序索引) 映射：position 为连续向量 -> permutation。
    常用于离散 TSP/路径选择等：解码为 np.argsort(position)。
    """
    pos_arr = np.asarray(position).reshape(-1)
    return np.argsort(pos_arr)


def decode_sigmoid_to_binary(position: Position, threshold: float = 0.5) -> np.ndarray:
    """
    Sigmoid 映射：position -> (0/1)^D
    threshold=0.5 等价于 sigmoid(x) >= 0.5 <=> x >= 0
    """
    x = np.asarray(position, dtype=float)
    p = 1.0 / (1.0 + np.exp(-x))
    return (p >= threshold).astype(int)


def decode_round_to_integer(position: Position, lb: Sequence[int], ub: Sequence[int]) -> np.ndarray:
    """
    取整 + 边界裁剪：position -> integer vector
    """
    x = np.rint(np.asarray(position, dtype=float)).astype(int)
    lb_arr = np.asarray(lb, dtype=int).reshape(-1)
    ub_arr = np.asarray(ub, dtype=int).reshape(-1)
    return np.clip(x, lb_arr, ub_arr)
