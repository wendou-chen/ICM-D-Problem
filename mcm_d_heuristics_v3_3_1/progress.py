# -*- coding: utf-8 -*-
"""
progress.py
Lightweight progress utilities with tqdm fallback.
"""
from __future__ import annotations

import json
import time
from collections import deque
from dataclasses import dataclass
from typing import Any, Deque, Optional

try:
    from tqdm import tqdm  # type: ignore
except Exception:  # pragma: no cover
    tqdm = None


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime())


class Progress:
    """
    Progress bar with tqdm if available, otherwise fallback printer.
    """
    def __init__(
        self,
        total: Optional[int],
        desc: str,
        enabled: bool = True,
        log_path: Optional[str] = None,
        refresh_sec: float = 2.0,
        position: Optional[int] = None,
    ) -> None:
        self.total = total
        self.desc = desc
        self.enabled = enabled
        self.log_path = log_path
        self.refresh_sec = refresh_sec
        self.start_ts = time.time()
        self.last_print = 0.0
        self.completed = 0
        self._durations: Deque[float] = deque(maxlen=10)
        self._bar = None

        if self.enabled and tqdm is not None:
            self._bar = tqdm(
                total=total,
                desc=desc,
                dynamic_ncols=True,
                mininterval=0.5,
                miniters=1,
                leave=True,
                position=position,
            )

    def set_desc(self, desc: str) -> None:
        self.desc = desc
        if self._bar is not None:
            self._bar.set_description(desc)

    def update(self, n: int = 1, **metrics: Any) -> None:
        if not self.enabled:
            return
        self.completed += n

        if self._bar is not None:
            if metrics:
                self._bar.set_postfix({k: v for k, v in metrics.items()})
            self._bar.update(n)
        else:
            now = time.time()
            if (now - self.last_print) >= self.refresh_sec:
                self.last_print = now
                elapsed = now - self.start_ts
                if self.total:
                    pct = 100.0 * self.completed / max(1, self.total)
                    eta = None
                    if "eta_sec" in metrics and metrics["eta_sec"] is not None:
                        eta = metrics["eta_sec"]
                    msg = f"[{self.desc}] {self.completed}/{self.total} ({pct:.1f}%) elapsed={elapsed:.1f}s"
                    if eta is not None:
                        msg += f" eta={float(eta):.1f}s"
                else:
                    msg = f"[{self.desc}] completed={self.completed} elapsed={elapsed:.1f}s"
                if metrics:
                    msg += " " + " ".join([f"{k}={v}" for k, v in metrics.items()])
                print(msg)

        if self.log_path:
            rec = {
                "ts": _now_iso(),
                "desc": self.desc,
                "completed": self.completed,
                "total": self.total,
                "metrics": metrics,
            }
            try:
                with open(self.log_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            except Exception:
                pass

    def close(self) -> None:
        if self._bar is not None:
            self._bar.close()


@dataclass
class StageTimer:
    name: str
    log_path: Optional[str] = None

    def __enter__(self):
        self.t0 = time.time()
        msg = f"[Stage START] {self.name} { _now_iso() }"
        print(msg)
        if self.log_path:
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(msg + "\n")
        return self

    def __exit__(self, exc_type, exc, tb):
        dt = time.time() - self.t0
        msg = f"[Stage END] {self.name} duration={dt:.1f}s"
        print(msg)
        if self.log_path:
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(msg + "\n")
        return False
