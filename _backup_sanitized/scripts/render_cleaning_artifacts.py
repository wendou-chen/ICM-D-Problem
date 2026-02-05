#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
render_cleaning_artifacts.py
从 cleaning_log.md 解析 key:value 统计，自动生成：
1) 论文段落（Markdown）
2) 清洗统计表（Markdown）
3) 清洗统计表（LaTeX）

Usage:
  python scripts/render_cleaning_artifacts.py \
      --log data/processed/cleaning_log.md \
      --outdir outputs/paper
"""

import argparse
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, Tuple


# ----------------------------
# Parsing helpers
# ----------------------------
KV_RE = re.compile(r"^\s*(?:-\s+)?([A-Za-z0-9_]+)\s*:\s*([^\n]+?)\s*$", flags=re.M)


def parse_kv(md_text: str) -> Dict[str, str]:
    kv = {}
    for m in KV_RE.finditer(md_text):
        k = m.group(1).strip()
        v = m.group(2).strip()
        kv[k] = v
    return kv


def _strip_commas(s: str) -> str:
    return s.replace(",", "").strip()


def to_int(v: str) -> Optional[int]:
    if v is None:
        return None
    s = _strip_commas(str(v))
    s = s.replace("%", "").strip()
    # allow floats that are effectively ints
    try:
        if re.fullmatch(r"-?\d+(\.\d+)?", s):
            f = float(s)
            return int(round(f))
    except Exception:
        return None
    return None


def to_float(v: str) -> Optional[float]:
    if v is None:
        return None
    s = _strip_commas(str(v))
    s = s.replace("%", "").strip()
    try:
        return float(s)
    except Exception:
        return None


def fmt_int(n: Optional[int]) -> str:
    return "NA" if n is None else f"{n:,}"


def fmt_pct(x: Optional[float], nd: int = 2) -> str:
    return "NA" if x is None else f"{x:.{nd}f}%"


def safe_get(kv: Dict[str, str], key: str) -> str:
    if key not in kv:
        raise ValueError(f"Missing key in cleaning_log.md: {key}")
    return kv[key]


# ----------------------------
# Data model for tables
# ----------------------------
@dataclass
class DatasetRow:
    name: str
    raw: int
    clean: int
    removed: int
    removed_rate: float  # percent


def make_dataset_row(name: str, raw: int, clean: int) -> DatasetRow:
    removed = raw - clean
    removed_rate = (removed / raw * 100.0) if raw > 0 else 0.0
    return DatasetRow(name, raw, clean, removed, removed_rate)


# ----------------------------
# Rendering: paragraph
# ----------------------------
def render_paragraph(kv: Dict[str, str]) -> str:
    # Required keys (fail fast)
    required = [
        "N_raw", "N_clean", "N_drop_duplicate_osmid", "N_drop_bbox_outlier",
        "bbox_quantile_low", "bbox_quantile_high", "bbox_x_lo", "bbox_x_hi", "bbox_y_lo", "bbox_y_hi",
        "E_raw", "E_clean", "E_drop_self_loop",
        "E_lanes_fill_default", "E_maxspeed_fill_default",
        "lanes_default", "maxspeed_default_mph",
        "B_raw", "B_clean", "bbox_margin_deg",
    ]
    for k in required:
        safe_get(kv, k)

    N_raw = to_int(safe_get(kv, "N_raw"))
    N_clean = to_int(safe_get(kv, "N_clean"))
    E_raw = to_int(safe_get(kv, "E_raw"))
    E_clean = to_int(safe_get(kv, "E_clean"))
    B_raw = to_int(safe_get(kv, "B_raw"))
    B_clean = to_int(safe_get(kv, "B_clean"))

    n_row = make_dataset_row("Nodes", N_raw, N_clean)
    e_row = make_dataset_row("Edges", E_raw, E_clean)
    b_row = make_dataset_row("Bus stops", B_raw, B_clean)

    bbox_q_low = to_float(safe_get(kv, "bbox_quantile_low"))
    bbox_q_high = to_float(safe_get(kv, "bbox_quantile_high"))

    bbox_x_lo = safe_get(kv, "bbox_x_lo")
    bbox_x_hi = safe_get(kv, "bbox_x_hi")
    bbox_y_lo = safe_get(kv, "bbox_y_lo")
    bbox_y_hi = safe_get(kv, "bbox_y_hi")

    n_dup = to_int(safe_get(kv, "N_drop_duplicate_osmid"))
    n_bbox = to_int(safe_get(kv, "N_drop_bbox_outlier"))

    e_self = to_int(safe_get(kv, "E_drop_self_loop"))
    e_lanes_fill = to_int(safe_get(kv, "E_lanes_fill_default"))
    e_speed_fill = to_int(safe_get(kv, "E_maxspeed_fill_default"))
    lanes_default = to_int(safe_get(kv, "lanes_default"))
    maxspeed_default = to_int(safe_get(kv, "maxspeed_default_mph"))

    bbox_margin = to_float(safe_get(kv, "bbox_margin_deg"))

    # Optional keys
    N_drop_missing = to_int(kv.get("N_drop_missing_or_non_numeric_xy", "NA"))
    N_drop_range = to_int(kv.get("N_drop_invalid_range_xy", "NA"))
    E_drop_missing = to_int(kv.get("E_drop_missing_uvk", "NA"))

    text = f"""## Data Cleaning and Standardization (Auto-generated)

