"""
hybrid.py
Contest-grade hybrid pipeline orchestrator.

Step6 writer should read HybridRunLog.to_json()["convergence"] to draw multi-stage
convergence curves; StageLog can be used for stage comparison tables.
"""
from __future__ import annotations

import copy
import time
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import List, Optional, Any, Dict, Callable, Tuple

import numpy as np

from .problem import OptimizationProblem
from .pso import PSOConfig, ParticleSwarmOptimizer
from .ga import GAConfig, GeneticAlgorithm
from .sa import SAConfig, SimulatedAnnealing, NeighborOp


class StageKind(str, Enum):
    PSO = "pso"
    GA = "ga"
    SA = "sa"
    MP_REPAIR = "mp_repair"
    ALNS = "alns"
    LNS_MP = "lns_mp"


@dataclass
class ConvergencePoint:
    """Single convergence data point."""
    run_id: str
    phase: str
    iter: int
    best_cost: float
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "phase": self.phase,
            "iter": int(self.iter),
            "best_cost": float(self.best_cost),
            "timestamp": float(self.timestamp),
        }


@dataclass
class StageLog:
    """Execution summary for a single stage."""
    phase: str
    kind: StageKind
    seed: Optional[int]
    duration_sec: float
    n_evals_approx: Optional[int]
    best_cost: float
    best_solution_summary: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["kind"] = str(self.kind)
        return d


@dataclass
class HybridRunLog:
    """Full pipeline log."""
    run_id: str
    start_time_iso: str
    pipeline: str
    global_seed: int
    stage_logs: List[StageLog] = field(default_factory=list)
    convergence: List[ConvergencePoint] = field(default_factory=list)
    final_cost: float = float("inf")
    notes: Dict[str, Any] = field(default_factory=dict)
    end_time_iso: Optional[str] = None

    def to_json(self, max_convergence_points: Optional[int] = 5000) -> Dict[str, Any]:
        points = self.convergence
        downsample_info = None
        if max_convergence_points is not None:
            points, downsample_info = _downsample_convergence(points, int(max_convergence_points))

        notes = dict(self.notes) if self.notes is not None else {}
        if downsample_info is not None:
            notes.update(downsample_info)

        return {
            "run_id": self.run_id,
            "pipeline": self.pipeline,
            "global_seed": int(self.global_seed),
            "start_time": self.start_time_iso,
            "end_time": self.end_time_iso,
            "stages": [s.to_dict() for s in self.stage_logs],
            "convergence": [p.to_dict() for p in points],
            "final_cost": float(self.final_cost),
            "notes": notes,
        }


@dataclass
class HybridResult:
    """Pipeline execution result."""
    best_solution: Any
    best_cost: float
    log: HybridRunLog


@dataclass
class StageSpec:
    phase: str
    kind: StageKind
    seed_offset: int = 0
    pso_cfg: Optional[PSOConfig] = None
    ga_cfg: Optional[GAConfig] = None
    sa_cfg: Optional[SAConfig] = None
    neighbor_ops: Optional[List[NeighborOp]] = None
    mp_repair: Optional[Callable[[OptimizationProblem, Any], Tuple[Any, float]]] = None
    stage_notes: Optional[Dict[str, Any]] = None


def _now_iso() -> str:
    from datetime import datetime
    return datetime.now().isoformat()


def _is_finite(x: Any) -> bool:
    try:
        return bool(np.isfinite(x))
    except Exception:
        return False


def _summarize_solution(sol: Any, max_len: int = 30) -> Dict[str, Any]:
    summary: Dict[str, Any] = {"type": type(sol).__name__}
    if sol is None:
        return summary

    try:
        if hasattr(sol, "shape"):
            arr = np.asarray(sol)
            summary["shape"] = tuple(arr.shape)
            flat = arr.reshape(-1)
            head = flat[:max_len].tolist()
            summary["head"] = _json_safe(head)
            return summary
        if isinstance(sol, (list, tuple)):
            summary["shape"] = (len(sol),)
            head = list(sol)[:max_len]
            summary["head"] = _json_safe(head)
            return summary
        if np.isscalar(sol):
            summary["value"] = _json_safe(sol)
            return summary
    except Exception:
        summary["value"] = str(sol)
        return summary

    summary["value"] = str(sol)
    return summary


def _json_safe(x: Any) -> Any:
    if isinstance(x, (int, float, str, bool)) or x is None:
        return x
    if isinstance(x, np.generic):
        return x.item()
    if isinstance(x, (list, tuple)):
        return [_json_safe(v) for v in x]
    if isinstance(x, dict):
        return {str(k): _json_safe(v) for k, v in x.items()}
    return str(x)


