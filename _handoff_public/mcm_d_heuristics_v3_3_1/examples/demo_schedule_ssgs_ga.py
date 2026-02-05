"""\
Example: Scheduling via Priority-List GA + SSGS decoder.

Chromosome encodes a permutation of tasks; the decoder builds a feasible schedule
that respects precedence + machine capacity. GA searches only permutations.
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import numpy as np

from mcm_d_heuristics_v3_3 import GAConfig, GeneticAlgorithm, OptimizationProblem
from mcm_d_heuristics_v3_3.schedule import Task, SSGSDecoder, makespan_objective


def main() -> None:
    # Tasks: id, duration, machine
    tasks = [
        Task(0, 3, "M1"),
        Task(1, 2, "M1"),
        Task(2, 4, "M2"),
        Task(3, 1, "M2"),
        Task(4, 3, "M1"),
    ]
    # Precedence constraints (DAG)
    preds = {
        2: [0],
        3: [1],
        4: [2, 3],
    }
    decoder = SSGSDecoder(tasks, predecessors=preds)

    # GA permutation encoding uses 0..n-1, perfect for task ids above.
    n = len(tasks)
    problem = OptimizationProblem(
        objective=makespan_objective(decoder),
        decoder=lambda perm: list(map(int, perm)),
    )

    cfg = GAConfig(
        encoding="permutation",
        n_pop=100,
        max_gen=250,
        cx_rate=0.9,
        mut_rate=0.05,
        elitism_k=2,
        tournament_k=3,
        seed=11,
        perm_size=n,
    )

    ga = GeneticAlgorithm(problem, cfg)
    best_perm, best_cost = ga.run()

    print("Best makespan:", best_cost)
    print("Best priority list:", best_perm)

    res = decoder.decode(best_perm)
    print("Schedule (task: start-end @ machine):")
    for tid in sorted(res.start_times.keys()):
        t = decoder.tasks[tid]
        print(f"  {tid}: {res.start_times[tid]:.1f}-{res.end_times[tid]:.1f} @ {t.machine}")

    # --- 新增可视化 ---
    import matplotlib.pyplot as plt
    import mcm_d_heuristics_v3_3.viz as viz

    # 1) 收敛曲线
    viz.plot_convergence(ga.history_best, title="Scheduling GA Convergence (GA + SSGS)")

    # 2) 甘特图：v3.3 里是 res.gantt（不是 gantt_chart）
    if hasattr(res, "gantt"):
        viz.plot_gantt(res.gantt, title="Optimal Schedule Gantt Chart")
        plt.show()
    else:
        print("Warning: Decoder result does not contain 'gantt' attribute; cannot plot Gantt chart.")

    # --- export (append-only) ---
    import time
    from src.exporters import export_metrics_row

    run_id_str = time.strftime("schedule_ga_%Y%m%d_%H%M%S")
    export_metrics_row({
        "run_id": run_id_str,
        "method": "GA_SSGS",
        "objective": float(best_cost),
        "total_cost": None,
        "max_congestion": None,
        "makespan": float(best_cost),
        "resilience_score": None,
        "feasible": True,
        "runtime_sec": None,
        "seed": getattr(cfg, "seed", None),
        "note": "",
    })


if __name__ == "__main__":
    main()