We treat the provided CSV files as **raw, immutable inputs** and apply a reproducible cleaning pipeline to produce curated files in `data/processed`. The goal is to remove clearly invalid records and standardize key attributes while avoiding over-cleaning that could alter the underlying network structure.

**Road network nodes (`nodes_all.csv`).** We require `osmid`, longitude `x`, and latitude `y`. Rows with missing or non-numeric coordinates are removed ({fmt_int(N_drop_missing)}), and we enforce global coordinate bounds longitude ∈ [−180, 180] and latitude ∈ [−90, 90] (removed {fmt_int(N_drop_range)}). We de-duplicate by `osmid`, removing {fmt_int(n_dup)} rows. To eliminate rare coordinate-drift outliers, we compute a robust bounding box using the quantiles $(q_{{low}}, q_{{high}})=({bbox_q_low}, {bbox_q_high})$, yielding bounds $x\\in[{bbox_x_lo},{bbox_x_hi}]$ and $y\\in[{bbox_y_lo},{bbox_y_hi}]$; this removes {fmt_int(n_bbox)} nodes. Overall, nodes are reduced from {fmt_int(n_row.raw)} to {fmt_int(n_row.clean)} ({fmt_pct(n_row.removed_rate)} removed).

**Road network edges (`edges_all.csv`).** We require valid endpoints (`u`, `v`, `key`). Rows with missing endpoints are removed ({fmt_int(E_drop_missing)}). We remove self-loops ($u=v$), removing {fmt_int(e_self)} edges. We standardize `lanes` and `maxspeed` to numeric fields; unparseable/missing lane counts are imputed with a conservative default of {fmt_int(lanes_default)} lane(s), affecting {fmt_int(e_lanes_fill)} edges, and unparseable/missing speed limits are imputed with a default of {fmt_int(maxspeed_default)} mph, affecting {fmt_int(e_speed_fill)} edges. Overall, edges are reduced from {fmt_int(e_row.raw)} to {fmt_int(e_row.clean)} ({fmt_pct(e_row.removed_rate)} removed).

**Bus stops (`Bus_Stops.csv`).** We standardize coordinates by renaming `X,Y` to `stop_lon, stop_lat` and enforce the same coordinate validity checks. Optionally, we filter stops to the node-derived study-area bounding box expanded by a small margin of {bbox_margin} degrees to prevent disconnected artifacts. Bus stops are reduced from {fmt_int(b_row.raw)} to {fmt_int(b_row.clean)} ({fmt_pct(b_row.removed_rate)} removed).

