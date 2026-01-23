# -*- coding: utf-8 -*-
"""
Exporters for solver outputs -> CSV artifacts used by:
- artist (Kepler/Gephi)
- writer (paper tables)
- scripts/make_tables.py (LaTeX tables)

Core solver code MUST NOT be modified.
These exporters only consume results and write standardized CSVs.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

import numpy as np
import pandas as pd
import networkx as nx

from src.utils.csv_log import append_row_csv, write_table_csv


# ----------------------------
# 1) Metrics / Ablation logs
# ----------------------------
METRICS_COLUMNS = [
    "run_id", "method", "objective", "total_cost", "max_congestion",
    "makespan", "resilience_score", "feasible", "runtime_sec", "seed", "note"
]

ABLATION_COLUMNS = [
    "run_id", "variant", "objective", "total_cost", "max_congestion",
    "makespan", "resilience_score", "feasible", "runtime_sec", "seed", "note"
]

PERTURB_COLUMNS = [
    "scenario", "metric_name", "baseline_value", "perturbed_value",
    "delta_pct", "mc_runs", "stderr", "note"
]


def export_metrics_row(row: Dict[str, Any], out_csv: str | Path = "outputs/metrics/metrics.csv") -> Path:
    return append_row_csv(out_csv, row=row, columns=METRICS_COLUMNS)


def export_ablation_row(row: Dict[str, Any], out_csv: str | Path = "outputs/metrics/ablation.csv") -> Path:
    return append_row_csv(out_csv, row=row, columns=ABLATION_COLUMNS)


def export_perturbation_table(rows: List[Dict[str, Any]], out_csv: str | Path = "outputs/robust/perturbation_table.csv") -> Path:
    return write_table_csv(out_csv, rows=rows, columns=PERTURB_COLUMNS)


# ----------------------------
# 2) Robustness curves
# ----------------------------
def export_resilience_curve(
    attack_ratio: Sequence[float],
    performance: Sequence[float],
    stderr: Optional[Sequence[float]] = None,
    out_csv: str | Path = "outputs/exports/resilience_curve.csv",
) -> Path:
    xs = np.asarray(attack_ratio, dtype=float)
    ys = np.asarray(performance, dtype=float)
    if stderr is None:
        df = pd.DataFrame({"attack_ratio": xs, "performance": ys})
    else:
        df = pd.DataFrame({"attack_ratio": xs, "performance": ys, "stderr": np.asarray(stderr, dtype=float)})

    p = Path(out_csv)
    p.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(p, index=False, encoding="utf-8-sig")
    return p


# ----------------------------
# 3) Flow export for artist
# ----------------------------
FLOW_COLUMNS = ["u", "v", "u_lat", "u_lon", "v_lat", "v_lon", "flow", "capacity", "utilization"]


def _get_node_latlon(G: nx.Graph, n: Any) -> Tuple[Optional[float], Optional[float]]:
    d = G.nodes[n]
    for lat_k, lon_k in [("lat", "lon"), ("latitude", "longitude"), ("y", "x"), ("Y", "X")]:
        if lat_k in d and lon_k in d:
            try:
                return float(d[lat_k]), float(d[lon_k])
            except Exception:
                return None, None
    return None, None


def export_solution_flows(
    G: nx.Graph,
    flow: Mapping[Tuple[Any, Any], float],
    capacity: Optional[Mapping[Tuple[Any, Any], float]] = None,
    out_csv: str | Path = "outputs/exports/solution_flows.csv",
    directed: Optional[bool] = None,
) -> Path:
    if directed is None:
        directed = G.is_directed()

    rows: List[Dict[str, Any]] = []
    for (u, v), f in flow.items():
        u_lat, u_lon = _get_node_latlon(G, u)
        v_lat, v_lon = _get_node_latlon(G, v)

        cap = None
        if capacity is not None:
            cap = capacity.get((u, v), None)
            if cap is None and (not directed):
                cap = capacity.get((v, u), None)
        else:
            if G.has_edge(u, v):
                cap = G.edges[u, v].get("capacity", None)
            if cap is None and (not directed) and G.has_edge(v, u):
                cap = G.edges[v, u].get("capacity", None)

        util = None
        try:
            if cap is not None and float(cap) != 0.0:
                util = float(f) / float(cap)
        except Exception:
            util = None

        rows.append({
            "u": u, "v": v,
            "u_lat": u_lat, "u_lon": u_lon,
            "v_lat": v_lat, "v_lon": v_lon,
            "flow": float(f),
            "capacity": (float(cap) if cap is not None else None),
            "utilization": util
        })

    p = Path(out_csv)
    p.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows, columns=FLOW_COLUMNS).to_csv(p, index=False, encoding="utf-8-sig")
    return p
