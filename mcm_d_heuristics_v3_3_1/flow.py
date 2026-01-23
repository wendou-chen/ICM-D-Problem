"""\
flow.py
Path-based flow formulation utilities for ICM/MCM D.

Why path-based?
--------------
For network flow, encoding decision variables as edge flows f_{ij} is brittle:
any local mutation breaks flow conservation (\sum f_in = \sum f_out), making the
search space dominated by infeasible solutions.

Path-based decomposition encodes variables as x_k = flow on candidate path P_k.
As long as each P_k is a valid s-t path, flow conservation is automatically
satisfied. The remaining hard constraints are capacities on edges.

This module provides a practical contest-grade toolkit:
- Generate candidate paths for each commodity (k-shortest simple paths).
- Build an incidence structure Edge-Path.
- Provide a *repair* operator that projects any x onto capacity constraints via
  iterative proportional scaling, with an optional greedy augmentation step to
  meet demands.

The goal is not exact optimality, but a robust, fast feasibility mechanism that
plays well with GA/PSO/SA.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np

try:
    import networkx as nx
except Exception:  # pragma: no cover
    nx = None

from .graph_io import k_shortest_paths, path_cost
from .problem import OptimizationProblem, Penalty


def _require_nx() -> Any:
    if nx is None:
        raise ImportError("networkx is required for flow utilities. Please pip install networkx.")
    return nx


@dataclass(frozen=True)
class Commodity:
    """A single-commodity demand from source to target."""

    source: Any
    target: Any
    demand: float
    name: str = ""


@dataclass
class PathFlowModel:
    """Path-based flow model.

    Attributes
    ----------
    paths:
        Candidate paths (list of node lists).
    path_commodity:
        path_commodity[p] = commodity index of path p.
    edge_list:
        Unique directed edges used by any candidate path.
    capacities:
        capacity for each edge in edge_list.
    path_edges:
        path_edges[p] = list of edge indices used by path p.
    edge_to_paths:
        edge_to_paths[e] = list of path indices that use edge e.
    path_costs:
        path costs (sum of weight along edges).
    """

    G: Any
    commodities: List[Commodity]
    paths: List[List[Any]]
    path_commodity: List[int]
    edge_list: List[Tuple[Any, Any]]
    capacities: np.ndarray
    path_edges: List[List[int]]
    edge_to_paths: List[List[int]]
    path_costs: np.ndarray
    weight_attr: str = "weight"
    capacity_attr: str = "capacity"

    @property
    def n_paths(self) -> int:
        return len(self.paths)

    @property
    def n_edges(self) -> int:
        return len(self.edge_list)

    def edge_loads(self, x: np.ndarray) -> np.ndarray:
        x = np.asarray(x, dtype=float).reshape(-1)
        loads = np.zeros(self.n_edges, dtype=float)
        for e, plist in enumerate(self.edge_to_paths):
            if plist:
                loads[e] = float(np.sum(x[plist]))
        return loads

    def capacity_violation(self, x: np.ndarray) -> float:
        loads = self.edge_loads(x)
        vio = np.maximum(0.0, loads - self.capacities)
        return float(np.sum(vio))

    def demand_violation(self, x: np.ndarray) -> float:
        x = np.asarray(x, dtype=float).reshape(-1)
        vio = 0.0
        for m, c in enumerate(self.commodities):
            tot = float(np.sum(x[np.where(np.asarray(self.path_commodity) == m)[0]]))
            if tot < c.demand:
                vio += (c.demand - tot)
        return float(vio)


    def repair_demand_only(self, x: Sequence[float], tol: float = 1e-12) -> np.ndarray:
        """Repair only nonnegativity and *demand equality* within each commodity.

        This is useful for min-max congestion: demands are hard, capacities are in objective.
        """
        x = np.asarray(x, dtype=float).reshape(-1)
        if x.size != self.n_paths:
            raise ValueError(f"x size {x.size} must equal n_paths {self.n_paths}.")
        x = np.maximum(x, 0.0)

        path_comm = np.asarray(self.path_commodity, dtype=int)
        for m, c in enumerate(self.commodities):
            idx = np.where(path_comm == m)[0]
            if idx.size == 0:
                continue
            tot = float(np.sum(x[idx]))
            if tot > tol:
                x[idx] *= (float(c.demand) / tot)
            else:
                x[idx] = 0.0
                x[int(idx[0])] = float(c.demand)
        return x

    def repair(
        self,
        x: Sequence[float],
        *,
        meet_demands: bool = True,
        max_iter: int = 30,
        tol: float = 1e-9,
    ) -> np.ndarray:
        """Repair x to satisfy x>=0, edge capacities, and (optionally) meet demands.

        Heuristic steps
        ---------------
        1) Clip negatives to 0.
        2) If per-commodity total exceeds demand, scale down within commodity.
        3) Iteratively scale down path flows for violated edges (capacity projection).
        4) (Optional) Greedy augmentation using residual capacities to fill unmet demand.
        """
        x = np.asarray(x, dtype=float).reshape(-1)
        if x.size != self.n_paths:
            raise ValueError(f"x size {x.size} must equal n_paths {self.n_paths}.")

        x = np.maximum(x, 0.0)

        # Step 2: enforce per-commodity upper bounds
        path_comm = np.asarray(self.path_commodity, dtype=int)
        for m, c in enumerate(self.commodities):
            idx = np.where(path_comm == m)[0]
            if idx.size == 0:
                continue
            tot = float(np.sum(x[idx]))
            if tot > c.demand + tol:
                x[idx] *= (c.demand / max(tot, tol))

        # Step 3: capacity projection
        for _ in range(max_iter):
            loads = self.edge_loads(x)
            vio_edges = np.where(loads > self.capacities + tol)[0]
            if vio_edges.size == 0:
                break
            for e in vio_edges:
                load = float(loads[e])
                cap = float(self.capacities[e])
                if load <= cap + tol:
                    continue
                factor = cap / max(load, tol)
                for p in self.edge_to_paths[e]:
                    x[p] *= factor

        if not meet_demands:
            return x

        # Step 4: greedy augmentation under residual capacities
        loads = self.edge_loads(x)
        residual = np.maximum(0.0, self.capacities - loads)

        # Precompute paths per commodity sorted by path_cost
        paths_by_m: List[List[int]] = []
        for m, _c in enumerate(self.commodities):
            idx = np.where(path_comm == m)[0].tolist()
            idx.sort(key=lambda p: float(self.path_costs[p]))
            paths_by_m.append(idx)

        for m, c in enumerate(self.commodities):
            idx = paths_by_m[m]
            if not idx:
                continue
            tot = float(np.sum(x[idx]))
            short = c.demand - tot
            if short <= tol:
                continue

            for p in idx:
                if short <= tol:
                    break
                edges = self.path_edges[p]
                if not edges:
                    continue
                bottleneck = float(np.min(residual[edges])) if edges else 0.0
                if bottleneck <= tol:
                    continue
                delta = min(short, bottleneck)
                x[p] += delta
                residual[edges] -= delta
                short -= delta

        return x


def build_path_flow_model(
    G: Any,
    commodities: Sequence[Commodity],
    *,
    k_paths: int = 20,
    weight_attr: str = "weight",
    capacity_attr: str = "capacity",
) -> PathFlowModel:
    """Build a PathFlowModel by enumerating candidate paths per commodity."""
    _nx = _require_nx()

    comms = list(commodities)

    paths: List[List[Any]] = []
    path_commodity: List[int] = []
    for m, c in enumerate(comms):
        cand = k_shortest_paths(G, c.source, c.target, k=k_paths, weight=weight_attr)
        for p in cand:
            paths.append(list(p))
            path_commodity.append(m)

    if not paths:
        # still create a model (empty candidates), leaving it to the user
        return PathFlowModel(
            G=G,
            commodities=comms,
            paths=[],
            path_commodity=[],
            edge_list=[],
            capacities=np.zeros(0, dtype=float),
            path_edges=[],
            edge_to_paths=[],
            path_costs=np.zeros(0, dtype=float),
            weight_attr=weight_attr,
            capacity_attr=capacity_attr,
        )

    # Build edge universe
    edge_index: Dict[Tuple[Any, Any], int] = {}
    edge_list: List[Tuple[Any, Any]] = []
    path_edges: List[List[int]] = []

    for p in paths:
        eidx: List[int] = []
        for u, v in zip(p[:-1], p[1:]):
            key = (u, v)
            if key not in edge_index:
                edge_index[key] = len(edge_list)
                edge_list.append(key)
            eidx.append(edge_index[key])
        path_edges.append(eidx)

    # capacities
    caps = np.full(len(edge_list), float("inf"), dtype=float)
    for (u, v), i in edge_index.items():
        if G.has_edge(u, v):
            cap = G[u][v].get(capacity_attr, float("inf"))
            caps[i] = float(cap)

    # edge_to_paths
    edge_to_paths: List[List[int]] = [[] for _ in range(len(edge_list))]
    for p_idx, eidx in enumerate(path_edges):
        for e in eidx:
            edge_to_paths[e].append(p_idx)

    # path costs
    costs = np.array([path_cost(G, p, weight=weight_attr) for p in paths], dtype=float)

    return PathFlowModel(
        G=G,
        commodities=comms,
        paths=paths,
        path_commodity=path_commodity,
        edge_list=edge_list,
        capacities=caps,
        path_edges=path_edges,
        edge_to_paths=edge_to_paths,
        path_costs=costs,
        weight_attr=weight_attr,
        capacity_attr=capacity_attr,
    )


def make_min_cost_flow_problem(
    model: PathFlowModel,
    *,
    unmet_penalty: float = 1e6,
    meet_demands_in_repair: bool = True,
    penalty: Optional[Penalty] = None,
) -> OptimizationProblem:
    """Create an OptimizationProblem for min-cost flow using the path-flow model.

    Decision variable
    ---------------
    x \in R_+^{|P|}, where x_p is flow on path p.

    Objective
    ---------
    minimize  \sum_p x_p * cost(p)  + unmet_penalty * (\sum_m [d_m - \sum_{p in P(m)} x_p]_+)

    Notes
    -----
    - Repair enforces capacities and tries to meet demands.
    - We still keep a penalty term (Big-M) for diagnostics / robustness.
    """

    def _repair(x: np.ndarray) -> np.ndarray:
        return model.repair(x, meet_demands=meet_demands_in_repair)

    def _obj(x: np.ndarray) -> float:
        x = np.asarray(x, dtype=float).reshape(-1)
        cost = float(np.dot(x, model.path_costs))
        unmet = model.demand_violation(x)
        return cost + float(unmet_penalty * unmet)

    def _capacity_vio(x: np.ndarray) -> float:
        return model.capacity_violation(np.asarray(x, dtype=float))

    def _unmet_vio(x: np.ndarray) -> float:
        # if meet_demands_in_repair=True, this is typically 0; keep for safety
        return model.demand_violation(np.asarray(x, dtype=float))

    if penalty is None:
        penalty = Penalty(weight=1e9)

    # Bounds: 0 <= x_p <= demand(commodity(p)) is a safe default upper bound.
    ub = np.zeros(model.n_paths, dtype=float)
    for p, m in enumerate(model.path_commodity):
        ub[p] = float(model.commodities[m].demand)
    lb = np.zeros_like(ub)

    return OptimizationProblem(
        objective=_obj,
        decoder=None,
        repair=_repair,
        constraints=[_capacity_vio, _unmet_vio],
        penalty=penalty,
        lb=lb,
        ub=ub,
    )


 


# =========================
# Min-Max Congestion utils
# =========================

def make_min_max_congestion_problem(
    model: PathFlowModel,
    *,
    penalty_weight: float = 1e6,
    overload_penalty: float = 0.0,
    penalty: Optional[Penalty] = None,
) -> OptimizationProblem:
    """Create an OptimizationProblem for *min-max congestion* (load balancing).

    Objective
    ---------
    minimize  max_e ( load_e(x) / cap_e )

    Key modeling note
    -----------------
    For min-max congestion, **demands are treated as hard requirements**.
    Therefore, repair only enforces x>=0 and per-commodity demand equality
    (scaling within each commodity). Capacity is not enforced as a hard
    constraint; it is reflected in the objective via utilization ratio.

    Parameters
    ----------
    penalty_weight:
        Safety penalty when some commodity has zero candidate paths.
    overload_penalty:
        Optional extra penalty on (util-1)_+ if you want to discourage overload
        even when minimizing the max utilization.
    """

    def _repair_demand_only(x: np.ndarray) -> np.ndarray:
        return model.repair_demand_only(x)

    def _obj(x: np.ndarray) -> float:
        x = np.asarray(x, dtype=float).reshape(-1)
        # Ensure demands are met; if impossible (no paths), punish.
        x = _repair_demand_only(x)

        # If any commodity has no paths, this is structurally infeasible.
        path_comm = np.asarray(model.path_commodity, dtype=int)
        for m, c in enumerate(model.commodities):
            if np.sum(path_comm == m) == 0:
                return float(penalty_weight)

        loads = model.edge_loads(x)
        caps = np.asarray(model.capacities, dtype=float)

        # utilization: load/cap; inf cap -> 0; cap<=0 with load>0 -> huge
        util = np.zeros_like(loads)
        finite = np.isfinite(caps)
        pos = (caps > 1e-12) & finite
        util[pos] = loads[pos] / caps[pos]
        bad = (~pos) & (loads > 1e-12)
        util[bad] = 1e9

        max_util = float(np.max(util)) if util.size else 0.0

        if overload_penalty > 0.0:
            over = np.maximum(0.0, util - 1.0)
            max_util += float(overload_penalty * np.sum(over))
        return max_util

    if penalty is None:
        penalty = Penalty(weight=1e9)

    # Bounds: 0 <= x_p <= demand(commodity(p))
    ub = np.zeros(model.n_paths, dtype=float)
    for p, m in enumerate(model.path_commodity):
        ub[p] = float(model.commodities[m].demand)
    lb = np.zeros_like(ub)

    # We do NOT add capacity as a constraint here; capacity is in objective.
    # We keep a structural constraint: no negative demand violation (should be 0 after repair).
    def _demand_vio(x: np.ndarray) -> float:
        return model.demand_violation(np.asarray(x, dtype=float))

    return OptimizationProblem(
        objective=_obj,
        decoder=None,
        repair=_repair_demand_only,
        constraints=[_demand_vio],
        penalty=penalty,
        lb=lb,
        ub=ub,
    )


def op_congestion_shift(
    x: np.ndarray,
    model: PathFlowModel,
    rng: np.random.Generator,
    *,
    shift_ratio: float = 0.1,
    max_tries: int = 15,
    tol: float = 1e-12,
) -> np.ndarray:
    """Domain-specific operator for min-max congestion.

    Idea
    ----
    Identify the most congested edge e_max, then *shift* a small amount of flow
    from a path using e_max to an alternative path (same commodity) that does
    NOT use e_max.

    This combats the "flat" objective landscape of min-max problems, where only
    the bottleneck edge affects the objective.

    Notes
    -----
    - We preserve per-commodity demand by shifting within the same commodity.
    - If no alternative path exists, return x unchanged.
    """
    x = np.asarray(x, dtype=float).reshape(-1).copy()
    if x.size != model.n_paths:
        raise ValueError(f"x size {x.size} must equal n_paths {model.n_paths}.")

    # Normalize to meet demands (keeps x within reasonable bounds)
    x = model.repair_demand_only(x)

    loads = model.edge_loads(x)
    caps = np.asarray(model.capacities, dtype=float)

    util = np.zeros_like(loads)
    finite = np.isfinite(caps)
    pos = (caps > tol) & finite
    util[pos] = loads[pos] / caps[pos]
    bad = (~pos) & (loads > tol)
    util[bad] = 1e9

    if util.size == 0:
        return x

    e_max = int(np.argmax(util))
    if float(util[e_max]) <= 0.0:
        return x

    # Candidate victim paths using e_max with positive flow
    candidates = [p for p in model.edge_to_paths[e_max] if x[p] > tol]
    if not candidates:
        return x

    # Prefer higher-flow victims (more effective shifting)
    w = np.array([x[p] for p in candidates], dtype=float)
    w_sum = float(np.sum(w))
    if w_sum <= tol:
        p_victim = int(candidates[int(rng.integers(0, len(candidates)))])
    else:
        w = w / w_sum
        p_victim = int(rng.choice(np.array(candidates, dtype=int), p=w))

    m = int(model.path_commodity[p_victim])

    # Alternative paths in the SAME commodity that do NOT use e_max
    path_comm = np.asarray(model.path_commodity, dtype=int)
    same_m = np.where(path_comm == m)[0].tolist()
    alt = [p for p in same_m if p != p_victim and (e_max not in model.path_edges[p])]
    if not alt:
        return x

    delta = float(x[p_victim] * shift_ratio)
    if delta <= tol:
        return x

    # Heuristic: choose alt that best reduces estimated max-utilization on affected edges.
    victim_edges = model.path_edges[p_victim]

    # A cheap global "other-edge" max excluding victim edges (approximate)
    if model.n_edges > 0:
        mask = np.ones(model.n_edges, dtype=bool)
        mask[victim_edges] = False
        max_other = float(np.max(util[mask])) if np.any(mask) else 0.0
    else:
        max_other = 0.0

    best_p = int(alt[int(rng.integers(0, len(alt)))])
    best_score = float('inf')

    for _ in range(min(max_tries, len(alt))):
        p_alt = int(alt[int(rng.integers(0, len(alt)))])
        alt_edges = model.path_edges[p_alt]

        # compute max util on affected edges after shift, without full vector copy
        changed = {}
        for e in victim_edges:
            changed[e] = changed.get(e, 0.0) - delta
        for e in alt_edges:
            changed[e] = changed.get(e, 0.0) + delta

        max_aff = 0.0
        for e, dload in changed.items():
            new_load = float(loads[e] + dload)
            if new_load < 0.0:
                new_load = 0.0
            cap = float(caps[e])
            if not np.isfinite(cap):
                u = 0.0
            elif cap <= tol:
                u = 1e9 if new_load > tol else 0.0
            else:
                u = new_load / cap
            if u > max_aff:
                max_aff = u

        score = max(max_other, max_aff)
        if score < best_score:
            best_score = score
            best_p = p_alt

    # Apply shift
    x[p_victim] -= delta
    x[best_p] += delta
    if x[p_victim] < 0.0:
        x[p_victim] = 0.0

    # Renormalize within commodity to maintain exact demand equality
    x = model.repair_demand_only(x)
    return x
