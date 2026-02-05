"""
baseline_analysis.py
Baseline Analysis Script - 连通性抽样 + 中心性 top-10 输出

CLI (快速模式):
    python scripts/baseline_analysis.py --graph data/processed/graph.pkl --outdir outputs/baseline --K 100 --seed 42 --od_policy drive_lcc

CLI (betweenness 模式):
    python scripts/baseline_analysis.py --graph data/processed/graph.pkl --outdir outputs/baseline --K 100 --seed 42 --od_policy drive_lcc --centrality_method approx_betweenness --centrality_k 2000 --max_betweenness_k 200
"""

import argparse
import json
import pickle
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import networkx as nx
import numpy as np
import pandas as pd

# Add project root to path
ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))


def load_graph(graph_path: Path) -> Tuple[nx.MultiDiGraph, int, int]:
    """加载图并统计节点数和边数"""
    with open(graph_path, 'rb') as f:
        G = pickle.load(f)
    n_nodes = G.number_of_nodes()
    n_edges = G.number_of_edges()
    return G, n_nodes, n_edges


def get_od_pairs(G: nx.MultiDiGraph, K: int, seed: int, od_policy: str, graph_path: str) -> Tuple[List[Tuple[Any, Any]], str]:
    """选取 OD pairs（可复现）"""
    # 尝试使用 od_sampling.py
    try:
        from scripts.od_sampling import get_or_create_od_pairs
        
        # 使用 outputs/task2 作为缓存目录
        outdir = ROOT_DIR / "outputs" / "task2"
        od_pairs, od_pairs_path = get_or_create_od_pairs(
            G, K, seed, od_policy, outdir, graph_path
        )
        # od_pairs_path 可能是 Path 对象或字符串
        if isinstance(od_pairs_path, Path):
            return od_pairs, str(od_pairs_path.relative_to(ROOT_DIR))
        else:
            return od_pairs, str(od_pairs_path)
    except (ImportError, AttributeError):
        # Fallback: 从图中筛 drive 节点，随机抽样
        np.random.seed(seed)
        
        drive_nodes = []
        for n, d in G.nodes(data=True):
            if d.get("layer") == "drive":
                drive_nodes.append(n)
        
        if len(drive_nodes) < 2:
            raise ValueError(f"Not enough drive nodes: {len(drive_nodes)}")
        
        od_pairs = []
        max_attempts = K * 100
        attempts = 0
        while len(od_pairs) < K and attempts < max_attempts:
            o = np.random.choice(drive_nodes)
            d = np.random.choice(drive_nodes)
            if o != d:
                od_pairs.append((o, d))
            attempts += 1
        
        if len(od_pairs) < K:
            raise ValueError(f"Could not sample {K} OD pairs after {max_attempts} attempts")
        
        return od_pairs, "fallback_random"


def multigraph_to_digraph(G: nx.MultiDiGraph) -> Tuple[nx.DiGraph, int]:
    """MultiDiGraph 合并成 DiGraph（用于最短路与 centrality）"""
    D = nx.DiGraph()
    missing_cost_edges = 0
    
    # 添加所有节点（保留属性）
    for n, d in G.nodes(data=True):
        D.add_node(n, **d)
    
    # 遍历每条边，保留 cost 最小的一条
    edge_costs = {}  # (u, v) -> min_cost
    
    for u, v, k, data in G.edges(keys=True, data=True):
        w = data.get("cost")
        if w is None:
            missing_cost_edges += 1
            continue
        
        try:
            w_float = float(w)
            if not np.isfinite(w_float):
                missing_cost_edges += 1
                continue
        except (ValueError, TypeError):
            missing_cost_edges += 1
            continue
        
        if (u, v) not in edge_costs:
            edge_costs[(u, v)] = w_float
            data2 = dict(data)
            data2["cost"] = w_float
            D.add_edge(u, v, **data2)
        else:
            if w_float < edge_costs[(u, v)]:
                edge_costs[(u, v)] = w_float
                data2 = dict(data)
                data2["cost"] = w_float
                D[u][v].update(data2)
    
    return D, missing_cost_edges