def _downsample_convergence(
    points: List[ConvergencePoint],
    max_points: int,
) -> Tuple[List[ConvergencePoint], Optional[Dict[str, Any]]]:
    n = len(points)
    if max_points <= 0 or n <= max_points:
        return points, None

    first_idx: Dict[str, int] = {}
    last_idx: Dict[str, int] = {}
    for i, p in enumerate(points):
        if p.phase not in first_idx:
            first_idx[p.phase] = i
        last_idx[p.phase] = i

    keep = set(first_idx.values()) | set(last_idx.values())
    remaining = [i for i in range(n) if i not in keep]
    slots = max_points - len(keep)
    if slots > 0 and remaining:
        if slots >= len(remaining):
            keep.update(remaining)
        else:
            idx = np.linspace(0, len(remaining) - 1, num=slots, dtype=int)
            keep.update([remaining[int(i)] for i in idx.tolist()])

    kept_points = [points[i] for i in range(n) if i in keep]
    info = {
        "convergence_downsampled": True,
        "original_points": int(n),
        "kept_points": int(len(kept_points)),
    }
    return kept_points, info


def _history_to_points(
    run_id: str,
    phase: str,
    history: Optional[List[float]],
    start_iter: int,
) -> Tuple[List[ConvergencePoint], int]:
    if history is None or len(history) == 0:
        return [], start_iter
    points = []
    for i, cost in enumerate(history):
        points.append(ConvergencePoint(
            run_id=run_id,
            phase=phase,
            iter=start_iter + i,
            best_cost=float(cost),
        ))
    return points, start_iter + len(history)


def _validate_solution_and_cost(
    problem: OptimizationProblem,
    sol: Any,
    reported_cost: Optional[float],
    phase: str,
    kind: StageKind,
    notes: Dict[str, Any],
) -> float:
    if sol is None:
        raise ValueError(f"{phase}/{kind}: solution is None")

    eval_cost: Optional[float] = None
    if hasattr(problem, "evaluate_solution"):
        try:
            eval_cost = float(problem.evaluate_solution(sol))
        except Exception as exc:
            raise ValueError(f"{phase}/{kind}: evaluate_solution failed: {exc}") from exc
        if not _is_finite(eval_cost):
            raise ValueError(f"{phase}/{kind}: evaluate_solution returned non-finite cost")

    rep_cost = None
    if reported_cost is not None and _is_finite(reported_cost):
        rep_cost = float(reported_cost)

    if eval_cost is not None:
        if rep_cost is not None:
            diff = abs(eval_cost - rep_cost)
            tol = 1e-6 * max(1.0, abs(eval_cost), abs(rep_cost))
            if diff > tol:
                notes.setdefault("cost_mismatch", []).append({
                    "phase": phase,
                    "kind": str(kind),
                    "eval_cost": float(eval_cost),
                    "reported_cost": float(rep_cost),
                })
        return float(eval_cost)

    if rep_cost is None or not _is_finite(rep_cost):
        raise ValueError(f"{phase}/{kind}: reported cost is invalid")
    return float(rep_cost)


def extract_ga_seeds_from_pso(
    problem: OptimizationProblem,
    pso: ParticleSwarmOptimizer,
    ga_pop: int,
    top_k_from_history: int = 10,
    jitter_sigma: float = 0.10,
    seed: Optional[int] = None,
    seed_encoder: Optional[Callable[[Any], Any]] = None,
) -> List[Any]:
    """
    Seed extraction for PSO -> GA.
    Priority:
    1) Use pso.history_solutions (best-so-far sequence) if available.
    2) Fill remaining by jittering pso.best_position and decoding.
    """
    rng = np.random.default_rng(seed)
    seeds: List[Any] = []

    # 1) from history_solutions (best-so-far)
    hist = getattr(pso, "history_solutions", None)
    if hist:
        take = hist[-int(top_k_from_history):] if top_k_from_history > 0 else hist
        for sol in take:
            genome = seed_encoder(sol) if seed_encoder is not None else np.asarray(sol)
            seeds.append(genome)
            if len(seeds) >= ga_pop:
                return seeds[:ga_pop]

    # 2) jitter around best_position
    base = getattr(pso, "best_position", None)
    if base is not None and ga_pop > len(seeds):
        base = np.asarray(base, dtype=float)
        lb = getattr(problem, "lb", None)
        ub = getattr(problem, "ub", None)
        if lb is not None and ub is not None:
            lb = np.asarray(lb, dtype=float).reshape(-1)
            ub = np.asarray(ub, dtype=float).reshape(-1)
            clip_low, clip_high = lb, ub
        else:
            clip_low, clip_high = 0.0, 1.0

        while len(seeds) < ga_pop:
            noise = rng.normal(0.0, float(jitter_sigma), size=base.shape)
            cand = np.clip(base + noise, clip_low, clip_high)
            sol = problem.decode(cand)
            genome = seed_encoder(sol) if seed_encoder is not None else np.asarray(sol)
            seeds.append(genome)

    return seeds[:ga_pop]


