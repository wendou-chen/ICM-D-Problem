"""demo_sensitivity_robustness.py

ICM/IMC D 题 O 奖级章节支撑脚本：Model Assessment / Sensitivity Analysis。

**不修改任何核心库代码**，在 examples/ 目录新增该脚本即可。

提供两类评估：

(1) 网络韧性/抗毁性（Automated Resilience Testing）
    - 随机攻击（random）：按比例随机移除节点/边
    - 蓄意攻击（targeted）：移除 betweenness centrality 最高的节点（或负载最高的边）

    输出：
      - Throughput Ratio：幸存吞吐 / 总需求（固定策略 best_x，不重算优化）
      - Path Survival Ratio：活跃路径中仍可用的比例
      - 攻击-性能下降曲线（含误差条：random attack 多次重复）

(2) 参数扰动蒙特卡洛（Monte Carlo Robustness Check）
    - demand 扰动：demand * Normal(1, sigma)
    - capacity 扰动：cap * Uniform(cap_low, cap_high)

    评估：
      - Reliability(no overload)：P( max_e load_e/cap_e <= 1 )
      - Capacity-feasible throughput：通过全局缩放 alpha=min_e cap/load 的可达吞吐占比

运行：
    python -m mcm_d_heuristics_v3_3_1.examples.demo_sensitivity_robustness --mode minmax

说明：
- 为了让脚本可独立复现，本脚本默认会先跑一次 GA 求 best_x（可替换为你自己的 best_x 载入逻辑）。
- 若你已经有 (G, model, best_x)，只需跳过 solve_baseline()，直接调用 resilience_test() / monte_carlo_robustness()。
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from typing import Any, Dict, List, Sequence, Tuple

import numpy as np
import networkx as nx
import matplotlib.pyplot as plt


# ============================ Robust Imports ============================

def _import_lib():
    """Try multiple package names to be robust across your versions.

    Preferred: mcm_d_heuristics_v3_3_1
    Fallbacks: mcm_d_heuristics_v3_3, mcm_d_heuristics
    """

    pkgs = [
        "mcm_d_heuristics_v3_3_1",
        "mcm_d_heuristics_v3_3",
        "mcm_d_heuristics",
    ]

    last_err = None
    for pkg in pkgs:
        try:
            mod = __import__(pkg, fromlist=["GAConfig", "GeneticAlgorithm"])
            GAConfig = getattr(mod, "GAConfig")
            GeneticAlgorithm = getattr(mod, "GeneticAlgorithm")

            flow = __import__(f"{pkg}.flow", fromlist=[
                "Commodity",
                "build_path_flow_model",
                "make_min_cost_flow_problem",
                "make_min_max_congestion_problem",
                "op_congestion_shift",
            ])
            Commodity = getattr(flow, "Commodity")
            build_path_flow_model = getattr(flow, "build_path_flow_model")
            make_min_cost_flow_problem = getattr(flow, "make_min_cost_flow_problem")
            make_min_max_congestion_problem = getattr(flow, "make_min_max_congestion_problem")
            op_congestion_shift = getattr(flow, "op_congestion_shift")

            return (
                pkg,
                GAConfig,
                GeneticAlgorithm,
                Commodity,
                build_path_flow_model,
                make_min_cost_flow_problem,
                make_min_max_congestion_problem,
                op_congestion_shift,
            )
        except Exception as e:  # pragma: no cover
            last_err = e

    raise ImportError(
        "Cannot import heuristics library under expected package names. "
        "Tried: mcm_d_heuristics_v3_3_1, mcm_d_heuristics_v3_3, mcm_d_heuristics. "
        f"Last error: {last_err}"
    )


(
    PKG_NAME,
    GAConfig,
    GeneticAlgorithm,
    Commodity,
    build_path_flow_model,
    make_min_cost_flow_problem,
    make_min_max_congestion_problem,
    op_congestion_shift,
) = _import_lib()


def _ga_config(**kwargs):
    """Create GAConfig with only supported fields (avoid version mismatch)."""
    fields = getattr(GAConfig, "__dataclass_fields__", {})
    if not fields:
        # not a dataclass: assume it accepts kwargs
        return GAConfig(**kwargs)
    filtered = {k: v for k, v in kwargs.items() if k in fields}
    return GAConfig(**filtered)


# ============================ Demo Instance ============================


def build_demo_graph(seed: int = 0) -> nx.DiGraph:
    """Small but non-trivial directed graph with capacity & weight."""
    rng = np.random.default_rng(seed)
    G = nx.DiGraph()

    n = 14
    G.add_nodes_from(range(n))

    # backbone
    for i in range(n - 1):
        G.add_edge(
            i,
            i + 1,
            capacity=float(rng.integers(6, 14)),
            weight=float(rng.uniform(0.8, 2.0)),
        )

    # shortcuts
    for _ in range(24):
        u = int(rng.integers(0, n))
        v = int(rng.integers(0, n))
        if u == v or G.has_edge(u, v):
            continue
        G.add_edge(
            u,
            v,
            capacity=float(rng.integers(4, 12)),
            weight=float(rng.uniform(0.5, 2.5)),
        )

    return G


@dataclass
class BaselineResult:
    G: nx.DiGraph
    commodities: List[Any]
    model: Any
    best_x: np.ndarray
    history_best: List[float]
    name: str


def solve_baseline(mode: str = "minmax", seed: int = 11) -> BaselineResult:
    """Solve once to obtain best_x for later assessment plots."""
    G = build_demo_graph(seed=seed)

    commodities = [
        Commodity(0, 13, demand=12.0, name="A"),
        Commodity(2, 11, demand=10.0, name="B"),
    ]

    model = build_path_flow_model(
        G,
        commodities,
        k_paths=10,
        weight_attr="weight",
        capacity_attr="capacity",
    )
    if getattr(model, "n_paths", 0) == 0:
        raise RuntimeError("No candidate paths found. Try increasing k_paths or graph density.")

    lb = np.zeros(model.n_paths, dtype=float)
    ub = np.array([model.commodities[m].demand for m in model.path_commodity], dtype=float)

    if mode == "mincost":
        problem = make_min_cost_flow_problem(model, unmet_penalty=1e5, meet_demands_in_repair=True)
        cfg = _ga_config(
            encoding="real",
            n_pop=140,
            max_gen=220,
            cx_rate=0.9,
            mut_rate=0.18,
            elitism_k=4,
            tournament_k=3,
            seed=seed,
            n_genes=model.n_paths,
            lb=lb,
            ub=ub,
        )
        name = "Min-Cost"
    else:
        problem = make_min_max_congestion_problem(model, penalty_weight=1e6, overload_penalty=0.0)
        cfg = _ga_config(
            encoding="real",
            n_pop=160,
            max_gen=260,
            cx_rate=0.9,
            mut_rate=0.15,
            elitism_k=4,
            tournament_k=3,
            seed=seed,
            n_genes=model.n_paths,
            lb=lb,
            ub=ub,
            # domain-specific operator
            custom_mutation_prob=0.02,
            custom_mutation=lambda genome, rng: op_congestion_shift(
                genome, model, rng, shift_ratio=0.10, max_tries=20
            ),
            # stagnation trigger (if supported)
            stagnation_patience=12,
            stagnation_tol=1e-8,
            stagnation_reset=True,
            stagnation_elite_fraction=1.0,
            stagnation_aggressive_steps=2,
            custom_mutation_aggressive=lambda genome, rng: op_congestion_shift(
                genome, model, rng, shift_ratio=0.20, max_tries=35
            ),
        )
        name = "Min-Max Congestion"

    ga = GeneticAlgorithm(problem, cfg)
    best_x, _ = ga.run()
    best_x = np.asarray(best_x, dtype=float)

    # normalize to a well-defined operating point
    if mode == "mincost":
        best_x = model.repair(best_x, meet_demands=True)
    else:
        best_x = model.repair_demand_only(best_x)

    return BaselineResult(
        G=G,
        commodities=commodities,
        model=model,
        best_x=best_x,
        history_best=list(getattr(ga, "history_best", [])),
        name=name,
    )


# ============================ Shared Helpers ============================


def path_survives(G_att: nx.DiGraph, path: Sequence[Any]) -> bool:
    """Path survives if all directed edges along it remain."""
    for u, v in zip(path[:-1], path[1:]):
        if not (G_att.has_node(u) and G_att.has_node(v) and G_att.has_edge(u, v)):
            return False
    return True


def aggregate_edge_flow(paths: Sequence[Sequence[Any]], x: np.ndarray, eps: float = 1e-12) -> Dict[Tuple[Any, Any], float]:
    edge_flow: Dict[Tuple[Any, Any], float] = {}
    x = np.asarray(x, dtype=float).reshape(-1)
    for p, f in enumerate(x):
        if float(f) <= eps:
            continue
        path = paths[p]
        for u, v in zip(path[:-1], path[1:]):
            edge_flow[(u, v)] = edge_flow.get((u, v), 0.0) + float(f)
    return edge_flow


def max_utilization(edge_flow: Dict[Tuple[Any, Any], float], cap: Dict[Tuple[Any, Any], float]) -> float:
    worst = 0.0
    for e, load in edge_flow.items():
        c = float(cap.get(e, np.inf))
        if not np.isfinite(c) or c <= 1e-12:
            continue
        worst = max(worst, float(load) / c)
    return float(worst)


def _protected_terminals(model: Any) -> List[Any]:
    prot: List[Any] = []
    for c in model.commodities:
        prot.extend([c.source, c.target])
    return list(dict.fromkeys(prot))


# ============================ Resilience Tests ============================


def _pick_nodes_random(candidates: List[Any], k: int, rng: np.random.Generator) -> List[Any]:
    if k <= 0:
        return []
    k = min(k, len(candidates))
    idx = rng.choice(len(candidates), size=k, replace=False)
    return [candidates[i] for i in idx]


def _pick_nodes_targeted_bc(G: nx.DiGraph, candidates: List[Any], k: int) -> List[Any]:
    if k <= 0:
        return []
    k = min(k, len(candidates))
    bc = nx.betweenness_centrality(G.to_undirected())
    ranked = sorted(candidates, key=lambda n: bc.get(n, 0.0), reverse=True)
    return ranked[:k]


def _pick_edges_random(candidates: List[Tuple[Any, Any]], k: int, rng: np.random.Generator) -> List[Tuple[Any, Any]]:
    if k <= 0:
        return []
    k = min(k, len(candidates))
    idx = rng.choice(len(candidates), size=k, replace=False)
    return [candidates[i] for i in idx]


def _pick_edges_targeted_load(edge_flow: Dict[Tuple[Any, Any], float], candidates: List[Tuple[Any, Any]], k: int) -> List[Tuple[Any, Any]]:
    if k <= 0:
        return []
    k = min(k, len(candidates))
    ranked = sorted(candidates, key=lambda e: edge_flow.get(e, 0.0), reverse=True)
    return ranked[:k]


def resilience_curve(
    G: nx.DiGraph,
    model: Any,
    best_x: np.ndarray,
    unit: str = "node",              # node|edge
    attack: str = "random",          # random|targeted
    fractions: Sequence[float] = (0.0, 0.05, 0.10, 0.15, 0.20, 0.25),
    reps: int = 20,                   # only for random
    seed: int = 0,
    eps: float = 1e-10,
) -> Dict[str, List[float]]:
    """Return mean/std curves for throughput_ratio and path_survival_ratio.

    评估口径：固定策略 best_x，不做 reroute / re-opt，仅统计“原方案幸存流量”。
    """

    rng = np.random.default_rng(seed)
    total_demand = float(sum(c.demand for c in model.commodities))

    active_paths = [p for p, f in enumerate(best_x) if float(f) > eps]
    n_active = max(1, len(active_paths))

    protected = set(_protected_terminals(model))

    # attack candidates
    if unit == "node":
        candidates = [n for n in G.nodes() if n not in protected]
        n_cand = len(candidates)
    else:
        candidates = [(u, v) for u, v in G.edges()]
        n_cand = len(candidates)
        edge_flow0 = aggregate_edge_flow(model.paths, best_x, eps=eps)  # for targeted_edge_load

    xs: List[float] = []
    thr_mean: List[float] = []
    thr_std: List[float] = []
    surv_mean: List[float] = []
    surv_std: List[float] = []

    for frac in fractions:
        k = int(round(frac * n_cand))

        # number of Monte Carlo trials for this point
        T = reps if attack == "random" else 1

        thr_list = []
        surv_list = []

        for _ in range(T):
            G_att = G.copy()

            if unit == "node":
                if attack == "random":
                    rm = _pick_nodes_random(candidates, k, rng)
                else:
                    rm = _pick_nodes_targeted_bc(G, candidates, k)
                G_att.remove_nodes_from(rm)
            else:
                if attack == "random":
                    rm_e = _pick_edges_random(candidates, k, rng)
                else:
                    rm_e = _pick_edges_targeted_load(edge_flow0, candidates, k)
                G_att.remove_edges_from(rm_e)

            surviving_paths = 0
            surviving_flow = 0.0
            for p in active_paths:
                if path_survives(G_att, model.paths[p]):
                    surviving_paths += 1
                    surviving_flow += float(best_x[p])

            thr_list.append(float(surviving_flow / max(total_demand, eps)))
            surv_list.append(float(surviving_paths / n_active))

        xs.append(float(frac))
        thr_mean.append(float(np.mean(thr_list)))
        thr_std.append(float(np.std(thr_list)))
        surv_mean.append(float(np.mean(surv_list)))
        surv_std.append(float(np.std(surv_list)))

    return {
        "fraction": xs,
        "thr_mean": thr_mean,
        "thr_std": thr_std,
        "surv_mean": surv_mean,
        "surv_std": surv_std,
    }


def plot_resilience(curves: Dict[str, Dict[str, List[float]]], title: str) -> None:
    # throughput
    plt.figure(figsize=(10, 6))
    for name, d in curves.items():
        plt.errorbar(d["fraction"], d["thr_mean"], yerr=d["thr_std"], marker="o", capsize=3, label=name)
    plt.xlabel("Removed fraction")
    plt.ylabel("Throughput ratio (surviving flow / total demand)")
    plt.title(title)
    plt.grid(True, linestyle="--", alpha=0.6)
    plt.legend()
    plt.show()

    # path survival
    plt.figure(figsize=(10, 6))
    for name, d in curves.items():
        plt.errorbar(d["fraction"], d["surv_mean"], yerr=d["surv_std"], marker="s", capsize=3, label=name)
    plt.xlabel("Removed fraction")
    plt.ylabel("Active-path survival ratio")
    plt.title(title + " (Path Survival)")
    plt.grid(True, linestyle="--", alpha=0.6)
    plt.legend()
    plt.show()


# ============================ Monte Carlo Robustness ============================


def monte_carlo_robustness(
    G: nx.DiGraph,
    model: Any,
    best_x: np.ndarray,
    n: int = 1000,
    demand_sigma: float = 0.10,
    cap_low: float = 0.90,
    cap_high: float = 1.00,
    seed: int = 0,
    eps: float = 1e-12,
) -> Dict[str, Any]:
    """Policy robustness: keep path split ratios fixed; perturb demand/capacity."""

    rng = np.random.default_rng(seed)

    # commodity -> path indices
    comm_to_paths: Dict[int, List[int]] = {}
    for p, c in enumerate(model.path_commodity):
        comm_to_paths.setdefault(int(c), []).append(int(p))

    # baseline split ratios
    ratios: Dict[int, np.ndarray] = {}
    for c, idxs in comm_to_paths.items():
        flows = np.asarray([best_x[i] for i in idxs], dtype=float)
        s = float(np.sum(flows))
        if s <= eps:
            ratios[c] = np.ones(len(idxs), dtype=float) / max(1, len(idxs))
        else:
            ratios[c] = flows / s

    base_demands = np.array([float(c.demand) for c in model.commodities], dtype=float)

    base_cap: Dict[Tuple[Any, Any], float] = {(u, v): float(d.get("capacity", np.inf)) for u, v, d in G.edges(data=True)}

    max_utils: List[float] = []
    thr_scaled: List[float] = []
    overload_flags: List[int] = []

    for _ in range(int(n)):
        demand_mult = rng.normal(1.0, demand_sigma, size=base_demands.shape)
        demand_mult = np.clip(demand_mult, 0.05, None)
        scen_demands = base_demands * demand_mult

        scen_cap: Dict[Tuple[Any, Any], float] = {}
        for e, c in base_cap.items():
            if np.isfinite(c):
                scen_cap[e] = float(c * rng.uniform(cap_low, cap_high))
            else:
                scen_cap[e] = c

        # build scenario x under fixed split ratios
        x = np.zeros(model.n_paths, dtype=float)
        for c, idxs in comm_to_paths.items():
            x[idxs] = ratios[c] * float(scen_demands[c])

        edge_flow = aggregate_edge_flow(model.paths, x, eps=eps)
        worst = max_utilization(edge_flow, scen_cap)
        max_utils.append(worst)
        overload_flags.append(1 if worst > 1.0 + 1e-9 else 0)

        # capacity-feasible throughput via global scaling alpha
        alpha = 1.0
        for e, load in edge_flow.items():
            c = float(scen_cap.get(e, np.inf))
            if not np.isfinite(c) or c <= eps:
                continue
            if load > eps:
                alpha = min(alpha, c / float(load))
        alpha = float(np.clip(alpha, 0.0, 1.0))

        delivered = float(alpha * np.sum(x))
        total_demand = float(np.sum(scen_demands))
        thr_scaled.append(float(delivered / max(total_demand, eps)))

    max_utils_arr = np.asarray(max_utils, dtype=float)
    thr_arr = np.asarray(thr_scaled, dtype=float)

    return {
        "n": int(n),
        "reliability_no_overload": float(1.0 - np.mean(overload_flags)),
        "max_utilization": max_utils_arr,
        "throughput_after_scaling": thr_arr,
        "summary": {
            "mean_max_util": float(np.mean(max_utils_arr)),
            "p50_max_util": float(np.quantile(max_utils_arr, 0.50)),
            "p95_max_util": float(np.quantile(max_utils_arr, 0.95)),
            "mean_thr_scaled": float(np.mean(thr_arr)),
            "p05_thr_scaled": float(np.quantile(thr_arr, 0.05)),
        },
    }


def plot_monte_carlo(mc: Dict[str, Any], title_prefix: str) -> None:
    max_util = mc["max_utilization"]
    thr = mc["throughput_after_scaling"]

    plt.figure(figsize=(10, 5))
    plt.hist(max_util, bins=40, alpha=0.85)
    plt.axvline(1.0, linestyle="--", linewidth=2, label="Util=1.0")
    plt.xlabel("Worst utilization (max load/cap)")
    plt.ylabel("Count")
    plt.title(f"{title_prefix}: Monte Carlo Worst Utilization")
    plt.grid(True, linestyle="--", alpha=0.5)
    plt.legend()
    plt.show()

    plt.figure(figsize=(10, 5))
    plt.hist(thr, bins=40, alpha=0.85)
    plt.xlabel("Throughput ratio after capacity scaling")
    plt.ylabel("Count")
    plt.title(f"{title_prefix}: Monte Carlo Capacity-feasible Throughput")
    plt.grid(True, linestyle="--", alpha=0.5)
    plt.show()


# ============================ Main ============================


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["mincost", "minmax"], default="minmax")

    parser.add_argument("--attack_unit", choices=["node", "edge"], default="node")
    parser.add_argument("--attack_type", choices=["random", "targeted"], default="random")
    parser.add_argument("--reps", type=int, default=20, help="random attack repeats per point")

    parser.add_argument("--mc", type=int, default=500)
    parser.add_argument("--demand_sigma", type=float, default=0.10)
    parser.add_argument("--cap_low", type=float, default=0.90)
    parser.add_argument("--cap_high", type=float, default=1.00)

    parser.add_argument("--seed", type=int, default=11)
    args = parser.parse_args()

    baseline = solve_baseline(mode=args.mode, seed=args.seed)
    G, model, best_x = baseline.G, baseline.model, baseline.best_x

    # baseline diagnostics
    edge_flow0 = aggregate_edge_flow(model.paths, best_x)
    base_cap = {(u, v): float(d.get("capacity", np.inf)) for u, v, d in G.edges(data=True)}
    worst0 = max_utilization(edge_flow0, base_cap)
    total_demand = float(sum(c.demand for c in model.commodities))

    print("=" * 72)
    print(f"Library package: {PKG_NAME}")
    print(f"Baseline solved: {baseline.name}")
    print(f"Total demand: {total_demand:.3f}")
    print(f"Active paths: {int(np.sum(best_x > 1e-8))}/{model.n_paths}")
    print(f"Worst utilization (baseline): {worst0:.3f}")

    # 1) Resilience
    fractions = [0.0, 0.05, 0.10, 0.15, 0.20, 0.25]

    curves: Dict[str, Dict[str, List[float]]] = {}

    # random
    if args.attack_type == "random":
        curves[f"Random-{args.attack_unit}"] = resilience_curve(
            G,
            model,
            best_x,
            unit=args.attack_unit,
            attack="random",
            fractions=fractions,
            reps=max(1, int(args.reps)),
            seed=args.seed + 1,
        )
    else:
        # targeted
        # targeted for edge uses load ranking; for node uses betweenness
        curves[f"Targeted-{args.attack_unit}"] = resilience_curve(
            G,
            model,
            best_x,
            unit=args.attack_unit,
            attack="targeted",
            fractions=fractions,
            reps=1,
            seed=args.seed + 2,
        )

    plot_resilience(curves, title=f"Resilience ({baseline.name})")

    # 2) Monte Carlo robustness
    mc = monte_carlo_robustness(
        G,
        model,
        best_x,
        n=int(args.mc),
        demand_sigma=float(args.demand_sigma),
        cap_low=float(args.cap_low),
        cap_high=float(args.cap_high),
        seed=args.seed + 3,
    )

    print("=" * 72)
    print("Monte Carlo robustness summary")
    print(f"N = {mc['n']}")
    print(f"Reliability (no overload): {mc['reliability_no_overload']:.2%}")
    for k, v in mc["summary"].items():
        print(f"  {k}: {v:.4f}")

    plot_monte_carlo(mc, title_prefix=f"{baseline.name}")

    # --- export (append-only) ---
    from src.exporters import export_resilience_curve, export_perturbation_table

    if curves:
        first_key = next(iter(curves))
        curve = curves[first_key]
        export_resilience_curve(
            curve["fraction"],
            curve["thr_mean"],
            stderr=curve["thr_std"],
            out_csv="outputs/exports/resilience_curve.csv",
        )

    base_alpha = 1.0
    for e, load in edge_flow0.items():
        c = float(base_cap.get(e, np.inf))
        if not np.isfinite(c) or c <= 1e-12:
            continue
        if float(load) > 1e-12:
            base_alpha = min(base_alpha, c / float(load))
    base_alpha = float(np.clip(base_alpha, 0.0, 1.0))
    base_thr = float(base_alpha * np.sum(best_x) / max(total_demand, 1e-12))

    max_util_arr = np.asarray(mc["max_utilization"], dtype=float)
    thr_arr = np.asarray(mc["throughput_after_scaling"], dtype=float)
    n_mc = int(mc["n"])
    stderr_max = float(np.std(max_util_arr) / np.sqrt(n_mc)) if n_mc > 1 else None
    stderr_thr = float(np.std(thr_arr) / np.sqrt(n_mc)) if n_mc > 1 else None

    scenario = f"demand_sigma={args.demand_sigma}, cap=[{args.cap_low},{args.cap_high}]"

    def _delta_pct(base: float, pert: float):
        if base == 0:
            return None
        return float((pert - base) / base * 100.0)

    rows = [
        {
            "scenario": scenario,
            "metric_name": "mean_max_util",
            "baseline_value": float(worst0),
            "perturbed_value": float(mc["summary"]["mean_max_util"]),
            "delta_pct": _delta_pct(float(worst0), float(mc["summary"]["mean_max_util"])),
            "mc_runs": n_mc,
            "stderr": stderr_max,
            "note": f"mode={args.mode}",
        },
        {
            "scenario": scenario,
            "metric_name": "mean_thr_scaled",
            "baseline_value": float(base_thr),
            "perturbed_value": float(mc["summary"]["mean_thr_scaled"]),
            "delta_pct": _delta_pct(float(base_thr), float(mc["summary"]["mean_thr_scaled"])),
            "mc_runs": n_mc,
            "stderr": stderr_thr,
            "note": f"mode={args.mode}",
        },
    ]
    export_perturbation_table(rows, out_csv="outputs/robust/perturbation_table.csv")


if __name__ == "__main__":
    main()
