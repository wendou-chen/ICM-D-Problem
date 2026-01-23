"""\
schedule.py
Contest-grade scheduling utilities for ICM/MCM D.

Core idea: Encode-Decode (Priority List -> Feasible Schedule)
------------------------------------------------------------
Directly optimizing start times typically explodes constraints (machine conflicts,
precedence, time windows). The standard contest/OR trick is:

- Encode: a permutation (priority list) of tasks.
- Decode: Serial Schedule Generation Scheme (SSGS) that deterministically builds
  a *feasible* schedule by inserting each eligible task at the earliest possible
  time respecting precedence + renewable resources.

This module implements an insertion-based SSGS for **unit-capacity machines**
(each task requires exactly one machine; each machine processes at most one task
at a time). This covers many ICM D scheduling/dispatching variants and can be
extended to multi-resource capacities if needed.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np


@dataclass(frozen=True)
class Task:
    """Scheduling task definition."""

    task_id: Any
    duration: float
    machine: Any
    release: float = 0.0  # earliest start (time window)
    due: Optional[float] = None  # optional due date (for penalty)


@dataclass
class ScheduleResult:
    """Decoded schedule."""

    start_times: Dict[Any, float]
    end_times: Dict[Any, float]
    gantt: List[Tuple[str, float, float, str]]  # (task_name, start, duration, resource_id)
    makespan: float


def _find_earliest_gap(intervals: List[Tuple[float, float]], earliest: float, duration: float) -> float:
    """Find earliest start >= earliest s.t. [start, start+duration] doesn't overlap.

    intervals must be sorted by start time.
    """
    if duration <= 0:
        return float(earliest)
    t = float(earliest)
    for s, e in intervals:
        if t + duration <= s:  # fits before this interval
            return t
        if t < e:  # overlaps, jump to end
            t = float(e)
    return t


class SSGSDecoder:
    """Serial Schedule Generation Scheme (SSGS) decoder."""

    def __init__(
        self,
        tasks: Sequence[Task],
        predecessors: Optional[Dict[Any, Sequence[Any]]] = None,
    ):
        self.tasks: Dict[Any, Task] = {t.task_id: t for t in tasks}
        self.preds: Dict[Any, List[Any]] = {k: list(v) for k, v in (predecessors or {}).items()}
        for tid in self.tasks:
            self.preds.setdefault(tid, [])

    def decode(self, priority_list: Sequence[Any]) -> ScheduleResult:
        """Decode a priority list into a feasible schedule.

        Parameters
        ----------
        priority_list:
            permutation of task ids.

        Returns
        -------
        ScheduleResult with gantt tuples compatible with viz.plot_gantt.
        """
        remaining = [tid for tid in priority_list if tid in self.tasks]
        # append any missing tasks (robustness)
        for tid in self.tasks:
            if tid not in remaining:
                remaining.append(tid)

        start: Dict[Any, float] = {}
        end: Dict[Any, float] = {}
        scheduled: set[Any] = set()

        # machine -> sorted intervals
        machine_intervals: Dict[Any, List[Tuple[float, float]]] = {}
        for t in self.tasks.values():
            machine_intervals.setdefault(t.machine, [])

        # iterative insertion respecting precedence
        safety = 0
        while remaining:
            progressed = False
            safety += 1
            if safety > 10 * len(self.tasks) + 100:
                raise ValueError("SSGS decoding failed: possible precedence cycle or invalid predecessors.")

            for idx, tid in enumerate(list(remaining)):
                preds = self.preds.get(tid, [])
                if any(p not in scheduled for p in preds):
                    continue

                task = self.tasks[tid]
                # precedence ready time
                ready = max([end[p] for p in preds], default=0.0)
                ready = max(ready, task.release)

                intervals = machine_intervals[task.machine]
                intervals.sort(key=lambda x: x[0])
                st = _find_earliest_gap(intervals, ready, task.duration)
                et = st + task.duration
                # insert interval and maintain sorted list
                intervals.append((st, et))
                intervals.sort(key=lambda x: x[0])

                start[tid] = float(st)
                end[tid] = float(et)
                scheduled.add(tid)
                remaining.pop(idx)
                progressed = True
                break

            if not progressed:
                # No eligible task found -> cycle
                raise ValueError("No eligible task found. Precedence graph may contain a cycle.")

        makespan = float(max(end.values(), default=0.0))
        gantt = [(str(tid), start[tid], self.tasks[tid].duration, str(self.tasks[tid].machine)) for tid in start]
        gantt.sort(key=lambda x: (x[3], x[1]))

        return ScheduleResult(start_times=start, end_times=end, gantt=gantt, makespan=makespan)


def makespan_objective(decoder: SSGSDecoder) -> Any:
    """Helper: build an objective(priority_list)->makespan for OptimizationProblem."""

    def _obj(priority_list: Sequence[Any]) -> float:
        res = decoder.decode(priority_list)
        return float(res.makespan)

    return _obj