def run_sa_traced(
    sa: SimulatedAnnealing,
    init_solution: Any,
    run_id: str,
    start_iter_idx: int,
    phase: str,
) -> Tuple[List[ConvergencePoint], Any, float]:
    """Run SA and return coarse-grained convergence points."""
    sa.init_solution_fn = lambda rng: init_solution
    best_sol, best_cost = sa.run()

    points: List[ConvergencePoint] = []
    current_iter = start_iter_idx
    step = int(sa.cfg.iters_per_T)
    for cost in sa.history_best:
        current_iter += step
        points.append(ConvergencePoint(
            run_id=run_id,
            phase=phase,
            iter=current_iter,
            best_cost=float(cost),
        ))
    return points, best_sol, best_cost


def _coerce_seed_population(seeds: List[Any], notes: Optional[Dict[str, Any]] = None) -> Any:
    arr = np.asarray(seeds)
    if arr.dtype == object or arr.ndim < 2:
        if notes is not None:
            notes["seed_population_left_as_list"] = True
            notes["seed_population_object_dtype"] = True
            notes["seed_population_hint"] = "Provide seed_encoder_for_ga for fixed-length genomes."
        return seeds
    try:
        _ = np.vstack(arr)
    except Exception:
        if notes is not None:
            notes["seed_population_left_as_list"] = True
            notes["seed_population_shape_mismatch"] = True
            notes["seed_population_hint"] = "Provide seed_encoder_for_ga for fixed-length genomes."
        return seeds
    return arr


