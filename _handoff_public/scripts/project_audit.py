"""
project_audit.py
工程审计器脚本 - Stage A/B/C/D/E 验收

运行方式:
    python scripts/project_audit.py --strict
    python scripts/project_audit.py --strict --run-smoke
"""

import argparse
import json
import pickle
import re
import sys
import zipfile
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import networkx as nx
import numpy as np
import pandas as pd

ROOT_DIR = Path(__file__).parent.parent
OUTPUT_DIR = ROOT_DIR / "outputs" / "audit"


# ==================
# 工具函数
# ==================
def list_tree(root: Path, focus_paths: List[Path]) -> str:
    """生成目录树结构（focus_paths 为关注路径）"""
    lines = []
    
    def _tree(p: Path, prefix: str = "", is_last: bool = True):
        if p.is_file():
            marker = "└── " if is_last else "├── "
            lines.append(f"{prefix}{marker}{p.name}")
        elif p.is_dir():
            marker = "└── " if is_last else "├── "
            lines.append(f"{prefix}{marker}{p.name}/")
            children = sorted([child for child in p.iterdir() if child.name[0] != '.'])
            for i, child in enumerate(children):
                is_last_child = (i == len(children) - 1)
                extension = "    " if is_last else "│   "
                _tree(child, prefix + extension, is_last_child)
    
    _tree(root)
    return "\n".join(lines)


def check_exists(path: Path) -> bool:
    """检查路径是否存在"""
    return path.exists()


def read_csv_schema(path: Path) -> Dict:
    """读取 CSV schema（行数、列名）"""
    if not path.exists():
        return {"n_rows": 0, "cols": []}
    
    try:
        df = pd.read_csv(path, low_memory=False, nrows=0)  # 只读header
        return {
            "n_rows": len(pd.read_csv(path, low_memory=False)),
            "cols": list(df.columns)
        }
    except Exception as e:
        return {"n_rows": 0, "cols": [], "error": str(e)}


def require_cols(cols: List[str], required_cols: List[str]) -> List[str]:
    """检查必需列，返回缺失列列表"""
    missing = [c for c in required_cols if c not in cols]
    return missing


def load_graph_pkl(path: Path) -> Tuple[Optional[nx.Graph], int, int]:
    """加载 graph.pkl，返回 (G, |V|, |E|)"""
    if not path.exists():
        return None, 0, 0
    
    try:
        with open(path, 'rb') as f:
            G = pickle.load(f)
        return G, G.number_of_nodes(), G.number_of_edges()
    except Exception as e:
        return None, 0, 0


def run_dijkstra_smoke(G: nx.Graph, K: int = 30, seed: int = 42) -> Dict:
    """运行 Dijkstra smoke test，返回统计信息"""
    if G is None:
        return {"error": "Graph is None"}
    
    np.random.seed(seed)
    
    # 获取所有节点
    nodes = list(G.nodes())
    if len(nodes) < 2:
        return {"error": "Not enough nodes"}
    
    # 随机抽样 K 对 OD
    od_pairs = []
    for _ in range(K):
        u = np.random.choice(nodes)
        v = np.random.choice(nodes)
        if u != v:
            od_pairs.append((u, v))
    
    # 运行 Dijkstra
    reachable_count = 0
    costs = []
    
    for u, v in od_pairs:
        try:
            # 直接使用 shortest_path_length 计算 cost
            cost = nx.shortest_path_length(G, u, v, weight='cost')
            if cost != float('inf'):
                costs.append(cost)
                reachable_count += 1
        except (nx.NetworkXNoPath, nx.NodeNotFound, nx.NetworkXError):
            pass
    
    reachable_ratio = reachable_count / len(od_pairs) if od_pairs else 0.0
    
    # 统计 cost 分布
    if costs:
        costs_arr = np.array(costs)
        stats = {
            "min": float(np.min(costs_arr)),
            "median": float(np.median(costs_arr)),
            "p95": float(np.percentile(costs_arr, 95)),
            "max": float(np.max(costs_arr)),
            "mean": float(np.mean(costs_arr))
        }
    else:
        stats = {"min": 0, "median": 0, "p95": 0, "max": 0, "mean": 0}
    
    return {
        "reachable_ratio": reachable_ratio,
        "reachable_count": reachable_count,
        "total_pairs": len(od_pairs),
        "cost_stats": stats,
        "warnings": []
    }


# ==================
# Stage A: Data ETL 审计
# ==================
def audit_stage_a(root_dir: Path, strict: bool) -> Dict:
    """Stage A: Data ETL 审计"""
    result = {
        "stage": "Stage A: Data ETL",
        "required_files": {},
        "optional_files": {},
        "schema_checks": {},
        "warnings": [],
        "missing_required": [],
        "pass": True
    }
    
    processed_dir = root_dir / "data" / "processed"
    scripts_dir = root_dir / "scripts"
    
    # REQUIRED 文件
    required_files = {
        "data_clean_script": scripts_dir / "data_clean.py",
        "cleaning_log": processed_dir / "cleaning_log.md",
        "nodes_clean": processed_dir / "nodes_clean.csv",
        "edges_clean": processed_dir / "edges_clean.csv",
        "bus_stops_clean": processed_dir / "bus_stops_clean.csv",
        "graph_pkl": processed_dir / "graph.pkl",
        "base_map": processed_dir / "base_map.csv",
    }
    
    for name, path in required_files.items():
        exists = check_exists(path)
        result["required_files"][name] = {
            "path": str(path.relative_to(root_dir)),
            "exists": exists
        }
        if not exists:
            result["missing_required"].append(name)
            if strict:
                result["pass"] = False
    
    # OPTIONAL 文件
    optional_files = {
        "boundary": processed_dir / "boundary.geojson",
        "graph_nodes": processed_dir / "graph_nodes.csv",
        "graph_edges_kepler": processed_dir / "graph_edges_kepler.csv",
        "data_dictionary": root_dir / "data_dictionary.md",
    }
    
    for name, path in optional_files.items():
        exists = check_exists(path)
        result["optional_files"][name] = {
            "path": str(path.relative_to(root_dir)),
            "exists": exists
        }
        if not exists:
            result["warnings"].append(f"Optional file missing: {name}")
    
    # Schema 校验
    # base_map.csv
    base_map_path = processed_dir / "base_map.csv"
    if base_map_path.exists():
        schema = read_csv_schema(base_map_path)
        required_cols = ["id", "lat", "lon", "type", "layer"]
        missing = require_cols(schema.get("cols", []), required_cols)
        result["schema_checks"]["base_map"] = {
            "n_rows": schema.get("n_rows", 0),
            "cols": schema.get("cols", [])[:20],  # 前20列
            "missing_cols": missing
        }
        if missing and strict:
            result["pass"] = False
            result["warnings"].append(f"base_map.csv missing columns: {missing}")
    
    # graph_nodes.csv (optional)
    graph_nodes_path = processed_dir / "graph_nodes.csv"
    if graph_nodes_path.exists():
        schema = read_csv_schema(graph_nodes_path)
        required_cols = ["node_id", "lon", "lat", "type", "layer", "original_id", "name"]
        missing = require_cols(schema.get("cols", []), required_cols)
        result["schema_checks"]["graph_nodes"] = {
            "n_rows": schema.get("n_rows", 0),
            "cols": schema.get("cols", [])[:20],
            "missing_cols": missing
        }
        if missing:
            result["warnings"].append(f"graph_nodes.csv missing columns: {missing}")
    
    # graph_edges_kepler.csv (optional)
    graph_edges_kepler_path = processed_dir / "graph_edges_kepler.csv"
    if graph_edges_kepler_path.exists():
        schema = read_csv_schema(graph_edges_kepler_path)
        required_cols = [
            "u", "v", "key", "mode", "cost", "weight", "distance",
            "transfer_type", "highway", "capacity", "u_lat", "u_lon", "v_lat", "v_lon"
        ]
        missing = require_cols(schema.get("cols", []), required_cols)
        result["schema_checks"]["graph_edges_kepler"] = {
            "n_rows": schema.get("n_rows", 0),
            "cols": schema.get("cols", [])[:20],
            "missing_cols": missing
        }
        if missing:
            result["warnings"].append(f"graph_edges_kepler.csv missing columns: {missing}")
    
    return result


