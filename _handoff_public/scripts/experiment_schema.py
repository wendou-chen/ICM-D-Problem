"""
experiment_schema.py
实验记录 Schema 定义与 Fail-fast 验证工具

提供：
- METRICS_SCHEMA / RUNTIME_SCHEMA 常量
- validate_schema_row: 严格字段校验
- ensure_csv_header: CSV header 一致性检查
- append_csv_row: 安全追加 CSV 行
- generate_schema_docs: 生成 schema 说明文档
"""

import csv
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
import math

# ===============================
# SCHEMA 定义（严格字段顺序）
# ===============================

METRICS_SCHEMA: List[str] = [
    "run_id", "timestamp", "graph_path", "candidates_path",
    "seed", "K", "od_seed", "od_policy",
    "budget", "lambda_reg", "unreachable_penalty",
    "pso_particles", "pso_iter", "ga_pop", "ga_gen",
    "best_total_obj", "best_reachable_ratio", "best_mean_cost_reachable",
    "best_reachable_count", "best_unreachable_count",
    "best_penalty_term", "best_regularization_term",
    "n_selected", "selected_ids"
]

RUNTIME_SCHEMA: List[str] = [
    "run_id", "total_sec", "pso_sec", "ga_sec", "n_eval", "avg_eval_sec"
]

CONVERGENCE_HISTORY_SCHEMA: List[str] = [
    "run_id", "phase", "iter",
    "best_total_obj", "best_reachable_ratio", "best_mean_cost_reachable",
    "best_reachable_count", "best_unreachable_count",
    "best_penalty_term", "best_regularization_term"
]

RESILIENCE_TABLE_SCHEMA: List[str] = [
    "solution_run_id", "timestamp", "graph_path", "candidates_path",
    "seed", "od_seed", "K", "od_policy",
    "attack_target", "strategy", "attack_ratio", "trial",
    "best_total_obj", "best_reachable_ratio", "best_mean_cost_reachable",
    "best_reachable_count", "best_unreachable_count",
    "best_penalty_term", "best_regularization_term"
]

RESILIENCE_CURVE_SCHEMA: List[str] = [
    "attack_target", "strategy", "attack_ratio",
    "best_total_obj_mean", "best_total_obj_std",
    "best_reachable_ratio_mean", "best_reachable_ratio_std",
    "best_mean_cost_reachable_mean", "best_mean_cost_reachable_std",
    "best_unreachable_count_mean", "best_unreachable_count_std"
]

# 允许为空的字段（仅当 reachable_count == 0 时）
NULLABLE_FIELDS: Set[str] = {
    "best_mean_cost_reachable",
    "best_mean_cost_reachable_mean",
    "best_mean_cost_reachable_std"
}


# ===============================
# 验证工具函数
# ===============================
# ... (validate_schema_row, ensure_csv_header, append_csv_row omitted - kept as is) ...
# To save space, we assume the previous content is here. 
# But since I'm using "ReplacementContent" with specific range, I don't need to repeat functions unless modifying them.
# I will supply the variables above and keep functions.



# ===============================
# 验证工具函数
# ===============================

def validate_schema_row(row: Dict[str, Any], schema: List[str], *, strict: bool = True) -> None:
    """
    严格验证 row 是否符合 schema。
    
    Args:
        row: 待验证的字典
        schema: 期望的字段列表
        strict: 是否严格模式（默认 True）
    
    Raises:
        KeyError: 缺失字段或多余字段
        ValueError: 字段值为 None/NaN 且不允许为空
    """
    row_keys = set(row.keys())
    schema_keys = set(schema)
    
    # 检查缺失字段
    missing = schema_keys - row_keys
    if missing:
        raise KeyError(f"Schema validation failed: missing fields {sorted(missing)}")
    
    # 检查多余字段
    if strict:
        extra = row_keys - schema_keys
        if extra:
            raise KeyError(f"Schema validation failed: extra fields {sorted(extra)}")
    
    # 检查空值
    for field in schema:
        val = row.get(field)
        is_null = val is None or (isinstance(val, float) and math.isnan(val))
        
        if is_null and field not in NULLABLE_FIELDS:
            raise ValueError(f"Schema validation failed: field '{field}' is null but not nullable")


def ensure_csv_header(path: Path, schema: List[str]) -> None:
    """
    确保 CSV 文件存在且 header 与 schema 一致。
    
    Args:
        path: CSV 文件路径
        schema: 期望的字段列表
    
    Raises:
        ValueError: header 不匹配
    """
    path = Path(path)
    
    if not path.exists():
        # 创建文件并写入 header
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(schema)
        return
    
    # 读取现有 header
    with open(path, 'r', newline='', encoding='utf-8') as f:
        reader = csv.reader(f)
        try:
            existing_header = next(reader)
        except StopIteration:
            # 文件为空，写入 header
            with open(path, 'w', newline='', encoding='utf-8') as fw:
                writer = csv.writer(fw)
                writer.writerow(schema)
            return
    
    # 比较 header
    if existing_header != schema:
        raise ValueError(
            f"CSV header mismatch!\n"
            f"  Expected: {schema}\n"
            f"  Actual:   {existing_header}"
        )


