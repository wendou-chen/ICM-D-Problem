"""
data_validate.py
数据审计脚本 - 只读检查 raw 数据质量，不修改任何文件

输入:
    - data/raw/nodes.csv
    - data/raw/edges.csv
    - data/raw/Bus_Stops.csv
    - data/processed/graph.pkl (可选)

输出:
    - outputs/audit/audit_report.md
    - outputs/audit/audit_summary.json

用法:
    python scripts/data_validate.py
    python scripts/data_validate.py --raw_dir data/raw --graph data/processed/graph.pkl
"""

import argparse
import json
import os
import pickle
from collections import Counter
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd


def check_csv_file(filepath: str) -> dict:
    """检查单个 CSV 文件的基本信息与质量问题"""
    result = {
        "exists": False,
        "rows": 0,
        "columns": 0,
        "column_names": [],
        "missing_counts": {},
        "duplicate_rows": 0,
        "sample_issues": [],
        "numeric_stats": {},
    }
    
    if not os.path.exists(filepath):
        return result
    
    result["exists"] = True
    
    try:
        df = pd.read_csv(filepath, low_memory=False)
    except Exception as e:
        result["error"] = str(e)
        return result
    
    result["rows"] = len(df)
    result["columns"] = len(df.columns)
    result["column_names"] = list(df.columns)
    
    # Missing values
    for col in df.columns:
        missing = df[col].isna().sum()
        if missing > 0:
            result["missing_counts"][col] = int(missing)
    
    # Duplicate rows
    result["duplicate_rows"] = int(df.duplicated().sum())
    
    # Numeric column stats
    for col in df.select_dtypes(include=[np.number]).columns:
        vals = df[col].dropna()
        if len(vals) > 0:
            result["numeric_stats"][col] = {
                "min": float(vals.min()),
                "max": float(vals.max()),
                "mean": float(vals.mean()),
                "zeros": int((vals == 0).sum()),
                "negatives": int((vals < 0).sum()),
            }
    
    return result


def check_graph_file(filepath: str) -> dict:
    """检查 graph.pkl 的基本属性"""
    result = {
        "exists": False,
        "nodes": 0,
        "edges": 0,
        "is_multigraph": False,
        "is_directed": False,
        "edge_attr_counts": {},
        "cost_coverage": 0.0,
        "mode_distribution": {},
    }
    
    if not os.path.exists(filepath):
        return result
    
    result["exists"] = True
    
    try:
        with open(filepath, "rb") as f:
            G = pickle.load(f)
    except Exception as e:
        result["error"] = str(e)
        return result
    
    result["nodes"] = G.number_of_nodes()
    result["edges"] = G.number_of_edges()
    result["is_multigraph"] = G.is_multigraph()
    result["is_directed"] = G.is_directed()
    
    # Edge attribute analysis
    attr_counter = Counter()
    mode_counter = Counter()
    cost_count = 0
    
    if G.is_multigraph():
        edges_iter = G.edges(keys=True, data=True)
    else:
        edges_iter = ((u, v, None, d) for u, v, d in G.edges(data=True))
    
    for u, v, k, data in edges_iter:
        attr_counter.update(data.keys())
        mode_counter[data.get("mode", "<none>")] += 1
        if "cost" in data and data["cost"] is not None:
            cost_count += 1
    
    result["edge_attr_counts"] = dict(attr_counter.most_common(20))
    result["mode_distribution"] = dict(mode_counter)
    result["cost_coverage"] = 100.0 * cost_count / result["edges"] if result["edges"] > 0 else 0.0
    
    return result