# ==================
# Stage B: Baseline & Sanity 审计
# ==================
def audit_stage_b(root_dir: Path, strict: bool, run_smoke: bool = False) -> Dict:
    """Stage B: Baseline & Sanity 审计"""
    result = {
        "stage": "Stage B: Baseline & Sanity",
        "baseline_script_found": False,
        "baseline_script_path": None,
        "baseline_output_dir_exists": False,
        "baseline_output_files": [],
        "smoke_test": None,
        "pass": True
    }
    
    scripts_dir = root_dir / "scripts"
    baseline_output_dir = root_dir / "outputs" / "baseline"
    
    # 搜索 baseline 脚本
    baseline_patterns = ["baseline_analysis.py", "baseline_sanity.py", "baseline_check.py"]
    baseline_scripts = []
    
    for pattern in baseline_patterns:
        script_path = scripts_dir / pattern
        if script_path.exists():
            baseline_scripts.append(script_path)
    
    # 也搜索包含 "baseline" 的 .py 文件
    if not baseline_scripts:
        for script_file in scripts_dir.glob("*baseline*.py"):
            if script_file.exists():
                baseline_scripts.append(script_file)
    
    if baseline_scripts:
        result["baseline_script_found"] = True
        result["baseline_script_path"] = str(baseline_scripts[0].relative_to(root_dir))
    else:
        if strict:
            result["pass"] = False
    
    # 检查 baseline 输出目录
    if baseline_output_dir.exists():
        result["baseline_output_dir_exists"] = True
        result["baseline_output_files"] = [
            f.name for f in baseline_output_dir.iterdir() if f.is_file()
        ]
    
    # Smoke test
    if run_smoke:
        graph_path = root_dir / "data" / "processed" / "graph.pkl"
        G, n_nodes, n_edges = load_graph_pkl(graph_path)
        
        if G is not None:
            smoke_result = run_dijkstra_smoke(G, K=30, seed=42)
            smoke_result["n_nodes"] = n_nodes
            smoke_result["n_edges"] = n_edges
            
            # 检查 cost 异常
            cost_stats = smoke_result.get("cost_stats", {})
            max_cost = cost_stats.get("max", 0)
            min_cost = cost_stats.get("min", 0)
            
            if max_cost > 1e6:
                smoke_result["warnings"] = smoke_result.get("warnings", [])
                smoke_result["warnings"].append(f"Cost extremely high: {max_cost:.2e}")
            if min_cost <= 0:
                smoke_result["warnings"] = smoke_result.get("warnings", [])
                smoke_result["warnings"].append(f"Cost <= 0: {min_cost}")
            
            result["smoke_test"] = smoke_result
        else:
            result["smoke_test"] = {"error": "Cannot load graph.pkl"}
    
    return result


# ==================
# Forbidden Grep 检查
# ==================
def forbidden_grep_check(root_dir: Path, pattern: str = "graph_with_cost") -> Dict:
    """全仓库递归 grep 字符串（审计用：搜索历史残留），strict FAIL"""
    result = {
        "pattern": pattern,
        "matches": [],
        "pass": True
    }
    
    # 排除目录
    exclude_dirs = {".git", "__pycache__", ".pytest_cache", "node_modules", ".venv", "venv", "env", ".agent", ".cursor"}
    exclude_extensions = {".pyc", ".pyo", ".pyd", ".zip", ".rar", ".7z", ".tar", ".gz"}
    
    # 排除审计脚本本身和相关文件（这些文件包含 pattern 是正常的）
    exclude_files = {
        "scripts/project_audit.py",
        "mcp_servers/icm_d_server.py",
        "prompt/forbidden_grep.md",
        "outputs/audit/forbidden_grep_graph_with_cost.txt",
        "outputs/audit/audit_tree.txt"
    }
    exclude_files = {p.replace("\\", "/").lower() for p in exclude_files}
    
    # 递归搜索
    for path in root_dir.rglob("*"):
        # 跳过排除目录
        if any(part in exclude_dirs for part in path.parts):
            continue
        
        # 跳过排除扩展名
        if path.suffix in exclude_extensions:
            continue
        
        # 跳过排除文件
        rel_path_str = path.relative_to(root_dir).as_posix().lower()
        if rel_path_str in exclude_files:
            continue
        
        # 只搜索文本文件（.py, .md, .txt, .json, .csv, .sh, .bat, 等）
        if path.is_file():
            try:
                # 尝试读取文件（二进制模式，避免编码问题）
                with open(path, 'rb') as f:
                    content = f.read()
                    
                # 尝试解码为文本（UTF-8 或 latin-1）
                try:
                    text = content.decode('utf-8')
                except UnicodeDecodeError:
                    try:
                        text = content.decode('latin-1')
                    except UnicodeDecodeError:
                        continue  # 二进制文件，跳过
                
                # 搜索模式
                for line_num, line in enumerate(text.splitlines(), 1):
                    if pattern in line:
                        # 截断行内容（前100字符）
                        line_truncated = line[:100] + "..." if len(line) > 100 else line
                        result["matches"].append({
                            "file": str(path.relative_to(root_dir)),
                            "line": line_num,
                            "content": line_truncated
                        })
            except Exception:
                # 读取失败，跳过
                continue
    
    if result["matches"]:
        result["pass"] = False
    
    return result


