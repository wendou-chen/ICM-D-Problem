#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generate LaTeX tables from CSV outputs.

Default inputs (relative to repo root):
- outputs/metrics/metrics.csv           -> paper/tables/table_metrics.tex
- outputs/metrics/ablation.csv          -> paper/tables/table_ablation.tex
- outputs/robust/perturbation_table.csv -> paper/tables/table_robust.tex

Usage (from repo root):
  python scripts/make_tables.py --wrap
"""
from __future__ import annotations

import argparse
import inspect
from pathlib import Path
from typing import Optional

import pandas as pd


def _read_csv(path: Path) -> Optional[pd.DataFrame]:
    if not path.exists():
        print(f"[WARN] Missing: {path}")
        return None
    try:
        return pd.read_csv(path)
    except Exception as e:
        print(f"[ERROR] Failed reading {path}: {e}")
        return None


def _round_numeric(df: pd.DataFrame, ndigits: int = 4) -> pd.DataFrame:
    df = df.copy()
    for c in df.columns:
        if pd.api.types.is_numeric_dtype(df[c]):
            df[c] = df[c].round(ndigits)
    return df


def _bold_best(df: pd.DataFrame, metric: str, mode: str = "min", ndigits: int = 4) -> pd.DataFrame:
    if metric not in df.columns:
        return df

    df = df.copy()
    s = df[metric]

    # Convert to numeric for comparison; non-numeric become NaN
    num = pd.to_numeric(s, errors="coerce")
    if num.notna().sum() == 0:
        return df

    best = num.max() if mode == "max" else num.min()
    if pd.isna(best):
        return df

    mask = num == best
    df[metric] = df[metric].astype("object")
    for idx in df.index[mask]:
        raw = df.at[idx, metric]
        if raw is None or (isinstance(raw, float) and pd.isna(raw)) or raw == "--":
            continue

        v = pd.to_numeric(pd.Series([raw]), errors="coerce").iloc[0]
        if pd.notna(v):
            text = f"{float(v):.{ndigits}f}"
        else:
            text = str(raw)

        df.at[idx, metric] = rf"\textbf{{{text}}}"

    return df


def _to_latex_table(df: pd.DataFrame, out_path: Path, caption: str, label: str, wrap: bool, ndigits: int) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df2 = _round_numeric(df, ndigits=ndigits)

    ncol = len(df2.columns)
    col_format = "l" + ("c" * (ncol - 1)) if ncol >= 1 else "l"

    supported = set(inspect.signature(pd.DataFrame.to_latex).parameters)
    kwargs = {
        "index": False,
        "escape": False,
        "na_rep": "--",
        "column_format": col_format,
        "float_format": lambda x: f"{x:.{ndigits}f}",
    }
    if "booktabs" in supported:
        kwargs["booktabs"] = True
    latex_tabular = df2.to_latex(**kwargs).rstrip()

    if wrap:
        latex = "\n".join([
            r"\begin{table}[htbp]",
            r"\centering",
            latex_tabular,
            rf"\caption{{{caption}}}",
            rf"\label{{{label}}}",
            r"\end{table}",
            ""
        ])
    else:
        latex = latex_tabular + "\n"

    out_path.write_text(latex, encoding="utf-8")
    print(f"[OK] Wrote {out_path}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", type=str, default=".", help="Repo root (where outputs/ and paper/ exist)")
    ap.add_argument("--wrap", action="store_true", help="Wrap into table environment with caption/label")
    ap.add_argument("--ndigits", type=int, default=4)
    args = ap.parse_args()

    repo = Path(args.repo).resolve()
    outdir = repo / "paper" / "tables"
    outdir.mkdir(parents=True, exist_ok=True)

    metrics = _read_csv(repo / "outputs/metrics/metrics.csv")
    if metrics is not None and len(metrics) > 0:
        sort_cols = [c for c in ["method", "objective", "max_congestion", "run_id"] if c in metrics.columns]
        if sort_cols:
            metrics = metrics.sort_values(by=sort_cols, ascending=True, kind="mergesort")

        metrics = _bold_best(metrics, "objective", mode="min", ndigits=args.ndigits)
        metrics = _bold_best(metrics, "total_cost", mode="min", ndigits=args.ndigits)
        metrics = _bold_best(metrics, "max_congestion", mode="min", ndigits=args.ndigits)
        metrics = _bold_best(metrics, "makespan", mode="min", ndigits=args.ndigits)
        metrics = _bold_best(metrics, "resilience_score", mode="max", ndigits=args.ndigits)

        _to_latex_table(metrics, outdir / "table_metrics.tex",
                        "Performance metrics comparison between baseline methods and the proposed approach.",
                        "tab:metrics", args.wrap, args.ndigits)

    ablation = _read_csv(repo / "outputs/metrics/ablation.csv")
    if ablation is not None and len(ablation) > 0:
        _to_latex_table(ablation, outdir / "table_ablation.tex",
                        "Ablation study: impact of key operators and hyperparameters on solution quality.",
                        "tab:ablation", args.wrap, args.ndigits)

    robust = _read_csv(repo / "outputs/robust/perturbation_table.csv")
    if robust is not None and len(robust) > 0:
        _to_latex_table(robust, outdir / "table_robust.tex",
                        "Sensitivity/robustness results under parameter perturbations (e.g., $\\pm 10\\%$) or attack scenarios.",
                        "tab:robust", args.wrap, args.ndigits)

    print("[DONE] make_tables complete.")


if __name__ == "__main__":
    main()
