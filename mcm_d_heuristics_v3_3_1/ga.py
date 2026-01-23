"""
ga.py
通用遗传算法（GA），支持多编码 + 精英保留。
- Permutation: 路径/访问顺序（TSP/巡检/路由序列）
- Binary: 0/1 选址/背包/激活
- Real: 连续参数优化（功率分配、比例等）
- Integer: 整数决策（设施数量、服务器台数等）

算法层不关心目标/约束：通过 OptimizationProblem.evaluate_solution() 注入。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Literal, Optional, Tuple

import numpy as np
import sys
try:
    from tqdm import tqdm
except Exception:  # pragma: no cover
    tqdm = None

try:
    import networkx as nx
except Exception:  # pragma: no cover
    nx = None

from .graph_io import k_shortest_paths, repair_path, path_cost, biased_random_walk_path

from .problem import OptimizationProblem


Encoding = Literal["permutation", "binary", "real", "integer"]


@dataclass
class GAConfig:
    encoding: Encoding
    n_pop: int = 120
    max_gen: int = 300
    enable_progress_bar: bool = False
    progress_position: Optional[int] = None
    progress_leave: bool = False
    cx_rate: float = 0.9
    mut_rate: float = 0.05
    elitism_k: int = 2
    tournament_k: int = 3
    seed: Optional[int] = 42

    # genome settings (choose depending on encoding)
    n_genes: Optional[int] = None  # for binary/real/integer
    perm_size: Optional[int] = None  # for permutation
    lb: Optional[np.ndarray] = None  # for real/integer
    ub: Optional[np.ndarray] = None  # for real/integer

    # New: Seed population (e.g. from PSO results)
    seed_population: Optional[np.ndarray] = None  # shape=(n_seed, n_genes), binary 0/1

    # for BLX-alpha
    blx_alpha: float = 0.3

    # optional: domain-specific mutation operator (e.g., flow shifting for min-max congestion)
    # signature: op(genome, rng) -> genome
    custom_mutation: Optional[Callable[[np.ndarray, np.random.Generator], np.ndarray]] = None
    custom_mutation_prob: float = 0.0

    # -------- Stagnation-based trigger (contest-grade) --------
    # For expensive, domain-specific operators (e.g., min-max congestion flow shifting),
    # a static probability can waste compute early on. Instead, trigger an aggressive
    # operator only when the global best has not improved for `stagnation_patience` gens.
    stagnation_patience: int = 0  # 0 disables the trigger
    stagnation_tol: float = 1e-9
    stagnation_reset: bool = True

    # Apply aggressive operator to elites (excluding the very best) when triggered.
    stagnation_elite_fraction: float = 1.0  # fraction of elites (excluding best) to mutate
    stagnation_aggressive_steps: int = 1

    # Optional separate aggressive operator (stronger than `custom_mutation`).
    # signature: op(genome, rng) -> genome
    custom_mutation_aggressive: Optional[Callable[[np.ndarray, np.random.Generator], np.ndarray]] = None


def _tournament_select(rng: np.random.Generator, pop: np.ndarray, costs: np.ndarray, k: int) -> np.ndarray:
    """Select one individual (minimization) via tournament."""
    idx = rng.integers(0, len(pop), size=k)
    best = idx[np.argmin(costs[idx])]
    return pop[best].copy()


def _order_crossover(rng: np.random.Generator, p1: np.ndarray, p2: np.ndarray) -> np.ndarray:
    """OX: keep a segment from p1, fill the rest by order from p2."""
    n = len(p1)
    a, b = sorted(rng.integers(0, n, size=2))
    child = -np.ones(n, dtype=int)
    child[a:b] = p1[a:b]
    fill = [x for x in p2 if x not in child[a:b]]
    ptr = 0
    for i in range(n):
        if child[i] == -1:
            child[i] = fill[ptr]
            ptr += 1
    return child


def _swap_mutation(rng: np.random.Generator, x: np.ndarray) -> np.ndarray:
    n = len(x)
    i, j = rng.integers(0, n, size=2)
    y = x.copy()
    y[i], y[j] = y[j], y[i]
    return y


def _inversion_mutation(rng: np.random.Generator, x: np.ndarray) -> np.ndarray:
    n = len(x)
    a, b = sorted(rng.integers(0, n, size=2))
    y = x.copy()
    y[a:b] = y[a:b][::-1]
    return y


def _uniform_crossover(rng: np.random.Generator, p1: np.ndarray, p2: np.ndarray) -> np.ndarray:
    mask = rng.random(p1.shape) < 0.5
    child = np.where(mask, p1, p2)
    return child


def _blx_alpha_crossover(rng: np.random.Generator, p1: np.ndarray, p2: np.ndarray, alpha: float) -> np.ndarray:
    lo = np.minimum(p1, p2)
    hi = np.maximum(p1, p2)
    diff = hi - lo
    low = lo - alpha * diff
    high = hi + alpha * diff
    return rng.uniform(low, high)


class GeneticAlgorithm:
    def __init__(self, problem: OptimizationProblem, config: GAConfig):
        self.problem = problem
        self.cfg = config
        self.rng = np.random.default_rng(config.seed)

        self.history_best: list[float] = []
        self.best_solution = None
        self.best_cost: float = float("inf")

        self._validate()

    def _validate(self) -> None:
        enc = self.cfg.encoding
        if enc == "permutation":
            if self.cfg.perm_size is None:
                raise ValueError("perm_size is required for permutation encoding.")
        else:
            if self.cfg.n_genes is None:
                raise ValueError("n_genes is required for binary/real/integer encoding.")
            if enc in ("real", "integer"):
                if self.cfg.lb is None or self.cfg.ub is None:
                    raise ValueError("lb/ub are required for real/integer encoding.")
                lb = np.asarray(self.cfg.lb).reshape(-1)
                ub = np.asarray(self.cfg.ub).reshape(-1)
                if lb.size != self.cfg.n_genes or ub.size != self.cfg.n_genes:
                    raise ValueError("lb/ub must have size n_genes.")
        if self.cfg.elitism_k < 0 or self.cfg.elitism_k >= self.cfg.n_pop:
            raise ValueError("elitism_k must satisfy 0 <= elitism_k < n_pop.")

    # ---------- initialization ----------
    def _init_population(self) -> np.ndarray:
        enc = self.cfg.encoding
        n_pop = self.cfg.n_pop
        
        pop = None
        if enc == "permutation":
            n = int(self.cfg.perm_size)
            pop = np.vstack([self.rng.permutation(n) for _ in range(n_pop)]).astype(int)
        elif enc == "binary":
            D = int(self.cfg.n_genes)
            pop = (self.rng.random((n_pop, D)) < 0.5).astype(int)
        elif enc == "real":
            lb = np.asarray(self.cfg.lb, dtype=float).reshape(-1)
            ub = np.asarray(self.cfg.ub, dtype=float).reshape(-1)
            pop = self.rng.uniform(lb, ub, size=(n_pop, lb.size))
        elif enc == "integer":
            lb = np.asarray(self.cfg.lb, dtype=int).reshape(-1)
            ub = np.asarray(self.cfg.ub, dtype=int).reshape(-1)
            pop = self.rng.integers(lb, ub + 1, size=(n_pop, lb.size)).astype(int)
        else:
            raise ValueError(f"Unknown encoding: {enc}")

        # Inject seed population if provided
        if self.cfg.seed_population is not None:
            seeds = np.asarray(self.cfg.seed_population)
            n_seeds = len(seeds)
            if n_seeds > 0:
                k = min(n_seeds, n_pop)
                # Ensure seeds match encoding type (roughly)
                if enc == "binary" or enc == "integer" or enc == "permutation":
                    pop[:k] = seeds[:k].astype(int)
                else:
                    pop[:k] = seeds[:k]

        return pop

    # ---------- operators ----------
    def _crossover(self, p1: np.ndarray, p2: np.ndarray) -> np.ndarray:
        if self.rng.random() > self.cfg.cx_rate:
            return p1.copy()
        enc = self.cfg.encoding
        if enc == "permutation":
            return _order_crossover(self.rng, p1, p2)
        if enc == "binary":
            return _uniform_crossover(self.rng, p1, p2).astype(int)
        if enc == "real":
            child = _blx_alpha_crossover(self.rng, p1, p2, self.cfg.blx_alpha)
            lb = np.asarray(self.cfg.lb, dtype=float).reshape(-1)
            ub = np.asarray(self.cfg.ub, dtype=float).reshape(-1)
            return np.clip(child, lb, ub)
        if enc == "integer":
            child = _blx_alpha_crossover(self.rng, p1.astype(float), p2.astype(float), self.cfg.blx_alpha)
            lb = np.asarray(self.cfg.lb, dtype=float).reshape(-1)
            ub = np.asarray(self.cfg.ub, dtype=float).reshape(-1)
            child = np.clip(child, lb, ub)
            return np.rint(child).astype(int)
        raise ValueError(f"Unknown encoding: {enc}")

    def _mutate(self, x: np.ndarray) -> np.ndarray:
        enc = self.cfg.encoding

        # optional domain-specific mutation (applied before default mutation)
        if self.cfg.custom_mutation is not None and self.cfg.custom_mutation_prob > 0:
            if self.rng.random() < float(self.cfg.custom_mutation_prob):
                y = self.cfg.custom_mutation(x.copy(), self.rng)
                # keep within bounds if provided
                if enc in ("real", "integer") and self.cfg.lb is not None and self.cfg.ub is not None:
                    lb = np.asarray(self.cfg.lb, dtype=float).reshape(-1)
                    ub = np.asarray(self.cfg.ub, dtype=float).reshape(-1)
                    y = np.clip(np.asarray(y, dtype=float), lb, ub)
                    if enc == "integer":
                        y = np.rint(y).astype(int)
                return y
        if enc == "permutation":
            if self.rng.random() < self.cfg.mut_rate:
                # randomly choose one of two neighborhood operators
                if self.rng.random() < 0.5:
                    return _swap_mutation(self.rng, x)
                return _inversion_mutation(self.rng, x)
            return x
        if enc == "binary":
            y = x.copy()
            flip = self.rng.random(y.shape) < self.cfg.mut_rate
            y[flip] = 1 - y[flip]
            return y.astype(int)
        if enc == "real":
            y = x.copy()
            lb = np.asarray(self.cfg.lb, dtype=float).reshape(-1)
            ub = np.asarray(self.cfg.ub, dtype=float).reshape(-1)
            sigma = 0.1 * (ub - lb + 1e-12)
            mask = self.rng.random(y.shape) < self.cfg.mut_rate
            y[mask] = y[mask] + self.rng.normal(0.0, sigma[mask])
            return np.clip(y, lb, ub)
        if enc == "integer":
            y = x.copy()
            lb = np.asarray(self.cfg.lb, dtype=int).reshape(-1)
            ub = np.asarray(self.cfg.ub, dtype=int).reshape(-1)
            mask = self.rng.random(y.shape) < self.cfg.mut_rate
            # random reset mutation
            if np.any(mask):
                y[mask] = self.rng.integers(lb[mask], ub[mask] + 1)
            return y.astype(int)
        raise ValueError(f"Unknown encoding: {enc}")

    def _clip_to_bounds(self, genome: np.ndarray) -> np.ndarray:
        """Keep genome within bounds for real/integer encodings."""
        enc = self.cfg.encoding
        if enc in ("real", "integer") and self.cfg.lb is not None and self.cfg.ub is not None:
            lb = np.asarray(self.cfg.lb, dtype=float).reshape(-1)
            ub = np.asarray(self.cfg.ub, dtype=float).reshape(-1)
            y = np.clip(np.asarray(genome, dtype=float).reshape(-1), lb, ub)
            if enc == "integer":
                y = np.rint(y).astype(int)
            return y
        return genome

    def _apply_aggressive_operator_to_elites(self, elites: np.ndarray) -> np.ndarray:
        """Apply the aggressive domain operator to elites (excluding the best)."""
        if elites.size == 0:
            return elites
        op = self.cfg.custom_mutation_aggressive or self.cfg.custom_mutation
        if op is None:
            return elites
        if self.cfg.stagnation_aggressive_steps <= 0:
            return elites

        # Do not mutate the very best elite to preserve monotonic best-cost tracking.
        n_elite = len(elites)
        k_mut = max(0, n_elite - 1)
        if k_mut == 0:
            return elites
        frac = float(self.cfg.stagnation_elite_fraction)
        frac = min(1.0, max(0.0, frac))
        n_apply = int(np.ceil(k_mut * frac)) if frac > 0 else 0
        n_apply = min(k_mut, max(0, n_apply))
        if n_apply == 0:
            return elites

        # Mutate a random subset among elites[1:]
        idx_pool = np.arange(1, n_elite)
        self.rng.shuffle(idx_pool)
        chosen = idx_pool[:n_apply]

        out = elites.copy()
        for i in chosen:
            g = out[int(i)].copy()
            for _ in range(int(self.cfg.stagnation_aggressive_steps)):
                g = op(g, self.rng)
                g = self._clip_to_bounds(g)
            out[int(i)] = g
        return out

    # ---------- evaluation ----------
    def _costs(self, pop: np.ndarray, desc: str = "GA eval") -> np.ndarray:
        """Evaluate fitness for all individuals."""
        costs = np.zeros(len(pop), dtype=float)
        eval_pos = None if self.cfg.progress_position is None else self.cfg.progress_position + 1

        if self.cfg.enable_progress_bar and tqdm is not None:
            iterator = tqdm(
                enumerate(pop),
                total=len(pop),
                desc=desc,
                file=sys.stderr,
                leave=self.cfg.progress_leave,
                position=eval_pos,
                dynamic_ncols=True,
                mininterval=0.5,
            )
        else:
            iterator = enumerate(pop)
        
        for i, genome in iterator:
            sol = self.problem.decode(genome)
            costs[i] = self.problem.evaluate_solution(sol)
        return costs

    def run(self, step_callback: Optional[Callable[..., None]] = None) -> Tuple[object, float]:
        pop = self._init_population()
        costs = self._costs(pop, desc="GA init")

        best_idx = int(np.argmin(costs))
        self.best_solution = self.problem.decode(pop[best_idx])
        self.best_cost = float(costs[best_idx])
        self.history_best = [self.best_cost]
        self.history_solutions = [self.best_solution] # Record initial best

        # stagnation tracking (minimization)
        best_ever_cost = float(self.best_cost)
        stagnation_counter = 0

        gen_range = range(self.cfg.max_gen)
        pbar = None
        if self.cfg.enable_progress_bar and tqdm is not None:
            pbar = tqdm(
                total=self.cfg.max_gen,
                desc=f"GA best={self.best_cost:.4f}",
                disable=False,
                file=sys.stderr,
                dynamic_ncols=True,
                mininterval=0.0,
                miniters=1,
                leave=True,
                position=self.cfg.progress_position,
            )

        for _gen in gen_range:
            # trigger expensive, domain-specific operator only when stagnated
            trigger = (
                self.cfg.stagnation_patience > 0
                and stagnation_counter >= int(self.cfg.stagnation_patience)
                and (self.cfg.custom_mutation_aggressive is not None or self.cfg.custom_mutation is not None)
            )
            # elitism
            elite_idx = np.argsort(costs)[: self.cfg.elitism_k]
            elites = pop[elite_idx].copy()

            if trigger and self.cfg.elitism_k > 0:
                elites = self._apply_aggressive_operator_to_elites(elites)
                if self.cfg.stagnation_reset:
                    stagnation_counter = 0

            # breeding
            new_pop = []
            while len(new_pop) < self.cfg.n_pop - self.cfg.elitism_k:
                p1 = _tournament_select(self.rng, pop, costs, self.cfg.tournament_k)
                p2 = _tournament_select(self.rng, pop, costs, self.cfg.tournament_k)
                child = self._crossover(p1, p2)
                child = self._mutate(child)
                new_pop.append(child)

            pop = np.vstack([elites] + new_pop) if self.cfg.elitism_k > 0 else np.vstack(new_pop)
            costs = self._costs(pop, desc=f"GA gen {_gen+1}/{self.cfg.max_gen}")

            gen_best_idx = int(np.argmin(costs))
            gen_best_cost = float(costs[gen_best_idx])
            if gen_best_cost < self.best_cost:
                self.best_cost = gen_best_cost
                self.best_solution = self.problem.decode(pop[gen_best_idx])

            self.history_best.append(self.best_cost)
            self.history_solutions.append(self.best_solution) # Append best solution at this step
            if pbar is not None:
                pbar.set_description(f"GA best={self.best_cost:.4f}")
                pbar.update(1)
            if step_callback is not None:
                avg_cost = float(np.mean(costs)) if costs.size else float("nan")
                diversity = float(np.std(costs)) if costs.size else float("nan")
                step_callback(
                    current_iter=_gen,
                    best_cost=float(self.best_cost),
                    avg_cost=avg_cost,
                    diversity=diversity,
                    phase="GA",
                )

            # update stagnation after observing (potentially improved) global best
            if self.best_cost < best_ever_cost - float(self.cfg.stagnation_tol):
                best_ever_cost = float(self.best_cost)
                stagnation_counter = 0
            else:
                stagnation_counter += 1

        if pbar is not None:
            pbar.close()

        return self.best_solution, self.best_cost

# ==========================
# Variable-length Path GA
# ==========================

from dataclasses import dataclass as _dataclass
from typing import Any as _Any, List as _List, Optional as _Optional, Tuple as _Tuple


@_dataclass
class PathGAConfig:
    """
    GA for variable-length paths on graphs (A->B routing / inspection with optional intermediate nodes).

    Notes
    -----
    - Specialized for ICM D题 graph/path variants.
    - Relies on repair_path(...) to keep feasibility high.
    - Avoid nx.all_simple_paths (can explode); use k_shortest_paths + random walks.
    """
    population_size: int = 80
    generations: int = 200
    elitism_k: int = 4

    crossover_rate: float = 0.9
    mutation_rate: float = 0.4

    # mutation operator mix
    p_delete: float = 0.25
    p_insert: float = 0.25
    p_reroute: float = 0.50

    # seeding
    k_seed_paths: int = 20
    random_walk_seeds: int = 40
    max_nodes: int = 80

    weight: str = "weight"
    seed: _Optional[int] = 42


class PathGeneticAlgorithm:
    """
    Variable-length path GA.

    Genome/solution: List[node]
    Evaluation: problem.evaluate_solution(path)
    """
    def __init__(self, G: _Any, source: _Any, target: _Any, problem: "OptimizationProblem", cfg: PathGAConfig):
        if nx is None:
            raise ImportError("networkx is required for PathGeneticAlgorithm.")
        self.G = G
        self.s = source
        self.t = target
        self.problem = problem
        self.cfg = cfg
        self.rng = np.random.default_rng(cfg.seed)

        # default repair: graph connectivity repair
        if self.problem.repair is None:
            self.problem.repair = lambda p: repair_path(self.G, p, self.s, self.t, weight=self.cfg.weight, max_nodes=self.cfg.max_nodes)

        self.best_solution: _Optional[_List[_Any]] = None
        self.best_cost: float = float("inf")
        self.history_best: _List[float] = []

    def _seed_population(self) -> _List[_List[_Any]]:
        pop: _List[_List[_Any]] = []
        # 1) k-shortest seeds
        seeds = k_shortest_paths(self.G, self.s, self.t, k=self.cfg.k_seed_paths, weight=self.cfg.weight)
        for p in seeds:
            pop.append(repair_path(self.G, p, self.s, self.t, weight=self.cfg.weight, max_nodes=self.cfg.max_nodes))

        # 2) biased random-walk seeds
        # - precomputes dist-to-target once per walk (in graph_io)
        # - avoids calling nx.has_path(...) inside the loop, which can be expensive on large graphs
        for _ in range(self.cfg.random_walk_seeds):
            walk = biased_random_walk_path(
                self.G,
                self.s,
                self.t,
                max_steps=self.cfg.max_nodes,
                weight=self.cfg.weight,
                beta=2.0,
                p_explore=0.3,
                avoid_loops=0.8,
                rng=self.rng,
            )
            pop.append(repair_path(self.G, walk, self.s, self.t, weight=self.cfg.weight, max_nodes=self.cfg.max_nodes))

        # 3) pad if needed
        while len(pop) < self.cfg.population_size:
            if nx.has_path(self.G, self.s, self.t):
                sp = nx.shortest_path(self.G, self.s, self.t, weight=self.cfg.weight)
            else:
                sp = [self.s, self.t]
            pop.append(repair_path(self.G, sp, self.s, self.t, weight=self.cfg.weight, max_nodes=self.cfg.max_nodes))

        self.rng.shuffle(pop)
        return pop[: self.cfg.population_size]

    def _cost(self, path: _List[_Any]) -> float:
        return float(self.problem.evaluate_solution(path))

    def _tournament(self, pop: _List[_List[_Any]], costs: np.ndarray, k: int = 3) -> _List[_Any]:
        idx = self.rng.integers(0, len(pop), size=k)
        best = idx[int(np.argmin(costs[idx]))]
        return pop[int(best)]

    def _crossover(self, p1: _List[_Any], p2: _List[_Any]) -> _Tuple[_List[_Any], _List[_Any]]:
        # common-node crossover: pick an internal common node as pivot
        set1 = set(p1[1:-1])
        commons = [x for x in p2[1:-1] if x in set1]
        if commons and self.rng.random() < 0.8:
            pivot = commons[int(self.rng.integers(0, len(commons)))]
            i1 = p1.index(pivot)
            i2 = p2.index(pivot)
            c1 = p1[: i1] + p2[i2:]
            c2 = p2[: i2] + p1[i1:]
        else:
            # prefix-suffix crossover then repair
            cut1 = int(self.rng.integers(1, max(2, len(p1) - 1)))
            cut2 = int(self.rng.integers(1, max(2, len(p2) - 1)))
            c1 = p1[:cut1] + p2[cut2:]
            c2 = p2[:cut2] + p1[cut1:]

        c1 = repair_path(self.G, c1, self.s, self.t, weight=self.cfg.weight, max_nodes=self.cfg.max_nodes)
        c2 = repair_path(self.G, c2, self.s, self.t, weight=self.cfg.weight, max_nodes=self.cfg.max_nodes)
        return c1, c2

    def _mutate(self, path: _List[_Any]) -> _List[_Any]:
        if len(path) <= 2:
            return path
        op = self.rng.random()
        p = list(path)

        if op < self.cfg.p_delete:
            # delete internal node
            if len(p) > 3:
                i = int(self.rng.integers(1, len(p) - 1))
                p.pop(i)

        elif op < self.cfg.p_delete + self.cfg.p_insert:
            # insert a neighbor after some position
            i = int(self.rng.integers(0, len(p) - 1))
            u = p[i]
            neigh = list(self.G.successors(u)) if isinstance(self.G, nx.DiGraph) else list(self.G.neighbors(u))
            if neigh:
                v = neigh[int(self.rng.integers(0, len(neigh)))]
                p.insert(i + 1, v)

        else:
            # reroute a segment between two nodes using shortest path
            if len(p) > 4:
                i = int(self.rng.integers(0, len(p) - 2))
                j = int(self.rng.integers(i + 1, len(p) - 1))
                a, b = p[i], p[j]
                if nx.has_path(self.G, a, b):
                    seg = nx.shortest_path(self.G, a, b, weight=self.cfg.weight)
                    p = p[:i] + seg + p[j+1:]

        p = repair_path(self.G, p, self.s, self.t, weight=self.cfg.weight, max_nodes=self.cfg.max_nodes)
        return p

    def run(self) -> _Tuple[_List[_Any], float]:
        pop = self._seed_population()
        costs = np.array([self._cost(ind) for ind in pop], dtype=float)

        best_idx = int(np.argmin(costs))
        self.best_cost = float(costs[best_idx])
        self.best_solution = pop[best_idx]
        self.history_best = [self.best_cost]

        for _gen in range(self.cfg.generations):
            elite_idx = np.argsort(costs)[: self.cfg.elitism_k]
            elites = [pop[int(i)] for i in elite_idx]

            new_pop: _List[_List[_Any]] = []
            while len(new_pop) < self.cfg.population_size - self.cfg.elitism_k:
                p1 = self._tournament(pop, costs)
                p2 = self._tournament(pop, costs)

                if self.rng.random() < self.cfg.crossover_rate:
                    c1, c2 = self._crossover(p1, p2)
                else:
                    c1, c2 = list(p1), list(p2)

                if self.rng.random() < self.cfg.mutation_rate:
                    c1 = self._mutate(c1)
                if self.rng.random() < self.cfg.mutation_rate:
                    c2 = self._mutate(c2)

                new_pop.append(c1)
                if len(new_pop) < self.cfg.population_size - self.cfg.elitism_k:
                    new_pop.append(c2)

            pop = elites + new_pop
            costs = np.array([self._cost(ind) for ind in pop], dtype=float)

            gen_best = float(np.min(costs))
            if gen_best < self.best_cost:
                self.best_cost = gen_best
                self.best_solution = pop[int(np.argmin(costs))]

            self.history_best.append(self.best_cost)

        assert self.best_solution is not None
        return self.best_solution, self.best_cost