def generate_report(nodes_audit: dict, edges_audit: dict, bus_audit: dict, graph_audit: dict) -> str:
    """生成 Markdown 格式的审计报告"""
    lines = []
    lines.append("# 数据审计报告")
    lines.append(f"\n**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("\n---\n")
    
    # Nodes
    lines.append("## 1. nodes_all.csv")
    if nodes_audit["exists"]:
        lines.append(f"- **行数**: {nodes_audit['rows']:,}")
        lines.append(f"- **列数**: {nodes_audit['columns']}")
        lines.append(f"- **列名**: `{', '.join(nodes_audit['column_names'])}`")
        lines.append(f"- **重复行**: {nodes_audit['duplicate_rows']}")
        if nodes_audit["missing_counts"]:
            lines.append("- **缺失值**:")
            for col, cnt in nodes_audit["missing_counts"].items():
                lines.append(f"  - `{col}`: {cnt:,}")
        else:
            lines.append("- **缺失值**: 无")
    else:
        lines.append("- ❌ 文件不存在")
    
    lines.append("\n---\n")
    
    # Edges
    lines.append("## 2. edges_all.csv")
    if edges_audit["exists"]:
        lines.append(f"- **行数**: {edges_audit['rows']:,}")
        lines.append(f"- **列数**: {edges_audit['columns']}")
        lines.append(f"- **列名**: `{', '.join(edges_audit['column_names'])}`")
        lines.append(f"- **重复行**: {edges_audit['duplicate_rows']}")
        if edges_audit["missing_counts"]:
            lines.append("- **缺失值**:")
            for col, cnt in edges_audit["missing_counts"].items():
                lines.append(f"  - `{col}`: {cnt:,}")
        else:
            lines.append("- **缺失值**: 无")
        if edges_audit["numeric_stats"]:
            lines.append("- **数值列统计**:")
            for col, stats in edges_audit["numeric_stats"].items():
                lines.append(f"  - `{col}`: min={stats['min']:.4g}, max={stats['max']:.4g}, mean={stats['mean']:.4g}, zeros={stats['zeros']}, negatives={stats['negatives']}")
    else:
        lines.append("- ❌ 文件不存在")
    
    lines.append("\n---\n")
    
    # Bus Stops
    lines.append("## 3. Bus_Stops.csv")
    if bus_audit["exists"]:
        lines.append(f"- **行数**: {bus_audit['rows']:,}")
        lines.append(f"- **列数**: {bus_audit['columns']}")
        lines.append(f"- **列名**: `{', '.join(bus_audit['column_names'])}`")
        lines.append(f"- **重复行**: {bus_audit['duplicate_rows']}")
        if bus_audit["missing_counts"]:
            lines.append("- **缺失值**:")
            for col, cnt in bus_audit["missing_counts"].items():
                lines.append(f"  - `{col}`: {cnt:,}")
        else:
            lines.append("- **缺失值**: 无")
    else:
        lines.append("- ❌ 文件不存在")
    
    lines.append("\n---\n")
    
    # Graph
    lines.append("## 4. graph.pkl (可选)")
    if graph_audit["exists"]:
        lines.append(f"- **节点数**: {graph_audit['nodes']:,}")
        lines.append(f"- **边数**: {graph_audit['edges']:,}")
        lines.append(f"- **类型**: {'MultiDiGraph' if graph_audit['is_multigraph'] and graph_audit['is_directed'] else 'DiGraph' if graph_audit['is_directed'] else 'Graph'}")
        lines.append(f"- **Cost 覆盖率**: {graph_audit['cost_coverage']:.2f}%")
        lines.append("- **边 mode 分布**:")
        for mode, cnt in graph_audit["mode_distribution"].items():
            lines.append(f"  - `{mode}`: {cnt:,}")
        lines.append("- **边属性 Top 10**:")
        for attr, cnt in list(graph_audit["edge_attr_counts"].items())[:10]:
            lines.append(f"  - `{attr}`: {cnt:,}")
    else:
        lines.append("- ⚠️ 文件不存在或未指定")
    
    lines.append("\n---\n")
    lines.append("## 5. 总结")
    
    issues = []
    if not nodes_audit["exists"]:
        issues.append("nodes_all.csv 缺失")
    if not edges_audit["exists"]:
        issues.append("edges_all.csv 缺失")
    if not bus_audit["exists"]:
        issues.append("Bus_Stops.csv 缺失")
    if nodes_audit.get("duplicate_rows", 0) > 0:
        issues.append(f"nodes_all.csv 有 {nodes_audit['duplicate_rows']} 行重复")
    if edges_audit.get("duplicate_rows", 0) > 0:
        issues.append(f"edges_all.csv 有 {edges_audit['duplicate_rows']} 行重复")
    if graph_audit["exists"] and graph_audit["cost_coverage"] < 100.0:
        issues.append(f"graph.pkl cost 覆盖率仅 {graph_audit['cost_coverage']:.2f}%")
    
    if issues:
        lines.append("**发现问题**:")
        for issue in issues:
            lines.append(f"- ⚠️ {issue}")
    else:
        lines.append("✅ **所有检查通过，无明显数据质量问题。**")
    
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="数据审计脚本 (只读)")
    parser.add_argument("--raw_dir", type=str, default="data/raw",
                        help="原始数据目录")
    parser.add_argument("--graph", type=str, default="data/processed/graph.pkl",
                        help="图文件路径 (可选)")
    parser.add_argument("--output_dir", type=str, default="outputs/audit",
                        help="审计报告输出目录")
    args = parser.parse_args()
    
    print("=" * 60)
    print("数据审计脚本 (只读)")
    print("=" * 60)
    print(f"原始数据目录: {args.raw_dir}")
    print(f"图文件: {args.graph}")
    print(f"输出目录: {args.output_dir}")
    print()
    
    # Check files
    nodes_path = os.path.join(args.raw_dir, "nodes_all.csv")
    edges_path = os.path.join(args.raw_dir, "edges_all.csv")
    bus_path = os.path.join(args.raw_dir, "Bus_Stops.csv")
    
    print("检查 nodes_all.csv ...")
    nodes_audit = check_csv_file(nodes_path)
    print(f"  存在: {nodes_audit['exists']}, 行数: {nodes_audit.get('rows', 0):,}")
    
    print("检查 edges_all.csv ...")
    edges_audit = check_csv_file(edges_path)
    print(f"  存在: {edges_audit['exists']}, 行数: {edges_audit.get('rows', 0):,}")
    
    print("检查 Bus_Stops.csv ...")
    bus_audit = check_csv_file(bus_path)
    print(f"  存在: {bus_audit['exists']}, 行数: {bus_audit.get('rows', 0):,}")
    
    print("检查 graph.pkl ...")
    graph_audit = check_graph_file(args.graph)
    print(f"  存在: {graph_audit['exists']}, 节点: {graph_audit.get('nodes', 0):,}, 边: {graph_audit.get('edges', 0):,}")
    
    # Generate report
    print("\n生成审计报告 ...")
    report_md = generate_report(nodes_audit, edges_audit, bus_audit, graph_audit)
    
    # Save outputs
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    
    report_path = out_dir / "audit_report.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_md)
    print(f"  ✓ 保存: {report_path}")
    
    summary = {
        "timestamp": datetime.now().isoformat(),
        "nodes": nodes_audit,
        "edges": edges_audit,
        "bus_stops": bus_audit,
        "graph": graph_audit,
    }
    
    summary_path = out_dir / "audit_summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    print(f"  ✓ 保存: {summary_path}")
    
    print("\n" + "=" * 60)
    print("审计完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