# ==================
# Stage C: Engine（Task2 求解引擎）
# ==================
def audit_stage_c(root_dir: Path, strict: bool) -> Dict:
    """Stage C: Engine 审计"""
    result = {
        "stage": "Stage C: Engine",
        "required_files": {},
        "candidates_validation": {},
        "pass": True,
        "warnings": [],
        "missing_required": []
    }
    
    scripts_dir = root_dir / "scripts"
    processed_dir = root_dir / "data" / "processed"
    
    # REQUIRED 文件
    required_files = {
        "experiment_schema": scripts_dir / "experiment_schema.py",
        "run_hybrid_pso_ga": scripts_dir / "run_hybrid_pso_ga_task2.py",
        "od_sampling": scripts_dir / "od_sampling.py",
        "run_resilience": scripts_dir / "run_resilience_task2.py",
        "candidates": processed_dir / "candidates_task2.json"
    }
    
    # 搜索 pso.py 和 ga.py
    pso_paths = list(root_dir.rglob("pso.py"))
    ga_paths = list(root_dir.rglob("ga.py"))
    
    # 排除 __pycache__ 和虚拟环境
    pso_paths = [p for p in pso_paths if "__pycache__" not in str(p) and "venv" not in str(p) and ".venv" not in str(p)]
    ga_paths = [p for p in ga_paths if "__pycache__" not in str(p) and "venv" not in str(p) and ".venv" not in str(p)]
    
    if pso_paths:
        result["required_files"]["pso"] = {
            "path": str(pso_paths[0].relative_to(root_dir)),
            "exists": True
        }
    else:
        result["required_files"]["pso"] = {
            "path": "NOT_FOUND",
            "exists": False
        }
        result["missing_required"].append("pso")
        if strict:
            result["pass"] = False
    
    if ga_paths:
        result["required_files"]["ga"] = {
            "path": str(ga_paths[0].relative_to(root_dir)),
            "exists": True
        }
    else:
        result["required_files"]["ga"] = {
            "path": "NOT_FOUND",
            "exists": False
        }
        result["missing_required"].append("ga")
        if strict:
            result["pass"] = False
    
    for name, path in required_files.items():
        exists = check_exists(path)
        result["required_files"][name] = {
            "path": str(path.relative_to(root_dir)),
            "exists": exists
        }
        if not exists:
            result["missing_required"].append(name)
            if strict:
                result["pass"] = False
    
    # 校验 candidates_task2.json 格式
    candidates_path = processed_dir / "candidates_task2.json"
    if candidates_path.exists():
        try:
            with open(candidates_path, 'r', encoding='utf-8') as f:
                candidates = json.load(f)
            
            # 严格校验
            validation = {
                "is_list": isinstance(candidates, list),
                "error": None,
                "first_candidate_keys": None,
                "first_edge_structure": None
            }
            
            if not isinstance(candidates, list):
                validation["error"] = f"顶层必须是 list，实际是 {type(candidates).__name__}"
                result["pass"] = False
            elif len(candidates) == 0:
                validation["error"] = "candidates 列表为空"
                result["warnings"].append("candidates 列表为空")
            else:
                # 检查第一个 candidate
                first_candidate = candidates[0]
                validation["first_candidate_keys"] = list(first_candidate.keys()) if isinstance(first_candidate, dict) else None
                
                # 检查必需字段
                if not isinstance(first_candidate, dict):
                    validation["error"] = f"元素必须是 dict，实际是 {type(first_candidate).__name__}"
                    result["pass"] = False
                else:
                    if "id" not in first_candidate:
                        validation["error"] = "缺少必需字段: id"
                        result["pass"] = False
                    if "edges" not in first_candidate:
                        validation["error"] = "缺少必需字段: edges"
                        result["pass"] = False
                    else:
                        edges = first_candidate.get("edges", [])
                        if not isinstance(edges, list):
                            validation["error"] = f"edges 必须是 list，实际是 {type(edges).__name__}"
                            result["pass"] = False
                        elif len(edges) > 0:
                            first_edge = edges[0]
                            validation["first_edge_structure"] = {
                                "type": type(first_edge).__name__,
                                "length": len(first_edge) if isinstance(first_edge, (list, tuple)) else None,
                                "repr": str(first_edge)[:100] if len(str(first_edge)) > 100 else str(first_edge)
                            }
                            
                            # 检查 edge 格式：[u, v, attrs_dict]
                            if not isinstance(first_edge, (list, tuple)) or len(first_edge) != 3:
                                validation["error"] = f"edge 必须是长度为 3 的 list/tuple，实际长度: {len(first_edge) if isinstance(first_edge, (list, tuple)) else 'N/A'}"
                                result["pass"] = False
                            else:
                                attrs = first_edge[2]
                                if not isinstance(attrs, dict):
                                    validation["error"] = f"edge[2] 必须是 dict，实际是 {type(attrs).__name__}"
                                    result["pass"] = False
                                else:
                                    if "mode" not in attrs:
                                        validation["error"] = "attrs_dict 缺少必需字段: mode"
                                        result["pass"] = False
                                    if "cost" not in attrs:
                                        validation["error"] = "attrs_dict 缺少必需字段: cost"
                                        result["pass"] = False
            
            result["candidates_validation"] = validation
            
        except json.JSONDecodeError as e:
            result["candidates_validation"] = {
                "error": f"JSON 解析错误: {str(e)}",
                "is_list": False
            }
            result["pass"] = False
        except Exception as e:
            result["candidates_validation"] = {
                "error": f"读取错误: {str(e)}",
                "is_list": False
            }
            result["pass"] = False
    else:
        result["candidates_validation"] = {
            "error": "文件不存在"
        }
        result["pass"] = False
    
    return result


# ==================
# Stage D: Experiment Logging（Task2 实验记录）
# ==================
def audit_stage_d(root_dir: Path, strict: bool) -> Dict:
    """Stage D: Experiment Logging 审计"""
    result = {
        "stage": "Stage D: Experiment Logging",
        "required_files": {},
        "schema_checks": {},
        "consistency_checks": {},
        "pass": True,
        "warnings": [],
        "missing_required": []
    }
    
    task2_dir = root_dir / "outputs" / "task2"
    
    # REQUIRED 文件
    required_files = {
        "metrics": task2_dir / "metrics.csv",
        "runtime": task2_dir / "runtime.csv",
        "experiments_log": task2_dir / "experiments_log.md",
        "best_solution": task2_dir / "best_solution.json",
        "metrics_schema": task2_dir / "metrics_schema.md",
        "runtime_schema": task2_dir / "runtime_schema.md",
        "convergence_history": task2_dir / "convergence_history.csv"
    }
    
    for name, path in required_files.items():
        exists = check_exists(path)
        result["required_files"][name] = {
            "path": str(path.relative_to(root_dir)),
            "exists": exists
        }
        if not exists:
            result["missing_required"].append(name)
            if strict:
                result["pass"] = False
    
    # Schema 校验
    # metrics.csv
    metrics_path = task2_dir / "metrics.csv"
    if metrics_path.exists():
        schema = read_csv_schema(metrics_path)
        required_cols = [
            "run_id", "timestamp", "graph_path", "candidates_path",
            "seed", "K", "od_seed", "od_policy", "budget", "lambda_reg", "unreachable_penalty",
            "pso_particles", "pso_iter", "ga_pop", "ga_gen",
            "best_total_obj", "best_reachable_ratio", "best_mean_cost_reachable",
            "best_reachable_count", "best_unreachable_count",
            "best_penalty_term", "best_regularization_term",
            "n_selected", "selected_ids"
        ]
        missing = require_cols(schema.get("cols", []), required_cols)
        result["schema_checks"]["metrics"] = {
            "n_rows": schema.get("n_rows", 0),
            "cols": schema.get("cols", []),
            "missing_cols": missing
        }
        if missing and strict:
            result["pass"] = False
    
    # runtime.csv
    runtime_path = task2_dir / "runtime.csv"
    if runtime_path.exists():
        schema = read_csv_schema(runtime_path)
        required_cols = ["run_id", "total_sec", "pso_sec", "ga_sec", "n_eval", "avg_eval_sec"]
        missing = require_cols(schema.get("cols", []), required_cols)
        result["schema_checks"]["runtime"] = {
            "n_rows": schema.get("n_rows", 0),
            "cols": schema.get("cols", []),
            "missing_cols": missing
        }
        if missing and strict:
            result["pass"] = False
    
    # convergence_history.csv
    convergence_path = task2_dir / "convergence_history.csv"
    if convergence_path.exists():
        schema = read_csv_schema(convergence_path)
        required_cols = [
            "run_id", "phase", "iter",
            "best_total_obj", "best_reachable_ratio", "best_mean_cost_reachable",
            "best_reachable_count", "best_unreachable_count",
            "best_penalty_term", "best_regularization_term"
        ]
        missing = require_cols(schema.get("cols", []), required_cols)
        result["schema_checks"]["convergence_history"] = {
            "n_rows": schema.get("n_rows", 0),
            "cols": schema.get("cols", []),
            "missing_cols": missing
        }
        if missing and strict:
            result["pass"] = False
    else:
        # convergence_history.csv 缺失（strict FAIL）
        if strict:
            result["pass"] = False
            result["warnings"].append("convergence_history.csv 缺失（流程图要求可复现收敛曲线）")
    
    # 合理性一致性检查
    best_solution_path = task2_dir / "best_solution.json"
    if metrics_path.exists() and best_solution_path.exists():
        try:
            metrics_df = pd.read_csv(metrics_path)
            with open(best_solution_path, 'r', encoding='utf-8') as f:
                best_solution = json.load(f)
            
            if len(metrics_df) > 0:
                # 取最新一行
                latest = metrics_df.iloc[-1]
                
                checks = {}
                
                # best_reachable_ratio ∈ [0,1]
                ratio = latest.get("best_reachable_ratio", None)
                if ratio is not None and (not isinstance(ratio, (int, float)) or ratio < 0 or ratio > 1):
                    checks["reachable_ratio_range"] = False
                    checks["reachable_ratio_value"] = ratio
                    result["pass"] = False
                else:
                    checks["reachable_ratio_range"] = True
                
                # best_reachable_count + best_unreachable_count == K
                reachable_count = latest.get("best_reachable_count", None)
                unreachable_count = latest.get("best_unreachable_count", None)
                K = latest.get("K", None)
                if all(x is not None for x in [reachable_count, unreachable_count, K]):
                    if reachable_count + unreachable_count != K:
                        checks["count_sum"] = False
                        checks["count_sum_details"] = f"{reachable_count} + {unreachable_count} != {K}"
                        result["pass"] = False
                    else:
                        checks["count_sum"] = True
                else:
                    checks["count_sum"] = None
                
                # best_reachable_ratio==1 且 best_unreachable_count==0，则 best_penalty_term 必须==0
                if ratio == 1.0 and unreachable_count == 0:
                    penalty_term = latest.get("best_penalty_term", None)
                    if penalty_term is not None and abs(penalty_term) > 1e-9:
                        checks["penalty_term_consistency"] = False
                        checks["penalty_term_value"] = penalty_term
                        result["pass"] = False
                    else:
                        checks["penalty_term_consistency"] = True
                else:
                    checks["penalty_term_consistency"] = None
                
                result["consistency_checks"] = checks
            
            # 检查 best_solution.json 必需字段
            solution_required_fields = ["run_id", "selected_ids", "n_selected", "best_total_obj", "best_reachable_ratio", "best_penalty_term"]
            missing_fields = [f for f in solution_required_fields if f not in best_solution]
            if missing_fields:
                result["consistency_checks"]["best_solution_missing_fields"] = missing_fields
                result["pass"] = False
            else:
                result["consistency_checks"]["best_solution_missing_fields"] = []
                
                # 检查 selected_ids 是 list
                if not isinstance(best_solution.get("selected_ids", []), list):
                    result["consistency_checks"]["selected_ids_type"] = type(best_solution.get("selected_ids")).__name__
                    result["pass"] = False
                else:
                    result["consistency_checks"]["selected_ids_type"] = "list"
                    
        except Exception as e:
            result["consistency_checks"]["error"] = str(e)
            result["warnings"].append(f"一致性检查失败: {str(e)}")
    
    return result