def run_pipeline(
    problem: OptimizationProblem,
    stages: List[StageSpec],
    pipeline_name: str,
    global_seed: int,
    run_id: Optional[str] = None,
    seed_encoder_for_ga: Optional[Callable[[Any], Any]] = None,
    max_convergence_points: int = 5000,
) -> HybridResult:
    if run_id is None:
        run_id = f"hybrid_run_{int(time.time())}"

    hlog = HybridRunLog(
        run_id=run_id,
        start_time_iso=_now_iso(),
        pipeline=pipeline_name,
        global_seed=global_seed,
        notes={"max_convergence_points": int(max_convergence_points)},
    )

    incumbent_sol = None
    incumbent_cost = float("inf")
    current_iter_base = 0
    last_pso: Optional[ParticleSwarmOptimizer] = None

    for stage in stages:
        t0 = time.time()
        phase = stage.phase
        kind = stage.kind

        stage_seed = None
        if kind == StageKind.PSO and stage.pso_cfg is not None:
            if stage.pso_cfg.seed is None:
                stage.pso_cfg.seed = int(global_seed + stage.seed_offset)
            stage_seed = stage.pso_cfg.seed
            pso = ParticleSwarmOptimizer(problem, stage.pso_cfg)
            sol, rep_cost = pso.run()
            best_cost = _validate_solution_and_cost(problem, sol, rep_cost, phase, kind, hlog.notes)
            pts, current_iter_base = _history_to_points(run_id, phase, getattr(pso, "history_best", None), current_iter_base)
            if not pts:
                pts = [ConvergencePoint(run_id=run_id, phase=phase, iter=current_iter_base, best_cost=best_cost)]
                current_iter_base += 1
            hlog.convergence.extend(pts)
            last_pso = pso
            n_evals = stage.pso_cfg.num_particles * stage.pso_cfg.max_iter

        elif kind == StageKind.GA and stage.ga_cfg is not None:
            if stage.ga_cfg.seed is None:
                stage.ga_cfg.seed = int(global_seed + stage.seed_offset)
            stage_seed = stage.ga_cfg.seed
            if stage.ga_cfg.seed_population is None and last_pso is not None:
                seeds = extract_ga_seeds_from_pso(
                    problem=problem,
                    pso=last_pso,
                    ga_pop=stage.ga_cfg.n_pop,
                    seed=int(global_seed + stage.seed_offset),
                    seed_encoder=seed_encoder_for_ga,
                )
                if len(seeds) > 0:
                    stage.ga_cfg.seed_population = _coerce_seed_population(seeds, hlog.notes)
            ga = GeneticAlgorithm(problem, stage.ga_cfg)
            sol, rep_cost = ga.run()
            best_cost = _validate_solution_and_cost(problem, sol, rep_cost, phase, kind, hlog.notes)
            pts, current_iter_base = _history_to_points(run_id, phase, getattr(ga, "history_best", None), current_iter_base)
            if not pts:
                pts = [ConvergencePoint(run_id=run_id, phase=phase, iter=current_iter_base, best_cost=best_cost)]
                current_iter_base += 1
            hlog.convergence.extend(pts)
            n_evals = stage.ga_cfg.n_pop * stage.ga_cfg.max_gen

        elif kind == StageKind.SA and stage.sa_cfg is not None:
            if stage.sa_cfg.seed is None:
                stage.sa_cfg.seed = int(global_seed + stage.seed_offset)
            stage_seed = stage.sa_cfg.seed
            if incumbent_sol is None:
                raise ValueError(f"{phase}/{kind}: incumbent solution is None for SA init")
            if not stage.neighbor_ops:
                raise ValueError(f"{phase}/{kind}: neighbor_ops must be provided for SA")
            sa = SimulatedAnnealing(
                problem=problem,
                init_solution=lambda rng: incumbent_sol,
                neighbor_ops=stage.neighbor_ops,
                config=stage.sa_cfg,
            )
            pts, sol, rep_cost = run_sa_traced(sa, incumbent_sol, run_id, current_iter_base, phase)
            best_cost = _validate_solution_and_cost(problem, sol, rep_cost, phase, kind, hlog.notes)
            if pts:
                current_iter_base = pts[-1].iter
            else:
                current_iter_base += 1
                pts = [ConvergencePoint(run_id=run_id, phase=phase, iter=current_iter_base, best_cost=best_cost)]
            hlog.convergence.extend(pts)
            n_evals = len(pts) * int(stage.sa_cfg.iters_per_T)

        elif kind == StageKind.MP_REPAIR and stage.mp_repair is not None:
            if incumbent_sol is None:
                raise ValueError(f"{phase}/{kind}: incumbent solution is None for MP repair")
            sol, rep_cost = stage.mp_repair(problem, incumbent_sol)
            best_cost = _validate_solution_and_cost(problem, sol, rep_cost, phase, kind, hlog.notes)
            hlog.convergence.append(ConvergencePoint(
                run_id=run_id,
                phase=phase,
                iter=current_iter_base,
                best_cost=best_cost,
            ))
            current_iter_base += 1
            n_evals = None

        else:
            raise ValueError(f"Unsupported stage kind or missing config: {phase}/{kind}")

        duration_sec = time.time() - t0
        hlog.stage_logs.append(StageLog(
            phase=phase,
            kind=kind,
            seed=stage_seed,
            duration_sec=float(duration_sec),
            n_evals_approx=n_evals,
            best_cost=float(best_cost),
            best_solution_summary=_summarize_solution(sol),
        ))

        if best_cost < incumbent_cost:
            incumbent_sol = sol
            incumbent_cost = float(best_cost)

    hlog.final_cost = float(incumbent_cost)
    hlog.end_time_iso = _now_iso()

    return HybridResult(best_solution=incumbent_sol, best_cost=incumbent_cost, log=hlog)


def recipe_pso_ga_sa(
    problem: OptimizationProblem,
    pso_cfg: PSOConfig,
    ga_cfg: GAConfig,
    sa_cfg: SAConfig,
    sa_neighbor_ops: List[NeighborOp],
    run_id: str = "hybrid_run",
    global_seed: int = 42,
    pipeline_name: str = "PSO->GA->SA",
    seed_encoder_for_ga: Optional[Callable[[Any], Any]] = None,
    max_convergence_points: int = 5000,
) -> HybridResult:
    stages = [
        StageSpec(phase="PSO", kind=StageKind.PSO, seed_offset=0, pso_cfg=pso_cfg),
        StageSpec(phase="GA", kind=StageKind.GA, seed_offset=1, ga_cfg=ga_cfg),
        StageSpec(phase="SA", kind=StageKind.SA, seed_offset=2, sa_cfg=sa_cfg, neighbor_ops=sa_neighbor_ops),
    ]
    return run_pipeline(
        problem=problem,
        stages=stages,
        pipeline_name=pipeline_name,
        global_seed=global_seed,
        run_id=run_id,
        seed_encoder_for_ga=seed_encoder_for_ga,
        max_convergence_points=max_convergence_points,
    )