def append_csv_row(path: Path, schema: List[str], row: Dict[str, Any]) -> None:
    """
    安全追加一行到 CSV 文件。
    
    Args:
        path: CSV 文件路径
        schema: 字段列表
        row: 数据字典
    
    Raises:
        KeyError/ValueError: 验证失败
    """
    # 1. 确保 header 存在且一致
    ensure_csv_header(path, schema)
    
    # 2. 验证 row
    validate_schema_row(row, schema, strict=True)
    
    # 3. 按 schema 顺序写入
    path = Path(path)
    with open(path, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([row[field] for field in schema])


# ===============================
# Schema 文档生成
# ===============================

METRICS_SCHEMA_DOC = """# metrics.csv Schema

| Field | Type | Nullable | Description | Example |
|-------|------|----------|-------------|---------|
| run_id | str | No | Unique run identifier | "20260109_190000_abc123" |
| timestamp | str | No | ISO format timestamp | "2026-01-09T19:00:00" |
| graph_path | str | No | Path to graph.pkl | "data/processed/graph.pkl" |
| candidates_path | str | No | Path to candidates JSON | "data/processed/candidates_task2.json" |
| seed | int | No | Main random seed | 42 |
| K | int | No | Number of OD pairs sampled | 30 |
| od_seed | int | No | Seed for OD sampling | 42 |
| od_policy | str | No | OD sampling policy | "random" |
| budget | float | No | Budget constraint | 100.0 |
| lambda_reg | float | No | Regularization coefficient | 0.1 |
| unreachable_penalty | float | No | Penalty for unreachable OD | 1000000.0 |
| pso_particles | int | No | PSO particle count | 10 |
| pso_iter | int | No | PSO iterations | 10 |
| ga_pop | int | No | GA population size | 20 |
| ga_gen | int | No | GA generations | 20 |
| best_total_obj | float | No | Final objective value | 1000000.5 |
| best_reachable_ratio | float | No | Ratio of reachable OD pairs | 0.9 |
| best_mean_cost_reachable | float | **Yes** (if reachable_count=0) | Mean cost of reachable OD | 5.2 |
| best_reachable_count | int | No | Number of reachable OD pairs | 27 |
| best_unreachable_count | int | No | Number of unreachable OD pairs | 3 |
| best_penalty_term | float | No | Penalty term in objective | 3000000.0 |
| best_regularization_term | float | No | Regularization term | 0.5 |
| n_selected | int | No | Number of selected routes | 5 |
| selected_ids | str | No | Selected route IDs (semicolon-separated) | "1;3;5;7;9" |
"""

RUNTIME_SCHEMA_DOC = """# runtime.csv Schema

| Field | Type | Nullable | Description | Example |
|-------|------|----------|-------------|---------|
| run_id | str | No | Unique run identifier | "20260109_190000_abc123" |
| total_sec | float | No | Total runtime in seconds | 125.5 |
| pso_sec | float | No | PSO phase runtime in seconds | 50.2 |
| ga_sec | float | No | GA phase runtime in seconds | 75.3 |
| n_eval | int | No | Total number of evaluations | 1000 |
| avg_eval_sec | float | No | Average time per evaluation | 0.125 |
"""

CONVERGENCE_HISTORY_DOC = """# convergence_history.csv Schema

| Field | Type | Nullable | Description |
|-------|------|----------|-------------|
| run_id | str | No | Task2 run ID |
| phase | str | No | "PSO" or "GA" |
| iter | int | No | Iteration number (0-indexed) |
| best_total_obj | float | No | Global best objective at this step |
| best_reachable_ratio | float | No | Detailed metric |
| best_mean_cost_reachable | float | **Yes** | Detailed metric |
| best_reachable_count | int | No | Detailed metric |
| best_unreachable_count | int | No | Detailed metric |
| best_penalty_term | float | No | Detailed metric |
| best_regularization_term | float | No | Detailed metric |
"""

RESILIENCE_SCHEMA_DOC = """# resilience_table.csv & resilience_curve.csv Schema

## resilience_table.csv (Raw Trials)

| Field | Type | Nullable | Description |
|-------|------|----------|-------------|
| solution_run_id | str | No | The Task2 run being tested |
| timestamp | str | No | Test execution time |
| graph_path | str | No | Source graph |
| candidates_path | str | No | Source candidates |
| seed | int | No | Original Task2 seed |
| od_seed | int | No | OD sampling seed (reused) |
| K | int | No | Number of OD pairs |
| od_policy | str | No | OD policy |
| attack_target | str | No | "node" or "edge" |
| strategy | str | No | "random" or "targeted" |
| attack_ratio | float | No | Fraction removed (0.0 - 1.0) |
| trial | int | No | Trial index (0 for targeted) |
| best_* | ... | ... | Metrics on damaged graph |

## resilience_curve.csv (Aggregated)

| Field | Type | Nullable | Description |
|-------|------|----------|-------------|
| attack_target | str | No | Grouping key |
| strategy | str | No | Grouping key |
| attack_ratio | float | No | Grouping key |
| *_mean | float | **Yes** | Mean of metrics over trials |
| *_std | float | **Yes** | Std deviation of metrics |
"""


def generate_schema_docs(output_dir: Path) -> None:
    """
    生成 schema 说明文档。
    
    Args:
        output_dir: 输出目录
    
    Raises:
        IOError: 写入失败
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        with open(output_dir / "metrics_schema.md", 'w', encoding='utf-8') as f:
            f.write(METRICS_SCHEMA_DOC)
        
        with open(output_dir / "runtime_schema.md", 'w', encoding='utf-8') as f:
            f.write(RUNTIME_SCHEMA_DOC)

        with open(output_dir / "convergence_schema.md", 'w', encoding='utf-8') as f:
            f.write(CONVERGENCE_HISTORY_DOC)

        with open(output_dir / "resilience_schema.md", 'w', encoding='utf-8') as f:
            f.write(RESILIENCE_SCHEMA_DOC)

    except Exception as e:
        raise IOError(f"Failed to generate schema docs: {e}")


def generate_run_id() -> str:
    """生成唯一的 run_id"""
    import uuid
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    short_uuid = uuid.uuid4().hex[:8]
    return f"{ts}_{short_uuid}"