# ==================
# Stage E: Robustness（鲁棒性）
# ==================
def audit_stage_e(root_dir: Path, strict: bool) -> Dict:
    """Stage E: Robustness 审计"""
    result = {
        "stage": "Stage E: Robustness",
        "required_files": {},
        "consistency_checks": {},
        "pass": True,
        "warnings": [],
        "missing_required": []
    }
    
    task2_dir = root_dir / "outputs" / "task2"
    
    # REQUIRED 文件
    required_files = {
        "resilience_table": task2_dir / "resilience_table.csv",
        "resilience_curve": task2_dir / "resilience_curve.csv",
        "resilience_schema": task2_dir / "resilience_schema.md"
    }
    
    for name, path in required_files.items():
        exists = check_exists(path)
        result["required_files"][name] = {
            "path": str(path.relative_to(root_dir)),
            "exists": exists
        }
        if not exists:
            result["missing_required"].append(name)
            if strict:
                result["pass"] = False
    
    # 检查 od_pairs_*.json（至少 1 个）
    od_pairs_files = list(task2_dir.glob("od_pairs_*.json"))
    result["required_files"]["od_pairs_files"] = {
        "path": f"{len(od_pairs_files)} files found",
        "exists": len(od_pairs_files) > 0,
        "count": len(od_pairs_files),
        "files": [str(f.name) for f in od_pairs_files[:10]]
    }
    if len(od_pairs_files) == 0:
        result["missing_required"].append("od_pairs_*.json")
        if strict:
            result["pass"] = False
    
    # 检查 cache_*lscc*.json（至少 1 个）
    cache_files = list(task2_dir.glob("cache_*lscc*.json"))
    result["required_files"]["cache_lscc_files"] = {
        "path": f"{len(cache_files)} files found",
        "exists": len(cache_files) > 0,
        "count": len(cache_files),
        "files": [str(f.name) for f in cache_files[:10]]
    }
    if len(cache_files) == 0:
        result["missing_required"].append("cache_*lscc*.json")
        if strict:
            result["pass"] = False
    
    # 一致性检查
    best_solution_path = task2_dir / "best_solution.json"
    resilience_table_path = task2_dir / "resilience_table.csv"
    
    if best_solution_path.exists() and resilience_table_path.exists():
        try:
            with open(best_solution_path, 'r', encoding='utf-8') as f:
                best_solution = json.load(f)
            
            solution_run_id = best_solution.get("run_id")
            baseline_obj = best_solution.get("best_total_obj")
            baseline_ratio = best_solution.get("best_reachable_ratio")
            baseline_unreachable = best_solution.get("best_unreachable_count")
            baseline_penalty = best_solution.get("best_penalty_term")
            baseline_reg = best_solution.get("best_regularization_term")
            
            # 读取 resilience_table.csv
            resilience_df = pd.read_csv(resilience_table_path)
            
            # 筛选 attack_ratio==0 且 solution_run_id 匹配的行
            filtered = resilience_df[
                (resilience_df.get("attack_ratio", resilience_df.get("attack_ratio", pd.Series([None]))).fillna(0) == 0) &
                (resilience_df.get("solution_run_id", "") == solution_run_id)
            ]
            
            if len(filtered) > 0:
                row = filtered.iloc[0]
                
                checks = {}
                tolerance = 1e-9
                
                # 对比 best_total_obj
                resilience_obj = row.get("best_total_obj")
                if resilience_obj is not None and baseline_obj is not None:
                    if abs(float(resilience_obj) - float(baseline_obj)) > tolerance:
                        checks["obj_match"] = False
                        checks["obj_diff"] = float(resilience_obj) - float(baseline_obj)
                        checks["obj_baseline"] = baseline_obj
                        checks["obj_resilience"] = resilience_obj
                        result["pass"] = False
                    else:
                        checks["obj_match"] = True
                
                # 对比 best_reachable_ratio
                resilience_ratio = row.get("best_reachable_ratio") if "best_reachable_ratio" in row else row.get("best_rachable_ratio")  # 容错拼写错误
                if resilience_ratio is not None and baseline_ratio is not None:
                    if abs(float(resilience_ratio) - float(baseline_ratio)) > tolerance:
                        checks["ratio_match"] = False
                        checks["ratio_diff"] = float(resilience_ratio) - float(baseline_ratio)
                        checks["ratio_baseline"] = baseline_ratio
                        checks["ratio_resilience"] = resilience_ratio
                        result["pass"] = False
                    else:
                        checks["ratio_match"] = True
                
                # 对比 best_unreachable_count
                resilience_unreachable = row.get("best_unreachable_count")
                if resilience_unreachable is not None and baseline_unreachable is not None:
                    if int(resilience_unreachable) != int(baseline_unreachable):
                        checks["unreachable_match"] = False
                        checks["unreachable_diff"] = int(resilience_unreachable) - int(baseline_unreachable)
                        checks["unreachable_baseline"] = baseline_unreachable
                        checks["unreachable_resilience"] = resilience_unreachable
                        result["pass"] = False
                    else:
                        checks["unreachable_match"] = True
                
                # 对比 best_penalty_term
                resilience_penalty = row.get("best_penalty_term")
                if resilience_penalty is not None and baseline_penalty is not None:
                    if abs(float(resilience_penalty) - float(baseline_penalty)) > tolerance:
                        checks["penalty_match"] = False
                        checks["penalty_diff"] = float(resilience_penalty) - float(baseline_penalty)
                        checks["penalty_baseline"] = baseline_penalty
                        checks["penalty_resilience"] = resilience_penalty
                        result["pass"] = False
                    else:
                        checks["penalty_match"] = True
                
                # 对比 best_regularization_term
                resilience_reg = row.get("best_regularization_term")
                if resilience_reg is not None and baseline_reg is not None:
                    if abs(float(resilience_reg) - float(baseline_reg)) > tolerance:
                        checks["reg_match"] = False
                        checks["reg_diff"] = float(resilience_reg) - float(baseline_reg)
                        checks["reg_baseline"] = baseline_reg
                        checks["reg_resilience"] = resilience_reg
                        result["pass"] = False
                    else:
                        checks["reg_match"] = True
                
                result["consistency_checks"] = checks
            else:
                result["warnings"].append(f"未找到 attack_ratio==0 且 solution_run_id=={solution_run_id} 的行")
                
        except Exception as e:
            result["consistency_checks"]["error"] = str(e)
            result["warnings"].append(f"一致性检查失败: {str(e)}")
    
    # 检查 resilience_curve.csv 包含 attack_ratio=0
    resilience_curve_path = task2_dir / "resilience_curve.csv"
    if resilience_curve_path.exists():
        try:
            curve_df = pd.read_csv(resilience_curve_path)
            if "attack_ratio" in curve_df.columns:
                has_zero = (curve_df["attack_ratio"] == 0).any()
                result["consistency_checks"]["curve_has_zero"] = has_zero
                if not has_zero and strict:
                    result["pass"] = False
                    result["warnings"].append("resilience_curve.csv 中缺少 attack_ratio=0")
            else:
                result["warnings"].append("resilience_curve.csv 中缺少 attack_ratio 列")
        except Exception as e:
            result["warnings"].append(f"读取 resilience_curve.csv 失败: {str(e)}")
    
    return result