def recipe_memetic_ga(
    problem: OptimizationProblem,
    ga_cfg: GAConfig,
    local_improve: Optional[Callable[[np.ndarray, np.random.Generator], np.ndarray]] = None,
    global_seed: int = 42,
    pipeline_name: str = "Memetic-GA(stagnation-trigger)",
    max_convergence_points: int = 5000,
) -> HybridResult:
    if local_improve is not None:
        ga_cfg.custom_mutation_aggressive = local_improve
        if ga_cfg.stagnation_patience <= 0:
            ga_cfg.stagnation_patience = 10
        ga_cfg.stagnation_elite_fraction = 1.0
        ga_cfg.stagnation_aggressive_steps = 1

    stages = [
        StageSpec(phase="GA", kind=StageKind.GA, seed_offset=0, ga_cfg=ga_cfg),
    ]
    return run_pipeline(
        problem=problem,
        stages=stages,
        pipeline_name=pipeline_name,
        global_seed=global_seed,
        run_id="memetic_ga",
        max_convergence_points=max_convergence_points,
    )


def recipe_matheuristic_repair(
    problem: OptimizationProblem,
    ga_cfg: GAConfig,
    mp_repair_callable: Callable[[OptimizationProblem, Any], Tuple[Any, float]],
    global_seed: int = 42,
    pipeline_name: str = "GA->MP-Repair",
    max_convergence_points: int = 5000,
) -> HybridResult:
    stages = [
        StageSpec(phase="GA", kind=StageKind.GA, seed_offset=0, ga_cfg=ga_cfg),
        StageSpec(phase="MP_REPAIR", kind=StageKind.MP_REPAIR, seed_offset=1, mp_repair=mp_repair_callable),
    ]
    return run_pipeline(
        problem=problem,
        stages=stages,
        pipeline_name=pipeline_name,
        global_seed=global_seed,
        run_id="ga_mp_repair",
        max_convergence_points=max_convergence_points,
    )


def recipe_multistart_pso_sa(
    problem: OptimizationProblem,
    pso_cfg: PSOConfig,
    n_starts: int,
    sa_cfg: SAConfig,
    sa_neighbor_ops: List[NeighborOp],
    global_seed: int = 42,
    pipeline_name: str = "MS-PSO->SA",
    run_id: str = "ms_pso_sa",
    seed_encoder_for_ga: Optional[Callable[[Any], Any]] = None,
    max_convergence_points: int = 5000,
) -> HybridResult:
    """
    Multi-start PSO followed by SA.

    什么时候用：
    - 连续优化、多峰/噪声函数：多个 PSO 起点增加全局探索，减少早熟收敛
    - PSO 易陷入局部最优：多起点分散搜索，incumbent 自动选择最优起点
    - 评估有噪声：多起点鲁棒性更好
    不适用：
    - 评估成本极高：n_starts 次 PSO 会显著增加评估次数
    - 单峰凸问题：单一 PSO 通常足够
    """
    stages: List[StageSpec] = []
    for i in range(n_starts):
        cfg_copy = copy.deepcopy(pso_cfg)
        cfg_copy.seed = global_seed + i
        stages.append(StageSpec(
            phase=f"PSO_{i}",
            kind=StageKind.PSO,
            seed_offset=i,
            pso_cfg=cfg_copy,
        ))
    
    stages.append(StageSpec(
        phase="SA",
        kind=StageKind.SA,
        seed_offset=n_starts,
        sa_cfg=sa_cfg,
        neighbor_ops=sa_neighbor_ops,
    ))
    
    return run_pipeline(
        problem=problem,
        stages=stages,
        pipeline_name=pipeline_name,
        global_seed=global_seed,
        run_id=run_id,
        seed_encoder_for_ga=seed_encoder_for_ga,
        max_convergence_points=max_convergence_points,
    )


def build_vns_local_improve(
    problem: OptimizationProblem,
    neighborhood_ops: List[Callable[[np.ndarray, np.random.Generator], np.ndarray]],
    tries_per_neighborhood: int = 5,
    max_rounds: int = 50,
) -> Callable[[np.ndarray, np.random.Generator], np.ndarray]:
    """
    构建 VNS 局部改进函数。
    
    Returns:
        local_improve(genome, rng) -> improved_genome
    """
    def local_improve(genome: np.ndarray, rng: np.random.Generator) -> np.ndarray:
        decode_fn = getattr(problem, "decode", None)
        current_genome = genome.copy()
        decoded = decode_fn(current_genome) if callable(decode_fn) else current_genome
        best_cost = problem.evaluate_solution(decoded)
        
        for round_idx in range(max_rounds):
            improved = False
            for n_idx, neighbor_op in enumerate(neighborhood_ops):
                for _ in range(tries_per_neighborhood):
                    candidate = neighbor_op(current_genome, rng)
                    decoded_candidate = decode_fn(candidate) if callable(decode_fn) else candidate
                    candidate_cost = problem.evaluate_solution(decoded_candidate)
                    
                    if candidate_cost < best_cost:
                        current_genome = candidate
                        best_cost = candidate_cost
                        improved = True
                        break  # 回到第一个邻域
                
                if improved:
                    break  # 回到第一个邻域
            
            if not improved:
                break  # 所有邻域都无改进，停止
        
        return current_genome
    
    return local_improve