def connectivity_sanity(D: nx.DiGraph, od_pairs: List[Tuple[Any, Any]]) -> Dict:
    """连通性 + cost sanity 检查"""
    # 将 OD pairs 按 origin 分组
    od_by_origin = {}
    for o, d in od_pairs:
        if o not in od_by_origin:
            od_by_origin[o] = []
        od_by_origin[o].append(d)
    
    reachable_count = 0
    unreachable_count = 0
    reachable_costs = []
    
    # 对每个 origin 跑一次 single_source_dijkstra_path_length
    for origin, targets in od_by_origin.items():
        if origin not in D:
            unreachable_count += len(targets)
            continue
        
        try:
            dists = nx.single_source_dijkstra_path_length(D, origin, weight='cost')
            for target in targets:
                if target in dists:
                    cost = dists[target]
                    reachable_costs.append(cost)
                    reachable_count += 1
                else:
                    unreachable_count += 1
        except Exception:
            unreachable_count += len(targets)
    
    reachable_ratio = reachable_count / len(od_pairs) if od_pairs else 0.0
    
    # 统计 cost 分布
    if reachable_costs:
        costs_arr = np.array(reachable_costs)
        cost_min = float(np.min(costs_arr))
        cost_median = float(np.median(costs_arr))
        cost_p95 = float(np.percentile(costs_arr, 95))
        cost_max = float(np.max(costs_arr))
    else:
        cost_min = "NA"
        cost_median = "NA"
        cost_p95 = "NA"
        cost_max = "NA"
    
    return {
        "reachable_count": reachable_count,
        "unreachable_count": unreachable_count,
        "reachable_ratio": reachable_ratio,
        "cost_min": cost_min,
        "cost_median": cost_median,
        "cost_p95": cost_p95,
        "cost_max": cost_max
    }


def compute_od_sample_bottlenecks_top10(G_original: nx.MultiDiGraph, D: nx.DiGraph, od_pairs: List[Tuple[Any, Any]], seed: int) -> Tuple[List[Dict], int, int]:
    """
    OD-sampled bottleneck 快速代理指标
    对每对 OD 计算最短路径，统计中间节点出现次数，取 top-10
    """
    node_load = {}  # node -> count
    reachable_paths_count = 0
    
    # 对每对 (o, d) 计算最短路径
    for o, d in od_pairs:
        try:
            path = nx.dijkstra_path(D, o, d, weight='cost')
            if path and len(path) > 2:  # 至少3个节点才有中间节点
                # 统计中间节点（不包含端点）
                for node in path[1:-1]:
                    node_load[node] = node_load.get(node, 0) + 1
                reachable_paths_count += 1
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            # 不可达，跳过
            pass
    
    # 取 top-10
    sorted_nodes = sorted(node_load.items(), key=lambda x: x[1], reverse=True)
    top10 = sorted_nodes[:10]
    
    # 构造 bottlenecks 列表
    bottlenecks = []
    missing_geo_count = 0
    
    for rank, (node_id, count) in enumerate(top10, 1):
        # proxy 值：count / reachable_paths_count（归一化，范围[0,1]）
        proxy_value = count / reachable_paths_count if reachable_paths_count > 0 else 0.0
        
        # 优先从原图节点属性 pos=(lon,lat) 读取
        node_data = G_original.nodes.get(node_id, {})
        pos = node_data.get("pos")
        
        if pos is not None and isinstance(pos, (list, tuple)) and len(pos) == 2:
            lon, lat = pos[0], pos[1]
        else:
            lon, lat = None, None
            missing_geo_count += 1
        
        bottlenecks.append({
            "rank": rank,
            "node_id": node_id,
            "betweenness": proxy_value,
            "lon": lon,
            "lat": lat
        })
    
    return bottlenecks, missing_geo_count, reachable_paths_count