# ==================
# Stage F: Viz Output（绘图资产与打包交付）
# ==================
def audit_stage_f(root_dir: Path, strict: bool) -> Dict:
    """Stage F: Viz Output 审计"""
    result = {
        "pass": True,
        "missing_required": [],
        "warnings": [],
        "figures_check": {},
        "csv_checks": {},
        "zip_check": {}
    }
    
    viz_dir = root_dir / "outputs" / "task2" / "viz"
    figures_dir = viz_dir / "figures"
    
    # 1. 检查必需文件
    required_files = {
        "viz_script": root_dir / "scripts" / "viz_task2.py",
        "readme": viz_dir / "README_for_artist.md",
        "solution_flows": viz_dir / "solution_flows.csv",
        "solution_routes_summary": viz_dir / "solution_routes_summary.csv",
        "figures_dir": figures_dir
    }
    
    for name, path in required_files.items():
        if not path.exists():
            result["missing_required"].append(name)
            if strict:
                result["pass"] = False
    
    # 2. 获取 run_id（从 best_solution.json 读取）
    best_solution_path = root_dir / "outputs" / "task2" / "best_solution.json"
    run_id = None
    zip_required = None
    
    if best_solution_path.exists():
        try:
            with open(best_solution_path, 'r', encoding='utf-8') as f:
                best_solution = json.load(f)
            run_id = best_solution.get("run_id")
            if run_id:
                zip_required = viz_dir / f"plot_pack_{run_id}.zip"
                if not zip_required.exists():
                    result["missing_required"].append(f"plot_pack_{run_id}.zip")
                    if strict:
                        result["pass"] = False
        except Exception as e:
            result["warnings"].append(f"读取 best_solution.json 失败: {str(e)}")
    
    # 3. 图数量验收（strict）
    if figures_dir.exists():
        pdf_files = list(figures_dir.glob("*.pdf"))
        png_files = list(figures_dir.glob("*.png"))
        
        pdf_count = len(pdf_files)
        png_count = len(png_files)
        
        # 检查同名配对
        pdf_names = {f.stem for f in pdf_files}
        png_names = {f.stem for f in png_files}
        paired_names = pdf_names & png_names
        
        result["figures_check"] = {
            "pdf_count": pdf_count,
            "png_count": png_count,
            "paired_count": len(paired_names),
            "unpaired_pdf": list(pdf_names - png_names),
            "unpaired_png": list(png_names - pdf_names)
        }
        
        # strict 模式要求至少 5 张图，且每张必须有 pdf 和 png
        if strict:
            if pdf_count < 5 or png_count < 5:
                result["warnings"].append(f"图数量不足：pdf={pdf_count}, png={png_count}，要求至少 5 张")
                result["pass"] = False
            
            if len(paired_names) < 5:
                result["warnings"].append(f"配对图数量不足：{len(paired_names)}，要求至少 5 对")
                result["pass"] = False
            
            if pdf_names != png_names:
                result["warnings"].append(f"PDF 和 PNG 文件名不匹配：unpaired_pdf={result['figures_check']['unpaired_pdf']}, unpaired_png={result['figures_check']['unpaired_png']}")
                result["pass"] = False
    
    # 4. CSV 列头严格校验（strict）
    solution_flows_path = viz_dir / "solution_flows.csv"
    solution_routes_summary_path = viz_dir / "solution_routes_summary.csv"
    
    # solution_flows.csv 列名顺序
    expected_flows_columns = ["run_id", "route_id", "segment_idx", "source_node_id", "target_node_id", 
                               "source_lon", "source_lat", "target_lon", "target_lat", "value"]
    
    if solution_flows_path.exists():
        try:
            df_flows = pd.read_csv(solution_flows_path, nrows=0)
            actual_columns = list(df_flows.columns)
            
            if actual_columns != expected_flows_columns:
                result["csv_checks"]["solution_flows"] = {
                    "pass": False,
                    "expected": expected_flows_columns,
                    "actual": actual_columns
                }
                if strict:
                    result["pass"] = False
                    result["warnings"].append(f"solution_flows.csv 列名顺序不匹配：期望 {expected_flows_columns}，实际 {actual_columns}")
            else:
                result["csv_checks"]["solution_flows"] = {"pass": True}
        except Exception as e:
            result["warnings"].append(f"读取 solution_flows.csv 失败: {str(e)}")
    
    # solution_routes_summary.csv 列名顺序
    expected_routes_columns = ["run_id", "route_id", "description", "n_segments", "total_cost",
                               "mode_counts_json", "mode_costs_json", "min_seg_cost", "max_seg_cost", "mean_seg_cost"]
    
    if solution_routes_summary_path.exists():
        try:
            df_routes = pd.read_csv(solution_routes_summary_path, nrows=0)
            actual_columns = list(df_routes.columns)
            
            if actual_columns != expected_routes_columns:
                result["csv_checks"]["solution_routes_summary"] = {
                    "pass": False,
                    "expected": expected_routes_columns,
                    "actual": actual_columns
                }
                if strict:
                    result["pass"] = False
                    result["warnings"].append(f"solution_routes_summary.csv 列名顺序不匹配：期望 {expected_routes_columns}，实际 {actual_columns}")
            else:
                result["csv_checks"]["solution_routes_summary"] = {"pass": True}
        except Exception as e:
            result["warnings"].append(f"读取 solution_routes_summary.csv 失败: {str(e)}")
    
    # 5. Zip 内容验收（strict）
    if zip_required and zip_required.exists():
        try:
            with zipfile.ZipFile(zip_required, 'r') as z:
                zip_files = [f.filename for f in z.filelist]
            
            required_in_zip = {
                "solution_flows.csv",
                "solution_routes_summary.csv",
                "metrics.csv",
                "runtime.csv",
                "convergence_history.csv",
                "resilience_curve.csv",
                "best_solution.json",
                "README_for_artist.md"
            }
            
            # 检查是否有 figures/*.pdf 和 figures/*.png（至少一个）
            has_pdf_in_figures = any(f.startswith("figures/") and f.endswith(".pdf") for f in zip_files)
            has_png_in_figures = any(f.startswith("figures/") and f.endswith(".png") for f in zip_files)
            
            missing_in_zip = []
            for req in required_in_zip:
                if req not in zip_files:
                    missing_in_zip.append(req)
            
            if not has_pdf_in_figures:
                missing_in_zip.append("figures/*.pdf")
            if not has_png_in_figures:
                missing_in_zip.append("figures/*.png")
            
            result["zip_check"] = {
                "zip_files": zip_files,
                "missing": missing_in_zip
            }
            
            if missing_in_zip and strict:
                result["pass"] = False
                result["warnings"].append(f"Zip 文件缺少必需内容: {missing_in_zip}")
        except Exception as e:
            result["warnings"].append(f"读取 zip 文件失败: {str(e)}")
    
    return result


