# -*- coding: utf-8 -*-
"""
optimization_monitor.py
Real-time iteration-level monitor for optimization runs.
"""
from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

try:
    from tqdm import tqdm  # type: ignore
except Exception:  # pragma: no cover
    tqdm = None

class OptimizationMonitor:
    """
    Two modes:
    - CLI: tqdm progress with Best/Avg
    - GUI: matplotlib interactive plot
    """
    def __init__(
        self,
        total: Optional[int] = None,
        mode: str = "cli",
        refresh_every: int = 1,
        position: Optional[int] = None,
        leave: bool = True,
    ) -> None:
        self.total = total
        self.mode = mode
        self.refresh_every = max(1, int(refresh_every))
        self.iterations: List[int] = []
        self.best_history: List[float] = []
        self.avg_history: List[float] = []
        self.div_history: List[float] = []
        self.phase_history: List[str] = []
        self._last_draw = 0
        self._bar = None

        if self.mode == "cli" and tqdm is not None:
            self._bar = tqdm(
                total=total,
                desc="Optimize",
                dynamic_ncols=True,
                mininterval=0.5,
                position=position,
                leave=leave,
            )

        if self.mode == "gui":
            import matplotlib.pyplot as plt
            plt.ion()
            self._plt = plt
            self._fig, (self._ax1, self._ax2) = plt.subplots(2, 1, figsize=(8, 6))
            self._ax1.set_title("Convergence")
            self._ax1.set_xlabel("Iter")
            self._ax1.set_ylabel("Cost")
            self._ax2.set_title("Diversity (Cost Std)")
            self._ax2.set_xlabel("Iter")
            self._ax2.set_ylabel("Std")
            self._fig.tight_layout()

    def update(self, **state: Any) -> None:
        it = int(state.get("current_iter", len(self.iterations)))
        best = float(state.get("best_cost", 0.0))
        avg = float(state.get("avg_cost", 0.0))
        div = float(state.get("diversity", 0.0))
        phase = str(state.get("phase", ""))

        self.iterations.append(it)
        self.best_history.append(best)
        self.avg_history.append(avg)
        self.div_history.append(div)
        self.phase_history.append(phase)

        if self._bar is not None:
            self._bar.update(1)
            self._bar.set_postfix({
                "phase": phase,
                "best": f"{best:.4f}",
                "avg": f"{avg:.4f}",
            })
            return

        if self.mode == "gui":
            if (len(self.iterations) % self.refresh_every) != 0:
                return
            now = time.time()
            if now - self._last_draw < 0.1:
                return
            self._last_draw = now
            self._ax1.cla()
            self._ax1.plot(self.iterations, self.best_history, color="red", label="Best")
            self._ax1.plot(self.iterations, self.avg_history, color="blue", alpha=0.5, label="Avg")
            self._ax1.legend()
            self._ax1.set_title("Convergence")
            self._ax1.set_xlabel("Iter")
            self._ax1.set_ylabel("Cost")

            self._ax2.cla()
            self._ax2.plot(self.iterations, self.div_history, color="purple", alpha=0.7)
            self._ax2.set_title("Diversity (Cost Std)")
            self._ax2.set_xlabel("Iter")
            self._ax2.set_ylabel("Std")

            self._fig.canvas.draw()
            self._plt.pause(0.01)

    def close(self) -> None:
        if self._bar is not None:
            self._bar.close()

    def save_final_plot(self, path: str) -> None:
        if self.mode != "gui":
            return
        self._fig.savefig(path, dpi=200)