def recipe_ga_vns(
    problem: OptimizationProblem,
    ga_cfg: GAConfig,
    neighborhood_ops: List[Callable[[np.ndarray, np.random.Generator], np.ndarray]],
    tries_per_neighborhood: int = 5,
    max_rounds: int = 50,
    global_seed: int = 42,
    pipeline_name: str = "GA+VNS",
    max_convergence_points: int = 5000,
) -> HybridResult:
    """
    GA with Variable Neighborhood Search local improvement.

    什么时候用：
    - 组合结构+多个自然邻域：如 TSP 的 2-opt/3-opt/swap，排程的 swap/shift
    - 单一 flip/swap 邻域不稳定：VNS 系统性探索多邻域，避免局部停滞
    - 需要精细局部优化：GA 的多样性 + VNS 的局部强化
    不适用：
    - 连续优化：邻域操作应定义为离散变换
    - 邻域定义不明确：需要清晰的 neighborhood_ops 实现
    """
    local_improve = build_vns_local_improve(
        problem=problem,
        neighborhood_ops=neighborhood_ops,
        tries_per_neighborhood=tries_per_neighborhood,
        max_rounds=max_rounds,
    )
    return recipe_memetic_ga(
        problem=problem,
        ga_cfg=ga_cfg,
        local_improve=local_improve,
        global_seed=global_seed,
        pipeline_name=pipeline_name,
        max_convergence_points=max_convergence_points,
    )


@dataclass
class ALNSConfig:
    """Adaptive Large Neighborhood Search configuration."""
    max_iter: int = 2000
    init_temp: float = 1.0
    alpha: float = 0.995
    update_every: int = 50
    seed: Optional[int] = None


def run_alns(
    problem: OptimizationProblem,
    init_solution: Any,
    destroy_ops: List[Callable[[Any, np.random.Generator], Any]],
    repair_ops: List[Callable[[Any, np.random.Generator], Any]],
    cfg: ALNSConfig,
    run_id: str,
    phase: str,
) -> Tuple[Any, float, List[float], Dict[str, Any]]:
    """
    Run Adaptive Large Neighborhood Search.

    Returns:
        (best_sol, best_cost, history_best, stage_notes)
    """
    rng = np.random.default_rng(cfg.seed)
    current_sol = init_solution
    current_cost = float(problem.evaluate_solution(current_sol))
    best_sol = current_sol
    best_cost = current_cost
    history_best: List[float] = [best_cost]
    
    n_destroy = len(destroy_ops)
    n_repair = len(repair_ops)
    destroy_scores = np.ones(n_destroy, dtype=float)
    repair_scores = np.ones(n_repair, dtype=float)
    
    T = float(cfg.init_temp)
    stage_notes: Dict[str, Any] = {}
    
    for iter_idx in range(cfg.max_iter):
        # 自适应选择 destroy 和 repair
        destroy_probs = destroy_scores / (destroy_scores.sum() + 1e-10)
        repair_probs = repair_scores / (repair_scores.sum() + 1e-10)
        destroy_idx = rng.choice(n_destroy, p=destroy_probs)
        repair_idx = rng.choice(n_repair, p=repair_probs)
        
        destroy_op = destroy_ops[destroy_idx]
        repair_op = repair_ops[repair_idx]
        
        # destroy + repair
        partial = destroy_op(current_sol, rng)
        new_sol = repair_op(partial, rng)
        new_cost = float(problem.evaluate_solution(new_sol))
        
        # SA-like 接受准则
        delta = new_cost - current_cost
        accept = False
        if delta < 0:
            accept = True
        else:
            if T > 1e-10:
                prob = np.exp(-delta / T)
                accept = rng.random() < prob
        
        if accept:
            current_sol = new_sol
            current_cost = new_cost
            
            # 更新权重（简单：成功次数）
            if delta < 0:
                destroy_scores[destroy_idx] += 1.0
                repair_scores[repair_idx] += 1.0
        
        # 更新 best
        if current_cost < best_cost:
            best_sol = current_sol
            best_cost = current_cost
        
        history_best.append(best_cost)
        
        # 更新温度
        T *= cfg.alpha
        
        # 定期更新概率（可选的重置/归一化）
        if (iter_idx + 1) % cfg.update_every == 0:
            destroy_scores = destroy_scores * 0.9 + 0.1  # 衰减避免过度集中
            repair_scores = repair_scores * 0.9 + 0.1
    
    stage_notes["final_temperature"] = float(T)
    stage_notes["destroy_scores"] = destroy_scores.tolist()
    stage_notes["repair_scores"] = repair_scores.tolist()
    
    return best_sol, best_cost, history_best, stage_notes