# ==================
# Stage G: Repro（最小复现链条）
# ==================
def audit_stage_g(root_dir: Path, strict: bool) -> Dict:
    """Stage G: Repro 审计"""
    result = {
        "pass": True,
        "repro_method": None,
        "missing_required": [],
        "warnings": [],
        "repro_commands": []
    }
    
    # 1. 检查 README 或 docs/ 中的复现命令块
    readme_paths = [
        root_dir / "README.md",
        root_dir / "docs" / "README.md"
    ]
    
    repro_pattern = re.compile(r'python\s+scripts/data_clean\.py.*?(?:\n|$)')
    
    for readme_path in readme_paths:
        if readme_path.exists():
            try:
                with open(readme_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                if repro_pattern.search(content):
                    result["repro_method"] = f"README command block in {readme_path.relative_to(root_dir)}"
                    result["pass"] = True
                    # 提取命令
                    matches = repro_pattern.findall(content)
                    result["repro_commands"] = [m.strip() for m in matches[:10]]
                    return result
            except Exception:
                pass
    
    # 2. 检查 scripts/reproduce_task2.(sh|ps1|bat)
    repro_scripts = [
        root_dir / "scripts" / "reproduce_task2.sh",
        root_dir / "scripts" / "reproduce_task2.ps1",
        root_dir / "scripts" / "reproduce_task2.bat"
    ]
    
    for script_path in repro_scripts:
        if script_path.exists():
            try:
                with open(script_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()[:40]
                result["repro_method"] = f"Script: {script_path.relative_to(root_dir)}"
                result["repro_commands"] = [line.rstrip() for line in lines if line.strip()][:40]
                result["pass"] = True
                return result
            except Exception:
                pass
    
    # 3. 检查 Makefile
    makefile_path = root_dir / "Makefile"
    if makefile_path.exists():
        try:
            with open(makefile_path, 'r', encoding='utf-8') as f:
                content = f.read()
            if re.search(r'reproduce|audit', content, re.IGNORECASE):
                result["repro_method"] = "Makefile target"
                result["pass"] = True
                return result
        except Exception:
            pass
    
    # 如果都不存在
    if strict:
        result["pass"] = False
        result["missing_required"].append("Repro method (README command block, reproduce_task2 script, or Makefile target)")
        result["warnings"].append("建议新增 reproduce_task2.ps1 的最小命令序列")
    
    # 设置最小复现命令序列
    result["repro_commands"] = [
        "python scripts/data_clean.py",
        "python scripts/data_loader.py",
        "python scripts/run_hybrid_pso_ga_task2.py",
        "python scripts/run_resilience_task2.py",
        "python scripts/viz_task2.py",
        "python scripts/project_audit.py --strict"
    ]
    
    return result


# ==================
# 报告生成
# ==================
def generate_report(stage_a: Dict, stage_b: Dict, stage_c: Dict, stage_d: Dict, stage_e: Dict, stage_f: Dict, stage_g: Dict, forbidden_grep: Dict, root_dir: Path, strict: bool, run_smoke: bool) -> str:
    """生成 audit_report.md"""
    lines = []
    
    # 计算 overall_pass
    all_pass = (stage_a["pass"] and stage_b["pass"] and forbidden_grep["pass"] and 
                stage_c["pass"] and stage_d["pass"] and stage_e["pass"] and
                stage_f["pass"] and stage_g["pass"])
    
    lines.append("# Audit Report")
    lines.append("")
    lines.append(f"**Overall Status:** {'✅ PASS' if all_pass else '❌ FAIL'}")
    lines.append(f"**Timestamp:** {datetime.now().isoformat()}")
    lines.append(f"**Repo Root:** {root_dir}")
    lines.append(f"**Strict Mode:** {strict}")
    lines.append(f"**Run Smoke:** {run_smoke}")
    lines.append("")
    lines.append("## Stage Summary")
    lines.append("")
    lines.append(f"- Stage A (ETL): {'✅ PASS' if stage_a['pass'] else '❌ FAIL'}")
    lines.append(f"- Stage B (Baseline): {'✅ PASS' if stage_b['pass'] else '❌ FAIL'}")
    lines.append(f"- Forbidden Grep: {'✅ PASS' if forbidden_grep['pass'] else '❌ FAIL'} ({len(forbidden_grep['matches'])} matches)")
    lines.append(f"- Stage C (Engine): {'✅ PASS' if stage_c['pass'] else '❌ FAIL'}")
    lines.append(f"- Stage D (Experiment Logging): {'✅ PASS' if stage_d['pass'] else '❌ FAIL'}")
    lines.append(f"- Stage E (Robustness): {'✅ PASS' if stage_e['pass'] else '❌ FAIL'}")
    lines.append(f"- Stage F (Viz Output): {'✅ PASS' if stage_f['pass'] else '❌ FAIL'}")
    lines.append(f"- Stage G (Repro): {'✅ PASS' if stage_g['pass'] else '❌ FAIL'}")
    lines.append("")
    
    # 如果有失败，添加缺失工件清单
    if not all_pass:
        lines.append("## Missing Artifacts")
        lines.append("")
        missing_list = []
        if stage_a["missing_required"]:
            missing_list.extend([f"Stage A: {m}" for m in stage_a["missing_required"]])
        if stage_b.get("missing_required"):
            missing_list.extend([f"Stage B: {m}" for m in stage_b.get("missing_required", [])])
        if stage_c["missing_required"]:
            missing_list.extend([f"Stage C: {m}" for m in stage_c["missing_required"]])
        if stage_d["missing_required"]:
            missing_list.extend([f"Stage D: {m}" for m in stage_d["missing_required"]])
        if stage_e["missing_required"]:
            missing_list.extend([f"Stage E: {m}" for m in stage_e["missing_required"]])
        if stage_f["missing_required"]:
            missing_list.extend([f"Stage F: {m}" for m in stage_f["missing_required"]])
        if stage_g["missing_required"]:
            missing_list.extend([f"Stage G: {m}" for m in stage_g["missing_required"]])
        
        for missing in missing_list:
            lines.append(f"- {missing}")
        
        lines.append("")
        lines.append("## Fix Commands")
        lines.append("")
        lines.append("```bash")
        for cmd in stage_g.get("repro_commands", []):
            lines.append(cmd)
        lines.append("```")
        lines.append("")
    
    # Stage A
    lines.append("## Stage A: Data ETL")
    lines.append("")
    
    if stage_a["pass"]:
        lines.append("**Status:** ✅ PASS")
    else:
        lines.append("**Status:** ❌ FAIL")
    
    lines.append("")
    lines.append("### Required Files")
    lines.append("")
    for name, info in stage_a["required_files"].items():
        status = "✅" if info["exists"] else "❌"
        lines.append(f"- {status} `{info['path']}`")
        if info["exists"]:
            if name in stage_a["schema_checks"]:
                check = stage_a["schema_checks"][name]
                lines.append(f"  - Rows: {check['n_rows']:,}")
                lines.append(f"  - Columns ({len(check['cols'])}): {', '.join(check['cols'][:10])}")
                if check.get("missing_cols"):
                    lines.append(f"  - ⚠️ Missing columns: {', '.join(check['missing_cols'])}")
    
    lines.append("")
    lines.append("### Optional Files")
    lines.append("")
    for name, info in stage_a["optional_files"].items():
        status = "✅ FOUND" if info["exists"] else "⚠️ WARNING (not found)"
        lines.append(f"- {status} `{info['path']}`")
        if info["exists"] and name in stage_a["schema_checks"]:
            check = stage_a["schema_checks"][name]
            lines.append(f"  - Rows: {check['n_rows']:,}")
            lines.append(f"  - Columns ({len(check['cols'])}): {', '.join(check['cols'][:10])}")
            if check.get("missing_cols"):
                lines.append(f"  - ⚠️ Missing columns: {', '.join(check['missing_cols'])}")
    
    # Stage B
    lines.append("")
    lines.append("## Stage B: Baseline & Sanity")
    lines.append("")
    
    if stage_b["pass"]:
        lines.append("**Status:** ✅ PASS")
    else:
        lines.append("**Status:** ❌ FAIL")
    
    lines.append("")
    if stage_b["baseline_script_found"]:
        lines.append(f"✅ Baseline script found: `{stage_b['baseline_script_path']}`")
    else:
        lines.append("❌ Baseline script not found")
        lines.append("")
        lines.append("**建议补齐 baseline_analysis.py：连通性抽样+中心性top10输出**")
    
    if stage_b["baseline_output_dir_exists"]:
        lines.append("")
        lines.append(f"✅ Baseline output directory exists: `outputs/baseline/`")
        if stage_b["baseline_output_files"]:
            lines.append(f"  - Files ({len(stage_b['baseline_output_files'])}): {', '.join(stage_b['baseline_output_files'][:10])}")
    
    # Smoke test 结果
    if run_smoke and stage_b.get("smoke_test"):
        lines.append("")
        lines.append("### Smoke Test Results")
        lines.append("")
        smoke = stage_b["smoke_test"]
        
        if "error" in smoke:
            lines.append(f"❌ Error: {smoke['error']}")
        else:
            lines.append(f"- Nodes: {smoke.get('n_nodes', 0):,}")
            lines.append(f"- Edges: {smoke.get('n_edges', 0):,}")
            lines.append(f"- OD Pairs: {smoke.get('total_pairs', 0)}")
            lines.append(f"- Reachable: {smoke.get('reachable_count', 0)} ({smoke.get('reachable_ratio', 0)*100:.1f}%)")
            
            cost_stats = smoke.get("cost_stats", {})
            lines.append("")
            lines.append("Cost Statistics:")
            lines.append(f"  - Min: {cost_stats.get('min', 0):.4f}")
            lines.append(f"  - Median: {cost_stats.get('median', 0):.4f}")
            lines.append(f"  - P95: {cost_stats.get('p95', 0):.4f}")
            lines.append(f"  - Max: {cost_stats.get('max', 0):.4f}")
            lines.append(f"  - Mean: {cost_stats.get('mean', 0):.4f}")
            
            if smoke.get("warnings"):
                lines.append("")
                lines.append("⚠️ Warnings:")
                for warning in smoke["warnings"]:
                    lines.append(f"  - {warning}")
    
    # Stage F: Viz Output
    lines.append("")
    lines.append("## Stage F: Viz Output")
    lines.append("")
    
    if stage_f["pass"]:
        lines.append("**Status:** ✅ PASS")
    else:
        lines.append("**Status:** ❌ FAIL")
    
    lines.append("")
    if stage_f["missing_required"]:
        lines.append("### Missing Required Files")
        for name in stage_f["missing_required"]:
            lines.append(f"- ❌ `{name}`")
    
    if stage_f.get("figures_check"):
        fig_check = stage_f["figures_check"]
        lines.append("")
        lines.append("### Figures Check")
        lines.append(f"- PDF files: {fig_check.get('pdf_count', 0)}")
        lines.append(f"- PNG files: {fig_check.get('png_count', 0)}")
        lines.append(f"- Paired count: {fig_check.get('paired_count', 0)}")
        if fig_check.get("unpaired_pdf") or fig_check.get("unpaired_png"):
            lines.append(f"- ⚠️ Unpaired PDF: {fig_check.get('unpaired_pdf', [])}")
            lines.append(f"- ⚠️ Unpaired PNG: {fig_check.get('unpaired_png', [])}")
    
    if stage_f.get("csv_checks"):
        csv_checks = stage_f["csv_checks"]
        lines.append("")
        lines.append("### CSV Column Headers")
        for csv_name, check in csv_checks.items():
            if check.get("pass"):
                lines.append(f"- ✅ `{csv_name}`: headers match")
            else:
                lines.append(f"- ❌ `{csv_name}`: headers mismatch")
                lines.append(f"  - Expected: {check.get('expected', [])}")
                lines.append(f"  - Actual: {check.get('actual', [])}")
    
    if stage_f.get("zip_check"):
        zip_check = stage_f["zip_check"]
        lines.append("")
        lines.append("### Zip Content Check")
        if zip_check.get("missing"):
            lines.append(f"- ❌ Missing in zip: {zip_check['missing']}")
        else:
            lines.append("- ✅ All required files in zip")
    
    if stage_f["warnings"]:
        lines.append("")
        lines.append("### Warnings")
        for warning in stage_f["warnings"]:
            lines.append(f"- ⚠️ {warning}")
    
    # Stage G: Repro
    lines.append("")
    lines.append("## Stage G: Repro（最小复现链条）")
    lines.append("")
    
    if stage_g["pass"]:
        lines.append("**Status:** ✅ PASS")
    else:
        lines.append("**Status:** ❌ FAIL")
    
    lines.append("")
    if stage_g.get("repro_method"):
        lines.append(f"**Repro Method:** {stage_g['repro_method']}")
    else:
        lines.append("**Repro Method:** ❌ Not found")
        lines.append("")
        lines.append("**建议新增 reproduce_task2.ps1 的最小命令序列**")
    
    if stage_g["warnings"]:
        lines.append("")
        lines.append("### Warnings")
        for warning in stage_g["warnings"]:
            lines.append(f"- ⚠️ {warning}")
    
    # 最小复现命令序列
    lines.append("")
    lines.append("## 最小复现命令序列")
    lines.append("")
    lines.append("```bash")
    for cmd in stage_g.get("repro_commands", []):
        lines.append(cmd)
    lines.append("```")
    
    # Next Actions
    lines.append("")
    lines.append("## Next Actions")
    lines.append("")
    
    has_issues = (not stage_a["pass"] or not stage_b["pass"] or not forbidden_grep["pass"] or
                  not stage_c["pass"] or not stage_d["pass"] or not stage_e["pass"] or
                  not stage_f["pass"] or not stage_g["pass"])
    
    if has_issues:
        all_missing = []
        if stage_a["missing_required"]:
            all_missing.extend([f"Stage A: {m}" for m in stage_a["missing_required"]])
        if stage_b.get("missing_required"):
            all_missing.extend([f"Stage B: {m}" for m in stage_b.get("missing_required", [])])
        if stage_c["missing_required"]:
            all_missing.extend([f"Stage C: {m}" for m in stage_c["missing_required"]])
        if stage_d["missing_required"]:
            all_missing.extend([f"Stage D: {m}" for m in stage_d["missing_required"]])
        if stage_e["missing_required"]:
            all_missing.extend([f"Stage E: {m}" for m in stage_e["missing_required"]])
        if stage_f["missing_required"]:
            all_missing.extend([f"Stage F: {m}" for m in stage_f["missing_required"]])
        if stage_g["missing_required"]:
            all_missing.extend([f"Stage G: {m}" for m in stage_g["missing_required"]])
        
        if all_missing:
            lines.append("### Missing Artifacts")
            for missing in all_missing:
                lines.append(f"- {missing}")
    else:
        lines.append("✅ All checks passed. No action needed.")
    
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("**Reproduce Smoke Test:**")
    lines.append("```bash")
    lines.append("python scripts/project_audit.py --strict --run-smoke")
    lines.append("```")
    
    return "\n".join(lines)


def generate_summary(stage_a: Dict, stage_b: Dict, stage_c: Dict, stage_d: Dict, stage_e: Dict, stage_f: Dict, stage_g: Dict, forbidden_grep: Dict) -> Dict:
    """生成 audit_summary.json"""
    summary = {
        "timestamp": datetime.now().isoformat(),
        "stage_a": {
            "pass": stage_a["pass"],
            "missing_required": len(stage_a["missing_required"]) > 0,
            "missing_optional": len([f for f in stage_a["optional_files"].values() if not f["exists"]]) > 0,
            "warnings": stage_a["warnings"]
        },
        "stage_b": {
            "pass": stage_b["pass"],
            "baseline_script_found": stage_b["baseline_script_found"]
        },
        "forbidden_grep": {
            "pass": forbidden_grep["pass"],
            "match_count": len(forbidden_grep["matches"])
        },
        "stage_c": {
            "pass": stage_c["pass"],
            "missing_required": len(stage_c["missing_required"]) > 0,
            "candidates_valid": stage_c.get("candidates_validation", {}).get("error") is None,
            "warnings": stage_c["warnings"]
        },
        "stage_d": {
            "pass": stage_d["pass"],
            "missing_required": len(stage_d["missing_required"]) > 0,
            "warnings": stage_d["warnings"]
        },
        "stage_e": {
            "pass": stage_e["pass"],
            "missing_required": len(stage_e["missing_required"]) > 0,
            "warnings": stage_e["warnings"]
        },
        "stage_f": {
            "pass": stage_f["pass"],
            "missing_required": len(stage_f["missing_required"]) > 0,
            "warnings": stage_f["warnings"]
        },
        "stage_g": {
            "pass": stage_g["pass"],
            "missing_required": len(stage_g["missing_required"]) > 0,
            "warnings": stage_g["warnings"],
            "repro_method": stage_g.get("repro_method")
        },
        "overall_pass": (
            stage_a["pass"] and stage_b["pass"] and forbidden_grep["pass"] and
            stage_c["pass"] and stage_d["pass"] and stage_e["pass"] and
            stage_f["pass"] and stage_g["pass"]
        )
    }
    return summary


# ==================
# 主函数
# ==================
def main():
    parser = argparse.ArgumentParser(description="工程审计器 - Stage A/B/C/D/E/F/G")
    parser.add_argument("--strict", action="store_true", help="严格模式（缺失必需文件会FAIL）")
    parser.add_argument("--run-smoke", action="store_true", help="运行 smoke test")
    
    args = parser.parse_args()
    
    # 创建输出目录
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # 运行审计
    print("=" * 80)
    print("工程审计器 - Stage A/B/C/D/E/F/G")
    print("=" * 80)
    print(f"\nRepo Root: {ROOT_DIR}")
    print(f"Strict Mode: {args.strict}")
    print(f"Run Smoke: {args.run_smoke}")
    print()
    
    print("[Stage A] Data ETL 审计...")
    stage_a = audit_stage_a(ROOT_DIR, args.strict)
    
    print("[Stage B] Baseline & Sanity 审计...")
    stage_b = audit_stage_b(ROOT_DIR, args.strict, args.run_smoke)
    
    print("[Forbidden Grep] 检查 graph_with_cost (forbidden pattern)...")
    forbidden_grep = forbidden_grep_check(ROOT_DIR, "graph_with_cost")
    
    print("[Stage C] Engine 审计...")
    stage_c = audit_stage_c(ROOT_DIR, args.strict)
    
    print("[Stage D] Experiment Logging 审计...")
    stage_d = audit_stage_d(ROOT_DIR, args.strict)
    
    print("[Stage E] Robustness 审计...")
    stage_e = audit_stage_e(ROOT_DIR, args.strict)
    
    print("[Stage F] Viz Output 审计...")
    stage_f = audit_stage_f(ROOT_DIR, args.strict)
    
    print("[Stage G] Repro 审计...")
    stage_g = audit_stage_g(ROOT_DIR, args.strict)
    
    # 生成报告
    print("\n生成报告...")
    report_content = generate_report(stage_a, stage_b, stage_c, stage_d, stage_e, stage_f, stage_g, forbidden_grep, ROOT_DIR, args.strict, args.run_smoke)
    summary = generate_summary(stage_a, stage_b, stage_c, stage_d, stage_e, stage_f, stage_g, forbidden_grep)
    
    # 生成目录树
    focus_paths = [
        ROOT_DIR / "data" / "processed",
        ROOT_DIR / "outputs",
        ROOT_DIR / "scripts"
    ]
    tree_content = list_tree(ROOT_DIR, focus_paths)
    
    # 写入文件
    report_path = OUTPUT_DIR / "audit_report.md"
    summary_path = OUTPUT_DIR / "audit_summary.json"
    tree_path = OUTPUT_DIR / "audit_tree.txt"
    
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report_content)
    
    with open(summary_path, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    
    with open(tree_path, 'w', encoding='utf-8') as f:
        f.write(tree_content)
    
    print(f"\n✅ 报告已生成:")
    print(f"  - {report_path}")
    print(f"  - {summary_path}")
    print(f"  - {tree_path}")
    
    # 打印摘要
    print("\n" + "=" * 80)
    print("审计摘要")
    print("=" * 80)
    print(f"\nStage A (ETL): {'✅ PASS' if stage_a['pass'] else '❌ FAIL'}")
    print(f"Stage B (Baseline): {'✅ PASS' if stage_b['pass'] else '❌ FAIL'}")
    print(f"Forbidden Grep: {'✅ PASS' if forbidden_grep['pass'] else '❌ FAIL'} ({len(forbidden_grep['matches'])} matches)")
    print(f"Stage C (Engine): {'✅ PASS' if stage_c['pass'] else '❌ FAIL'}")
    print(f"Stage D (Experiment Logging): {'✅ PASS' if stage_d['pass'] else '❌ FAIL'}")
    print(f"Stage E (Robustness): {'✅ PASS' if stage_e['pass'] else '❌ FAIL'}")
    
    all_pass = stage_a["pass"] and stage_b["pass"] and forbidden_grep["pass"] and stage_c["pass"] and stage_d["pass"] and stage_e["pass"]
    
    if not all_pass:
        print("\n❌ 审计失败（strict 模式）")
        sys.exit(1)
    else:
        print("\n✅ 所有检查通过")
        sys.exit(0)


if __name__ == "__main__":
    main()