def compute_betweenness_top10(G_original: nx.MultiDiGraph, D: nx.DiGraph, centrality_k: int, seed: int, max_betweenness_k: int = 200) -> Tuple[List[Dict], int, bool]:
    """
    计算 betweenness top-10（近似，带限速）
    返回: (bottlenecks, missing_geo_count, use_fallback)
    """
    # 从 D 中取 drive 子图（视图，不 copy）
    drive_nodes = set()
    for n, d in G_original.nodes(data=True):
        if d.get("layer") == "drive":
            drive_nodes.add(n)
    
    # 创建 drive 子图（视图）
    D_drive = D.subgraph(drive_nodes)
    
    if D_drive.number_of_nodes() == 0:
        return [], 0, True
    
    n = D_drive.number_of_nodes()
    
    # 自适应限制 k
    effective_k = min(centrality_k, n, max_betweenness_k if n > 50000 else centrality_k)
    print(f"  Effective k capped: {centrality_k} -> {effective_k} (n={n:,})")
    
    # 若 effective_k < 10，fallback 到 od_sample
    if effective_k < 10:
        print(f"  Warning: effective_k ({effective_k}) < 10, fallback to od_sample method")
        return [], 0, True
    
    # 使用 betweenness_centrality（近似，k=effective_k）
    betweenness = nx.betweenness_centrality(
        D_drive, k=effective_k, seed=seed, weight='cost', normalized=True
    )
    
    # 取 top-10
    sorted_nodes = sorted(betweenness.items(), key=lambda x: x[1], reverse=True)
    top10 = sorted_nodes[:10]
    
    # 收集节点坐标
    bottlenecks = []
    missing_geo_count = 0
    
    for rank, (node_id, bc_value) in enumerate(top10, 1):
        # 优先从原图节点属性 pos=(lon,lat) 读取
        node_data = G_original.nodes.get(node_id, {})
        pos = node_data.get("pos")
        
        if pos is not None and isinstance(pos, (list, tuple)) and len(pos) == 2:
            lon, lat = pos[0], pos[1]
        else:
            lon, lat = None, None
            missing_geo_count += 1
        
        bottlenecks.append({
            "rank": rank,
            "node_id": node_id,
            "betweenness": bc_value,
            "lon": lon,
            "lat": lat
        })
    
    return bottlenecks, missing_geo_count, False


