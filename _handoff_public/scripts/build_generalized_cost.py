"""
build_generalized_cost.py
[DEPRECATED] 此脚本已废弃 - data_loader.py 现已直接输出包含 cost 字段的 graph.pkl

原功能: 把 cost 统一构造成"广义代价"，并覆盖所有边；写回图文件 graph.pkl

用法 (仅供参考):
    python scripts/build_generalized_cost.py \
        --graph_in data/processed/graph.pkl \
        --graph_out data/processed/graph.pkl \
        --time_attr weight \
        --dist_attr distance \
        --transfer_penalty_default 5.0
"""

import argparse
import json
import pickle
from pathlib import Path

import numpy as np


def main():
    parser = argparse.ArgumentParser(description="Build generalized cost for all edges")
    parser.add_argument("--graph_in", type=str, default="data/processed/graph.pkl",
                        help="Input graph pickle file")
    parser.add_argument("--graph_out", type=str, default="data/processed/graph.pkl",
                        help="Output graph pickle file with generalized cost")
    parser.add_argument("--time_attr", type=str, default="weight",
                        help="Attribute name for travel time")
    parser.add_argument("--dist_attr", type=str, default="distance",
                        help="Attribute name for distance")
    parser.add_argument("--transfer_penalty_default", type=float, default=5.0,
                        help="Default penalty for transfer/transit edges (in same unit as time)")
    args = parser.parse_args()

    # Load graph
    print(f"Loading graph from {args.graph_in} ...")
    with open(args.graph_in, "rb") as f:
        G = pickle.load(f)

    print(f"Graph type: {type(G).__name__}")
    print(f"Is MultiGraph: {G.is_multigraph()}")
    print(f"nV = {G.number_of_nodes():,}   nE = {G.number_of_edges():,}")
    print("=" * 60)

    # Collect all edges to modify
    time_values = []
    cost_values = []
    dist_values = []
    
    count_transfer_penalty = 0
    count_cost_le_zero = 0
    count_time_le_zero = 0
    count_missing_time = 0
    count_missing_dist = 0

    print(f"\nProcessing edges with time_attr='{args.time_attr}', dist_attr='{args.dist_attr}'...")
    print(f"Transfer penalty: {args.transfer_penalty_default}")

    # Iterate and modify edges in-place
    for u, v, k, data in G.edges(keys=True, data=True):
        # (a) Set time_min from time_attr
        time_val = data.get(args.time_attr, None)
        if time_val is None or not isinstance(time_val, (int, float)):
            time_val = 0.0
            count_missing_time += 1
        data["time_min"] = float(time_val)
        time_values.append(float(time_val))

        # (b) Set dist_km from dist_attr
        dist_val = data.get(args.dist_attr, None)
        if dist_val is None or not isinstance(dist_val, (int, float)):
            dist_val = 0.0
            count_missing_dist += 1
        data["dist_km"] = float(dist_val)
        dist_values.append(float(dist_val))

        # (c) Determine penalty
        mode = data.get("mode", "")
        has_transfer_type = "transfer_type" in data
        is_transfer_mode = mode in ("transfer", "transit")

        if has_transfer_type or is_transfer_mode:
            penalty = args.transfer_penalty_default
            count_transfer_penalty += 1
        else:
            penalty = 0.0

        data["transfer_penalty"] = penalty

        # (d) cost = time_min + penalty
        cost = data["time_min"] + penalty
        data["cost"] = cost
        cost_values.append(cost)

        # (e) Flag anomalies
        flags = []
        if data["cost"] <= 0:
            flags.append("cost_le_zero")
            count_cost_le_zero += 1
        if data["time_min"] <= 0:
            flags.append("time_le_zero")
            count_time_le_zero += 1
        if flags:
            data["cost_flags"] = flags

    # Convert to numpy for quantile computation
    time_arr = np.array(time_values)
    cost_arr = np.array(cost_values)
    dist_arr = np.array(dist_values)

    # Summary statistics
    summary = {
        "total_edges": len(cost_values),
        "time_min": {
            "min": float(np.min(time_arr)),
            "max": float(np.max(time_arr)),
            "mean": float(np.mean(time_arr)),
            "p25": float(np.percentile(time_arr, 25)),
            "p50": float(np.percentile(time_arr, 50)),
            "p75": float(np.percentile(time_arr, 75)),
            "p95": float(np.percentile(time_arr, 95)),
        },
        "cost": {
            "min": float(np.min(cost_arr)),
            "max": float(np.max(cost_arr)),
            "mean": float(np.mean(cost_arr)),
            "p25": float(np.percentile(cost_arr, 25)),
            "p50": float(np.percentile(cost_arr, 50)),
            "p75": float(np.percentile(cost_arr, 75)),
            "p95": float(np.percentile(cost_arr, 95)),
        },
        "dist_km": {
            "min": float(np.min(dist_arr)),
            "max": float(np.max(dist_arr)),
            "mean": float(np.mean(dist_arr)),
        },
        "anomaly_counts": {
            "missing_time": count_missing_time,
            "missing_dist": count_missing_dist,
            "time_le_zero": count_time_le_zero,
            "cost_le_zero": count_cost_le_zero,
            "transfer_penalty_applied": count_transfer_penalty,
        },
    }

    # Print summary
    print("\n[Summary]")
    print(f"  Edges processed: {summary['total_edges']:,}")
    print(f"  Transfer penalty applied: {count_transfer_penalty:,}")
    print(f"  Missing time_attr: {count_missing_time:,}")
    print(f"  Missing dist_attr: {count_missing_dist:,}")
    print(f"  time_min <= 0: {count_time_le_zero:,}")
    print(f"  cost <= 0: {count_cost_le_zero:,}")
    print()
    print(f"  time_min: min={summary['time_min']['min']:.4g}  max={summary['time_min']['max']:.4g}  "
          f"p50={summary['time_min']['p50']:.4g}  p95={summary['time_min']['p95']:.4g}")
    print(f"  cost:     min={summary['cost']['min']:.4g}  max={summary['cost']['max']:.4g}  "
          f"p50={summary['cost']['p50']:.4g}  p95={summary['cost']['p95']:.4g}")

    # (a) Save graph
    print(f"\nSaving graph to {args.graph_out} ...")
    Path(args.graph_out).parent.mkdir(parents=True, exist_ok=True)
    with open(args.graph_out, "wb") as f:
        pickle.dump(G, f)
    print(f"  ✓ Saved: {args.graph_out}")

    # (b) Save summary JSON
    out_dir = Path("outputs/debug")
    out_dir.mkdir(parents=True, exist_ok=True)
    summary_path = out_dir / "cost_summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    print(f"  ✓ Saved: {summary_path}")

    # (c) Assert 100% coverage
    # Check that all edges now have 'cost'
    cost_coverage = sum(1 for u, v, k, data in G.edges(keys=True, data=True) if "cost" in data)
    coverage_pct = 100.0 * cost_coverage / G.number_of_edges() if G.number_of_edges() > 0 else 0.0

    print()
    print("=" * 60)
    print(f"[ASSERTION] cost coverage: {cost_coverage:,} / {G.number_of_edges():,} = {coverage_pct:.2f}%")
    assert coverage_pct == 100.0, f"Cost coverage is {coverage_pct:.2f}%, expected 100%!"
    print("  ✓ PASS: cost 覆盖率为 100%")
    print("\nBuild generalized cost complete.")


if __name__ == "__main__":
    main()
