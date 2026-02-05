"""
examples/demo_optimization.py
MIP schedule parsing demo with Visualizer integration.
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import numpy as np

from mcm_d_heuristics_v3_3.opt_algo import OptimizationSolver
from mcm_d_heuristics_v3_3.viz import Visualizer


def parse_binary_schedule(
    x: np.ndarray,
    jobs: list[str],
    machines: list[str],
    time_slots: list[int],
    durations: dict[tuple[str, str], int],
) -> list[dict]:
    tasks = []
    n_m = len(machines)
    n_t = len(time_slots)
    for i, job in enumerate(jobs):
        for j, machine in enumerate(machines):
            dur = durations[(job, machine)]
            for t in time_slots:
                idx = (i * n_m + j) * n_t + t
                if x[idx] > 0.5:
                    tasks.append({"Machine": machine, "Start": t, "Duration": dur, "Job": job})
    return tasks


def main() -> None:
    # 假设是 Job Shop 调度问题：min sum(Makespan)
    jobs = ["J1", "J2"]
    machines = ["Machine A", "Machine B"]
    time_slots = list(range(10))
    durations = {
        ("J1", "Machine A"): 5,
        ("J1", "Machine B"): 3,
        ("J2", "Machine A"): 4,
        ("J2", "Machine B"): 2,
    }

    # ... (运行 solver.solve() 得到 res['x']) ...
    # 这里给一个伪解演示解析流程
    n_vars = len(jobs) * len(machines) * len(time_slots)
    res_x = np.zeros(n_vars, dtype=float)

    def _idx(job_i: int, machine_j: int, t: int) -> int:
        return (job_i * len(machines) + machine_j) * len(time_slots) + t

    res_x[_idx(0, 0, 0)] = 1.0  # J1 on Machine A at t=0
    res_x[_idx(0, 1, 5)] = 1.0  # J1 on Machine B at t=5
    res_x[_idx(1, 0, 6)] = 1.0  # J2 on Machine A at t=6

    tasks_data = parse_binary_schedule(res_x, jobs, machines, time_slots, durations)
    Visualizer.plot_gantt_chart(tasks_data, title="Optimal Production Schedule (MIP Solution)")


if __name__ == "__main__":
    main()