def recipe_alns(
    problem: OptimizationProblem,
    init_solution: Any,
    destroy_ops: List[Callable[[Any, np.random.Generator], Any]],
    repair_ops: List[Callable[[Any, np.random.Generator], Any]],
    cfg: ALNSConfig,
    global_seed: int = 42,
    pipeline_name: str = "ALNS",
    run_id: str = "alns",
    max_convergence_points: int = 5000,
) -> HybridResult:
    """
    Adaptive Large Neighborhood Search.

    什么时候用：
    - 强约束组合优化：destroy/repair 天然适配约束处理
    - 可定义破坏-修复操作：如车辆路径的 remove-insert，排程的 job-removal-reinsert
    - 不可行解多：repair 机制保证可行性
    不适用：
    - 连续优化：destroy/repair 通常为离散操作
    - 没有明确的 destroy/repair 语义：需要领域知识定义操作
    """
    if cfg.seed is None:
        cfg.seed = global_seed
    
    hlog = HybridRunLog(
        run_id=run_id,
        start_time_iso=_now_iso(),
        pipeline=pipeline_name,
        global_seed=global_seed,
        notes={"max_convergence_points": int(max_convergence_points)},
    )
    
    phase = "ALNS"
    t0 = time.time()
    best_sol, best_cost, history_best, stage_notes = run_alns(
        problem=problem,
        init_solution=init_solution,
        destroy_ops=destroy_ops,
        repair_ops=repair_ops,
        cfg=cfg,
        run_id=run_id,
        phase=phase,
    )
    
    # 写入 convergence
    pts = []
    for i, cost in enumerate(history_best):
        pts.append(ConvergencePoint(
            run_id=run_id,
            phase=phase,
            iter=i,
            best_cost=float(cost),
        ))
    hlog.convergence.extend(pts)
    
    duration_sec = time.time() - t0
    hlog.stage_logs.append(StageLog(
        phase=phase,
        kind=StageKind.ALNS,
        seed=cfg.seed,
        duration_sec=float(duration_sec),
        n_evals_approx=cfg.max_iter,
        best_cost=float(best_cost),
        best_solution_summary=_summarize_solution(best_sol),
    ))
    
    # 合并 stage_notes
    hlog.notes.update(stage_notes)
    hlog.final_cost = float(best_cost)
    hlog.end_time_iso = _now_iso()
    
    return HybridResult(best_solution=best_sol, best_cost=best_cost, log=hlog)


@dataclass
class LNSMPConfig:
    """LNS with Mathematical Programming repair configuration."""
    max_iter: int = 500
    init_temp: float = 1.0
    alpha: float = 0.995
    seed: Optional[int] = None


def run_lns_mp(
    problem: OptimizationProblem,
    init_solution: Any,
    destroy_ops: List[Callable[[Any, np.random.Generator], Any]],
    mp_repair_callable: Callable[[OptimizationProblem, Any], Tuple[Any, float]],
    cfg: LNSMPConfig,
    run_id: str,
    phase: str,
) -> Tuple[Any, float, List[float], Dict[str, Any]]:
    """
    Run LNS with MP repair.

    Returns:
        (best_sol, best_cost, history_best, stage_notes)
    """
    rng = np.random.default_rng(cfg.seed)
    current_sol = init_solution
    current_cost = float(problem.evaluate_solution(current_sol))
    best_sol = current_sol
    best_cost = current_cost
    history_best: List[float] = [best_cost]
    
    T = float(cfg.init_temp)
    stage_notes: Dict[str, Any] = {}
    
    for iter_idx in range(cfg.max_iter):
        # 随机选择 destroy 操作
        destroy_op = rng.choice(destroy_ops)
        partial = destroy_op(current_sol, rng)
        
        # MP repair
        sol, rep_cost = mp_repair_callable(problem, partial)
        
        # 验证并获取 cost
        notes: Dict[str, Any] = {}
        new_cost = _validate_solution_and_cost(problem, sol, rep_cost, phase, StageKind.LNS_MP, notes)
        
        if notes.get("cost_mismatch"):
            stage_notes.setdefault("cost_mismatches", []).extend(notes["cost_mismatch"])
        
        # SA-like 接受准则
        delta = new_cost - current_cost
        accept = False
        if delta < 0:
            accept = True
        else:
            if T > 1e-10:
                prob = np.exp(-delta / T)
                accept = rng.random() < prob
        
        if accept:
            current_sol = sol
            current_cost = new_cost
        
        # 更新 best
        if current_cost < best_cost:
            best_sol = current_sol
            best_cost = current_cost
        
        history_best.append(best_cost)
        
        # 更新温度
        T *= cfg.alpha
    
    stage_notes["final_temperature"] = float(T)
    
    return best_sol, best_cost, history_best, stage_notes