All thresholds, defaults, and record counts are logged in `cleaning_log.md` to ensure full reproducibility and auditability.
"""
    return text


# ----------------------------
# Rendering: Markdown table(s)
# ----------------------------
def render_markdown_tables(kv: Dict[str, str]) -> str:
    # Required for summary
    N_raw = to_int(safe_get(kv, "N_raw"))
    N_clean = to_int(safe_get(kv, "N_clean"))
    E_raw = to_int(safe_get(kv, "E_raw"))
    E_clean = to_int(safe_get(kv, "E_clean"))
    B_raw = to_int(safe_get(kv, "B_raw"))
    B_clean = to_int(safe_get(kv, "B_clean"))

    rows = [
        make_dataset_row("Nodes", N_raw, N_clean),
        make_dataset_row("Edges", E_raw, E_clean),
        make_dataset_row("Bus stops", B_raw, B_clean),
    ]

    summary = [
        "| Dataset | Raw rows | Clean rows | Removed | Removed rate |",
        "|---|---:|---:|---:|---:|",
    ]
    for r in rows:
        summary.append(
            f"| {r.name} | {fmt_int(r.raw)} | {fmt_int(r.clean)} | {fmt_int(r.removed)} | {fmt_pct(r.removed_rate)} |"
        )

    # Key-operations table (narrow but informative)
    # Use NA if missing
    key_ops = [
        "| Component | Key operation | Count / Value |",
        "|---|---|---:|",
        f"| Nodes | Duplicate `osmid` removed | {fmt_int(to_int(kv.get('N_drop_duplicate_osmid','NA')))} |",
        f"| Nodes | BBox (quantile) outliers removed | {fmt_int(to_int(kv.get('N_drop_bbox_outlier','NA')))} |",
        f"| Nodes | BBox quantiles (low, high) | {kv.get('bbox_quantile_low','NA')}, {kv.get('bbox_quantile_high','NA')} |",
        f"| Nodes | BBox bounds (x_lo, x_hi) | {kv.get('bbox_x_lo','NA')}, {kv.get('bbox_x_hi','NA')} |",
        f"| Nodes | BBox bounds (y_lo, y_hi) | {kv.get('bbox_y_lo','NA')}, {kv.get('bbox_y_hi','NA')} |",
        f"| Edges | Self-loops removed | {fmt_int(to_int(kv.get('E_drop_self_loop','NA')))} |",
        f"| Edges | Lanes imputed with default | {fmt_int(to_int(kv.get('E_lanes_fill_default','NA')))} |",
        f"| Edges | Maxspeed imputed with default | {fmt_int(to_int(kv.get('E_maxspeed_fill_default','NA')))} |",
        f"| Edges | Defaults (lanes, maxspeed mph) | {kv.get('lanes_default','NA')}, {kv.get('maxspeed_default_mph','NA')} |",
        f"| Bus stops | BBox margin (deg) | {kv.get('bbox_margin_deg','NA')} |",
        f"| Bus stops | XY renamed to lon/lat | {kv.get('B_renamed_XY_to_stop_lonlat','NA')} |",
    ]

    return "\n".join([
        "# Cleaning Statistics (Auto-generated)",
        "",
        "## Summary",
        *summary,
        "",
        "## Key Operations and Parameters",
        *key_ops,
        ""
    ])


# ----------------------------
# Rendering: LaTeX table(s)
# ----------------------------
def latex_escape(s: str) -> str:
    # minimal escaping for underscores etc.
    return (s.replace("\\", "\\textbackslash{}")
             .replace("_", "\\_")
             .replace("%", "\\%"))


def render_latex_tables(kv: Dict[str, str]) -> str:
    N_raw = to_int(safe_get(kv, "N_raw"))
    N_clean = to_int(safe_get(kv, "N_clean"))
    E_raw = to_int(safe_get(kv, "E_raw"))
    E_clean = to_int(safe_get(kv, "E_clean"))
    B_raw = to_int(safe_get(kv, "B_raw"))
    B_clean = to_int(safe_get(kv, "B_clean"))

    rows = [
        make_dataset_row("Nodes", N_raw, N_clean),
        make_dataset_row("Edges", E_raw, E_clean),
        make_dataset_row("Bus stops", B_raw, B_clean),
    ]

    def row_line(r: DatasetRow) -> str:
        return f"{latex_escape(r.name)} & {fmt_int(r.raw)} & {fmt_int(r.clean)} & {fmt_int(r.removed)} & {r.removed_rate:.2f}\\% \\\\"

    summary_tab = "\n".join([
        "% Auto-generated cleaning summary table",
        "\\begin{table}[ht]",
        "\\centering",
        "\\caption{Data cleaning summary.}",
        "\\label{tab:cleaning_summary}",
        "\\begin{tabular}{lrrrr}",
        "\\hline",
        "Dataset & Raw & Clean & Removed & Removed rate \\\\",
        "\\hline",
        *[row_line(r) for r in rows],
        "\\hline",
        "\\end{tabular}",
        "\\end{table}",
        ""
    ])

    # Key parameters tab (compact)
    param_pairs = [
        ("bbox\\_quantile\\_low", kv.get("bbox_quantile_low", "NA")),
        ("bbox\\_quantile\\_high", kv.get("bbox_quantile_high", "NA")),
        ("bbox\\_margin\\_deg", kv.get("bbox_margin_deg", "NA")),
        ("lanes\\_default", kv.get("lanes_default", "NA")),
        ("maxspeed\\_default\\_mph", kv.get("maxspeed_default_mph", "NA")),
        ("length\\_upper\\_m", kv.get("length_upper_m", "NA")),
    ]
    params_tab = "\n".join([
        "% Auto-generated cleaning parameters table",
        "\\begin{table}[ht]",
        "\\centering",
        "\\caption{Key cleaning parameters and defaults.}",
        "\\label{tab:cleaning_params}",
        "\\begin{tabular}{lr}",
        "\\hline",
        "Parameter & Value \\\\",
        "\\hline",
        *[f"{k} & {latex_escape(str(v))} \\\\" for k, v in param_pairs],
        "\\hline",
        "\\end{tabular}",
        "\\end{table}",
        ""
    ])

    return summary_tab + "\n" + params_tab


# ----------------------------
# Main
# ----------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--log", default="data/processed/cleaning_log.md", help="Path to cleaning_log.md")
    ap.add_argument("--outdir", default="outputs/paper", help="Output directory")
    args = ap.parse_args()

    log_path = Path(args.log)
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    md_text = log_path.read_text(encoding="utf-8")
    kv = parse_kv(md_text)

    # Generate artifacts
    paragraph = render_paragraph(kv)
    md_tables = render_markdown_tables(kv)
    tex_tables = render_latex_tables(kv)

    para_path = outdir / "data_cleaning_paragraph.md"
    md_table_path = outdir / "data_cleaning_table.md"
    tex_table_path = outdir / "data_cleaning_table.tex"

    para_path.write_text(paragraph, encoding="utf-8")
    md_table_path.write_text(md_tables, encoding="utf-8")
    tex_table_path.write_text(tex_tables, encoding="utf-8")

    print("Generated:")
    print(f"- {para_path}")
    print(f"- {md_table_path}")
    print(f"- {tex_table_path}")


if __name__ == "__main__":
    main()