def main():
    parser = argparse.ArgumentParser(description="Baseline Analysis")
    parser.add_argument("--graph", type=str, default="data/processed/graph.pkl",
                       help="Path to graph.pkl")
    parser.add_argument("--outdir", type=str, default="outputs/baseline",
                       help="Output directory")
    parser.add_argument("--K", type=int, default=100,
                       help="Number of OD pairs")
    parser.add_argument("--seed", type=int, default=42,
                       help="Random seed")
    parser.add_argument("--od_policy", type=str, default="drive_lcc",
                       help="OD policy: drive_lcc or random")
    parser.add_argument("--centrality_k", type=int, default=2000,
                       help="Number of nodes for betweenness approximation")
    parser.add_argument("--centrality_method", type=str, default="od_sample",
                       choices=["od_sample", "approx_betweenness"],
                       help="Centrality method: od_sample (fast) or approx_betweenness (slow but exact)")
    parser.add_argument("--max_betweenness_k", type=int, default=200,
                       help="Maximum k for betweenness when graph is large (>50000 nodes)")
    
    args = parser.parse_args()
    
    graph_path = Path(args.graph).resolve()
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    
    print("=" * 80)
    print("Baseline Analysis")
    print("=" * 80)
    print(f"Graph: {graph_path}")
    print(f"Output: {outdir}")
    print(f"K: {args.K}, Seed: {args.seed}, Policy: {args.od_policy}")
    print(f"Centrality method: {args.centrality_method}")
    if args.centrality_method == "approx_betweenness":
        print(f"Centrality k: {args.centrality_k}, Max k: {args.max_betweenness_k}")
    print()
    
    # A) 加载图
    print("[A] Loading graph...")
    G, n_nodes, n_edges = load_graph(graph_path)
    print(f"  Nodes: {n_nodes:,}, Edges: {n_edges:,}")
    
    # B) 选取 OD pairs
    print(f"\n[B] Getting OD pairs (policy: {args.od_policy})...")
    od_pairs, od_pairs_path = get_od_pairs(G, args.K, args.seed, args.od_policy, str(graph_path))
    print(f"  OD pairs: {len(od_pairs)}")
    print(f"  Path: {od_pairs_path}")
    
    # C) MultiDiGraph 合并成 DiGraph
    print("\n[C] Converting MultiDiGraph to DiGraph...")
    D, missing_cost_edges = multigraph_to_digraph(G)
    print(f"  DiGraph nodes: {D.number_of_nodes():,}, edges: {D.number_of_edges():,}")
    print(f"  Missing cost edges: {missing_cost_edges}")
    
    # D) 连通性 + cost sanity
    print("\n[D] Connectivity + cost sanity...")
    connectivity_result = connectivity_sanity(D, od_pairs)
    print(f"  Reachable: {connectivity_result['reachable_count']}/{len(od_pairs)} ({connectivity_result['reachable_ratio']*100:.1f}%)")
    print(f"  Cost stats: min={connectivity_result['cost_min']}, median={connectivity_result['cost_median']}, "
          f"p95={connectivity_result['cost_p95']}, max={connectivity_result['cost_max']}")
    
    # E) Bottleneck computation
    reachable_paths_count = 0
    use_fallback = False
    
    if args.centrality_method == "od_sample":
        print(f"\n[E] Computing OD-sampled bottlenecks top-10...")
        bottlenecks, missing_geo_count, reachable_paths_count = compute_od_sample_bottlenecks_top10(
            G, D, od_pairs, args.seed
        )
        print(f"  Top-10 nodes computed")
        print(f"  Reachable paths: {reachable_paths_count}")
        print(f"  Missing geo count: {missing_geo_count}")
    else:  # approx_betweenness
        print(f"\n[E] Computing betweenness top-10 (k={args.centrality_k})...")
        bottlenecks, missing_geo_count, use_fallback = compute_betweenness_top10(
            G, D, args.centrality_k, args.seed, args.max_betweenness_k
        )
        
        if use_fallback:
            print(f"  Warning: Fallback to OD-sampled method")
            bottlenecks, missing_geo_count, reachable_paths_count = compute_od_sample_bottlenecks_top10(
                G, D, od_pairs, args.seed
            )
            args.centrality_method = "od_sample"  # 更新方法标记
        else:
            print(f"  Top-10 nodes computed")
            print(f"  Missing geo count: {missing_geo_count}")
    
    # 生成输出文件
    print("\n[Output] Generating output files...")
    
    # 1) baseline_metrics.csv
    timestamp = datetime.now().isoformat()
    # 按照要求的字段顺序
    metrics_data = {
        "timestamp": timestamp,
        "graph_path": str(graph_path.relative_to(ROOT_DIR)),
        "K": args.K,
        "seed": args.seed,
        "od_policy": args.od_policy,
        "reachable_count": connectivity_result["reachable_count"],
        "unreachable_count": connectivity_result["unreachable_count"],
        "reachable_ratio": connectivity_result["reachable_ratio"],
        "cost_min": connectivity_result["cost_min"],
        "cost_median": connectivity_result["cost_median"],
        "cost_p95": connectivity_result["cost_p95"],
        "cost_max": connectivity_result["cost_max"],
        "n_nodes": n_nodes,
        "n_edges": n_edges,
        "centrality_k": args.centrality_k if args.centrality_method == "approx_betweenness" else None,
        "missing_geo_count": missing_geo_count,
        "missing_cost_edges": missing_cost_edges,
        "od_pairs_path": od_pairs_path
    }
    
    # 按照要求的字段顺序创建 DataFrame
    column_order = [
        "timestamp", "graph_path", "K", "seed", "od_policy",
        "reachable_count", "unreachable_count", "reachable_ratio",
        "cost_min", "cost_median", "cost_p95", "cost_max",
        "n_nodes", "n_edges", "centrality_k",
        "missing_geo_count", "missing_cost_edges", "od_pairs_path"
    ]
    metrics_df = pd.DataFrame([metrics_data])[column_order]
    metrics_path = outdir / "baseline_metrics.csv"
    metrics_df.to_csv(metrics_path, index=False)
    print(f"  [OK] {metrics_path}")
    
    # 2) bottlenecks_top10_nodes.csv
    bottlenecks_df = pd.DataFrame(bottlenecks)
    bottlenecks_path = outdir / "bottlenecks_top10_nodes.csv"
    bottlenecks_df.to_csv(bottlenecks_path, index=False)
    print(f"  [OK] {bottlenecks_path}")
    
    # 3) baseline_report.md
    report_lines = []
    report_lines.append("# Baseline Analysis Report")
    report_lines.append("")
    report_lines.append(f"**Generated:** {timestamp}")
    report_lines.append("")
    report_lines.append("## Graph Statistics")
    report_lines.append("")
    report_lines.append(f"- **Nodes:** {n_nodes:,}")
    report_lines.append(f"- **Edges:** {n_edges:,}")
    report_lines.append("")
    report_lines.append("## OD Pairs")
    report_lines.append("")
    report_lines.append(f"- **Policy:** {args.od_policy}")
    report_lines.append(f"- **Count:** {len(od_pairs)}")
    report_lines.append(f"- **Path:** {od_pairs_path}")
    report_lines.append("")
    report_lines.append("## Connectivity + Cost Sanity")
    report_lines.append("")
    report_lines.append(f"- **Reachable:** {connectivity_result['reachable_count']} / {len(od_pairs)} ({connectivity_result['reachable_ratio']*100:.1f}%)")
    report_lines.append(f"- **Unreachable:** {connectivity_result['unreachable_count']}")
    report_lines.append("")
    
    if connectivity_result['reachable_count'] > 0:
        report_lines.append("Cost Statistics (reachable pairs only):")
        report_lines.append(f"- **Min:** {connectivity_result['cost_min']}")
        report_lines.append(f"- **Median:** {connectivity_result['cost_median']}")
        report_lines.append(f"- **P95:** {connectivity_result['cost_p95']}")
        report_lines.append(f"- **Max:** {connectivity_result['cost_max']}")
    else:
        report_lines.append("**Warning:** No reachable pairs found. Cost statistics are NA.")
        report_lines.append("This may indicate connectivity issues in the graph.")
    
    report_lines.append("")
    report_lines.append("## Data Quality")
    report_lines.append("")
    report_lines.append(f"- **Missing geo count:** {missing_geo_count}")
    report_lines.append(f"- **Missing cost edges:** {missing_cost_edges}")
    report_lines.append("")
    report_lines.append("## Bottleneck Analysis")
    report_lines.append("")
    report_lines.append(f"- **Centrality method:** {args.centrality_method}")
    
    if args.centrality_method == "od_sample":
        report_lines.append(f"- **Reachable paths count:** {reachable_paths_count}")
        report_lines.append("- **Note:** The 'betweenness' field in the table below is an OD-sampled path load proxy (normalized count / reachable_paths_count)")
        report_lines.append("- **Why OD-sampled proxy instead of full betweenness:** 更贴合通勤出行影响，也更可计算。这样审稿人也更能接受")
    else:
        report_lines.append(f"- **Betweenness approximation k:** {args.centrality_k}")
        report_lines.append("- **Note:** The 'betweenness' field in the table below is NetworkX approximate betweenness centrality")
    
    report_lines.append("")
    report_lines.append("## Top-10 Bottleneck Nodes")
    report_lines.append("")
    
    if bottlenecks:
        # Markdown 表格
        report_lines.append("| Rank | Node ID | Betweenness | Lon | Lat |")
        report_lines.append("|------|---------|-------------|-----|-----|")
        for b in bottlenecks:
            lon_str = str(b['lon']) if b['lon'] is not None else "N/A"
            lat_str = str(b['lat']) if b['lat'] is not None else "N/A"
            report_lines.append(f"| {b['rank']} | {b['node_id']} | {b['betweenness']:.6f} | {lon_str} | {lat_str} |")
    else:
        report_lines.append("No bottleneck nodes computed.")
    
    report_lines.append("")
    report_lines.append("---")
    report_lines.append("")
    report_lines.append("**Files:**")
    report_lines.append(f"- `baseline_metrics.csv`")
    report_lines.append(f"- `bottlenecks_top10_nodes.csv`")
    report_lines.append(f"- `baseline_report.md`")
    
    report_path = outdir / "baseline_report.md"
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(report_lines))
    print(f"  [OK] {report_path}")
    
    print("\n" + "=" * 80)
    print("Baseline analysis completed.")
    print("=" * 80)


if __name__ == "__main__":
    main()