def recipe_ga_lns_mp(
    problem: OptimizationProblem,
    ga_cfg: GAConfig,
    destroy_ops: List[Callable[[Any, np.random.Generator], Any]],
    mp_repair_callable: Callable[[OptimizationProblem, Any], Tuple[Any, float]],
    lns_cfg: Optional[LNSMPConfig] = None,
    global_seed: int = 42,
    pipeline_name: str = "GA->LNS-MP",
    run_id: str = "ga_lns_mp",
    max_convergence_points: int = 5000,
) -> HybridResult:
    """
    GA followed by LNS with Mathematical Programming repair.

    什么时候用：
    - 结构离散+局部子问题可 LP/MIP 精修：如排程的子时间段优化、网络流的子路径优化
    - 运筹味最浓：GA 探索结构，LNS 破坏局部，MP 精确修复
    - 混合整数规划松弛：destroy 产生部分解，MP 补全并优化
    不适用：
    - 没有可用的 MP solver：需要实现 mp_repair_callable
    - destroy 无法产生有意义的子问题：需要合理的部分解语义
    """
    if lns_cfg is None:
        lns_cfg = LNSMPConfig()
    
    # Stage 1: GA
    ga_stages = [
        StageSpec(phase="GA", kind=StageKind.GA, seed_offset=0, ga_cfg=ga_cfg),
    ]
    ga_result = run_pipeline(
        problem=problem,
        stages=ga_stages,
        pipeline_name="GA",
        global_seed=global_seed,
        run_id=f"{run_id}_ga",
        max_convergence_points=max_convergence_points,
    )
    
    # Stage 2: LNS-MP
    if lns_cfg.seed is None:
        lns_cfg.seed = global_seed + 1000
    
    hlog = ga_result.log
    phase = "LNS_MP"
    t0 = time.time()
    
    # 更新 GA 阶段的 convergence 点的 run_id 以匹配最终 run_id
    for pt in hlog.convergence:
        pt.run_id = run_id
    
    best_sol, best_cost, history_best, stage_notes = run_lns_mp(
        problem=problem,
        init_solution=ga_result.best_solution,
        destroy_ops=destroy_ops,
        mp_repair_callable=mp_repair_callable,
        cfg=lns_cfg,
        run_id=run_id,
        phase=phase,
    )
    
    # 合并 convergence（继续 GA 的迭代计数）
    current_iter_base = max([p.iter for p in hlog.convergence], default=0) + 1 if hlog.convergence else 0
    pts = []
    for i, cost in enumerate(history_best):
        pts.append(ConvergencePoint(
            run_id=run_id,
            phase=phase,
            iter=current_iter_base + i,
            best_cost=float(cost),
        ))
    hlog.convergence.extend(pts)
    
    duration_sec = time.time() - t0
    hlog.stage_logs.append(StageLog(
        phase=phase,
        kind=StageKind.LNS_MP,
        seed=lns_cfg.seed,
        duration_sec=float(duration_sec),
        n_evals_approx=lns_cfg.max_iter,
        best_cost=float(best_cost),
        best_solution_summary=_summarize_solution(best_sol),
    ))
    
    # 更新 pipeline name, run_id 和 final cost
    hlog.pipeline = pipeline_name
    hlog.run_id = run_id
    if best_cost < hlog.final_cost:
        hlog.final_cost = float(best_cost)
    
    hlog.notes.update(stage_notes)
    hlog.end_time_iso = _now_iso()
    
    return HybridResult(best_solution=best_sol, best_cost=best_cost, log=hlog)
