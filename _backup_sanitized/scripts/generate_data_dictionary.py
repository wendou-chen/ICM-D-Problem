"""
generate_data_dictionary.py
自动生成 data_dictionary.md（写作手交付物）

功能：
- 扫描 data/processed/ 下的工件文件
- 自动生成字段表和统计信息
- 输出到仓库根目录：data_dictionary.md
"""

import json
import sys
from collections import Counter
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd

ROOT_DIR = Path(__file__).parent.parent
PROCESSED_DIR = ROOT_DIR / "data" / "processed"
OUTPUT_PATH = ROOT_DIR / "data_dictionary.md"


# ==================
# 列名映射（保守解释）
# ==================
COLUMN_NOTES_MAP = {
    # 标识符
    "id": "节点/边的唯一标识符",
    "node_id": "节点唯一标识符",
    "original_id": "原始数据中的标识符",
    "osmid": "OpenStreetMap ID",
    "u": "边的起始节点（source node）",
    "v": "边的终止节点（target node）",
    "key": "边的键（用于 MultiGraph）",
    
    # 地理坐标
    "lat": "纬度（latitude）",
    "lon": "经度（longitude）",
    "latitude": "纬度",
    "longitude": "经度",
    "y": "纬度（Y 坐标）",
    "x": "经度（X 坐标）",
    "u_lat": "起始节点纬度",
    "u_lon": "起始节点经度",
    "v_lat": "终止节点纬度",
    "v_lon": "终止节点经度",
    
    # 类型和层级
    "type": "节点/边类型（如 intersection, bus_stop 等）",
    "layer": "图层类型（如 drive, walk, bus 等）",
    "mode": "交通模式（如 bus, walk, drive 等）",
    
    # 成本和权重
    "cost": "广义代价（generalized cost）",
    "weight": "边的权重",
    "distance": "距离（单位：米）",
    "length": "长度（单位：米）",
    
    # 道路属性
    "highway": "道路类型",
    "access": "访问权限",
    "lanes": "车道数",
    "maxspeed": "最高速度（单位：km/h）",
    "name": "道路名称",
    "oneway": "是否单行道",
    "ref": "道路编号",
    "reversed": "是否反向",
    "service": "服务类型",
    "junction": "路口类型",
    "bridge": "是否桥梁",
    "width": "宽度",
    "tunnel": "是否隧道",
    "area": "是否区域",
    "street_count": "街道数量",
    
    # 几何信息
    "geometry": "几何对象（WKT/GeoJSON）",
    "pos": "位置（经度，纬度）",
    
    # 公交相关
    "description": "路线描述",
    "transfer_type": "换乘类型",
    "capacity": "容量",
    
    # 其他
    "run_id": "运行标识符",
    "timestamp": "时间戳",
    "selected_ids": "选中的候选 ID 列表",
    "n_selected": "选中的数量",
    "best_total_obj": "最优总目标值",
    "best_reachable_ratio": "最优可达性比例",
    "best_mean_cost_reachable": "最优可达路径平均代价",
    "best_reachable_count": "最优可达数量",
    "best_unreachable_count": "最优不可达数量",
    "best_penalty_term": "最优惩罚项",
    "best_regularization_term": "最优正则化项",
}


def get_column_note(col_name: str) -> str:
    """根据列名获取保守解释"""
    col_lower = col_name.lower()
    
    # 直接匹配
    if col_lower in COLUMN_NOTES_MAP:
        return COLUMN_NOTES_MAP[col_lower]
    
    # 部分匹配
    if "lat" in col_lower or "latitude" in col_lower:
        return "纬度"
    if "lon" in col_lower or "longitude" in col_lower:
        return "经度"
    if "cost" in col_lower:
        return "代价"
    if "id" in col_lower:
        return "标识符"
    
    # 未知列
    return "(undocumented)"


def analyze_csv_file(csv_path: Path) -> Optional[Dict]:
    """分析 CSV 文件，返回字段表"""
    if not csv_path.exists():
        return None
    
    try:
        # 读取 CSV
        df = pd.read_csv(csv_path, low_memory=False)
        
        fields = []
        
        for col in df.columns:
            # dtype
            dtype_str = str(df[col].dtype)
            
            # missing_pct
            missing_count = df[col].isna().sum()
            total_count = len(df)
            missing_pct = (missing_count / total_count * 100) if total_count > 0 else 0.0
            missing_pct_str = f"{missing_pct:.2f}"
            
            # example（第一个非空值）
            example = None
            for val in df[col]:
                if pd.notna(val):
                    example = str(val)
                    if len(example) > 60:
                        example = example[:60] + "..."
                    break
            
            # notes
            notes = get_column_note(col)
            
            fields.append({
                "column": col,
                "dtype": dtype_str,
                "missing_pct": missing_pct_str,
                "example": example if example else "(all null)",
                "notes": notes
            })
        
        return {
            "exists": True,
            "n_rows": len(df),
            "n_cols": len(df.columns),
            "fields": fields
        }
        
    except Exception as e:
        return {
            "exists": True,
            "error": str(e)
        }


def analyze_candidates_json(json_path: Path) -> Optional[Dict]:
    """分析 candidates_task2.json 结构"""
    if not json_path.exists():
        return None
    
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            candidates = json.load(f)
        
        if not isinstance(candidates, list):
            return {
                "exists": True,
                "error": f"顶层不是 list，实际是 {type(candidates).__name__}"
            }
        
        # 统计信息
        n_candidates = len(candidates)
        
        edges_counts = []
        mode_counter = Counter()
        
        for candidate in candidates:
            if not isinstance(candidate, dict):
                continue
            
            # edges 数量
            edges = candidate.get("edges", [])
            if isinstance(edges, list):
                edges_counts.append(len(edges))
                
                # mode 分布
                for edge in edges:
                    if isinstance(edge, (list, tuple)) and len(edge) >= 3:
                        attrs = edge[2]
                        if isinstance(attrs, dict):
                            mode = attrs.get("mode")
                            if mode:
                                mode_counter[mode] += 1
        
        avg_edges = sum(edges_counts) / len(edges_counts) if edges_counts else 0.0
        
        # 分析第一个 candidate 的结构
        first_candidate = candidates[0] if candidates else {}
        first_structure = {
            "keys": list(first_candidate.keys()) if isinstance(first_candidate, dict) else [],
            "edges_structure": None
        }
        
        if isinstance(first_candidate, dict):
            edges = first_candidate.get("edges", [])
            if isinstance(edges, list) and len(edges) > 0:
                first_edge = edges[0]
                if isinstance(first_edge, (list, tuple)):
                    first_structure["edges_structure"] = {
                        "length": len(first_edge),
                        "u_type": type(first_edge[0]).__name__ if len(first_edge) > 0 else None,
                        "v_type": type(first_edge[1]).__name__ if len(first_edge) > 1 else None,
                        "attrs_type": type(first_edge[2]).__name__ if len(first_edge) > 2 else None,
                        "attrs_keys": list(first_edge[2].keys()) if len(first_edge) > 2 and isinstance(first_edge[2], dict) else []
                    }
        
        return {
            "exists": True,
            "structure": {
                "top_level": "list",
                "element_keys": first_structure["keys"],
                "edges_structure": first_structure["edges_structure"]
            },
            "stats": {
                "n_candidates": n_candidates,
                "avg_edges_per_candidate": f"{avg_edges:.2f}",
                "mode_distribution": dict(mode_counter)
            }
        }
        
    except json.JSONDecodeError as e:
        return {
            "exists": True,
            "error": f"JSON 解析错误: {str(e)}"
        }
    except Exception as e:
        return {
            "exists": True,
            "error": str(e)
        }


def generate_markdown() -> str:
    """生成 Markdown 文档"""
    lines = []
    
    # 标题
    lines.append("# Data Dictionary")
    lines.append("")
    lines.append("本文档自动生成，基于 `data/processed/` 下的真实工件文件。")
    lines.append("")
    lines.append(f"**生成时间：** {pd.Timestamp.now().isoformat()}")
    lines.append("")
    
    # Data Lineage
    lines.append("## Data Lineage（数据血缘）")
    lines.append("")
    lines.append("数据流转路径：")
    lines.append("")
    lines.append("```")
    lines.append("raw/ (原始数据)")
    lines.append("  ↓ data_clean.py")
    lines.append("*_clean.csv (清洗层：nodes_clean.csv, edges_clean.csv, bus_stops_clean.csv)")
    lines.append("  ↓ data_loader.py")
    lines.append("graph.pkl / base_map.csv / graph_nodes.csv / graph_edges_kepler.csv (图层导出)")
    lines.append("  ↓ Task2 处理")
    lines.append("candidates_task2.json / outputs/task2/ (实验输出)")
    lines.append("```")
    lines.append("")
    
    # 文件清单
    lines.append("## 文件清单")
    lines.append("")
    
    files_to_check = {
        "nodes_clean.csv": PROCESSED_DIR / "nodes_clean.csv",
        "edges_clean.csv": PROCESSED_DIR / "edges_clean.csv",
        "bus_stops_clean.csv": PROCESSED_DIR / "bus_stops_clean.csv",
        "base_map.csv": PROCESSED_DIR / "base_map.csv",
        "graph_nodes.csv": PROCESSED_DIR / "graph_nodes.csv",
        "graph_edges_kepler.csv": PROCESSED_DIR / "graph_edges_kepler.csv",
        "candidates_task2.json": PROCESSED_DIR / "candidates_task2.json"
    }
    
    file_status = {}
    
    for name, path in files_to_check.items():
        exists = path.exists()
        file_status[name] = exists
        status_mark = "✅" if exists else "❌ MISSING"
        lines.append(f"- {status_mark} `{name}`")
    
    lines.append("")
    
    # CSV 文件字段表
    csv_files = {
        "nodes_clean.csv": "节点清洗数据",
        "edges_clean.csv": "边清洗数据",
        "bus_stops_clean.csv": "公交站点清洗数据",
        "base_map.csv": "基础地图数据",
        "graph_nodes.csv": "图节点数据",
        "graph_edges_kepler.csv": "Kepler.gl 边数据"
    }
    
    for filename, description in csv_files.items():
        csv_path = PROCESSED_DIR / filename
        
        lines.append(f"## {filename}")
        lines.append("")
        
        if not csv_path.exists():
            lines.append(f"**状态：** ❌ MISSING")
            lines.append("")
            lines.append("文件不存在。")
            lines.append("")
            continue
        
        result = analyze_csv_file(csv_path)
        
        if result is None:
            lines.append("**状态：** ❌ 无法读取")
            lines.append("")
            continue
        
        if "error" in result:
            lines.append(f"**状态：** ❌ 错误: {result['error']}")
            lines.append("")
            continue
        
        lines.append(f"**描述：** {description}")
        lines.append("")
        lines.append(f"**行数：** {result['n_rows']:,}")
        lines.append(f"**列数：** {result['n_cols']}")
        lines.append("")
        lines.append("### 字段表")
        lines.append("")
        lines.append("| Column | Dtype | Missing % | Example | Notes |")
        lines.append("|--------|-------|-----------|---------|-------|")
        
        for field in result["fields"]:
            col = field["column"]
            dtype = field["dtype"]
            missing_pct = field["missing_pct"]
            example = field["example"].replace("|", "\\|") if field["example"] else "(all null)"
            notes = field["notes"]
            
            lines.append(f"| `{col}` | {dtype} | {missing_pct}% | {example} | {notes} |")
        
        lines.append("")
    
    # candidates_task2.json 结构分析
    lines.append("## candidates_task2.json")
    lines.append("")
    
    json_path = PROCESSED_DIR / "candidates_task2.json"
    
    if not json_path.exists():
        lines.append("**状态：** ❌ MISSING")
        lines.append("")
        lines.append("文件不存在。")
        lines.append("")
    else:
        result = analyze_candidates_json(json_path)
        
        if result is None:
            lines.append("**状态：** ❌ 无法读取")
            lines.append("")
        elif "error" in result:
            lines.append(f"**状态：** ❌ 错误: {result['error']}")
            lines.append("")
        else:
            lines.append("**描述：** Task2 候选路线数据")
            lines.append("")
            lines.append("### 数据结构")
            lines.append("")
            lines.append("```json")
            lines.append("{")
            lines.append('  "top_level": "list",')
            lines.append('  "element_structure": {')
            
            structure = result.get("structure", {})
            element_keys = structure.get("element_keys", [])
            edges_structure = structure.get("edges_structure", {})
            
            lines.append(f'    "keys": {json.dumps(element_keys, ensure_ascii=False)},')
            lines.append('    "edges": [')
            lines.append('      [u, v, {')
            if edges_structure:
                attrs_keys = edges_structure.get("attrs_keys", [])
                for key in attrs_keys:
                    lines.append(f'        "{key}": <value>,')
            else:
                lines.append('        "mode": <value>,')
                lines.append('        "cost": <value>,')
                lines.append('        "weight": <value>')
            lines.append('      }],')
            lines.append('      ...')
            lines.append('    ]')
            lines.append('  }')
            lines.append('}')
            lines.append("```")
            lines.append("")
            
            lines.append("**说明：**")
            lines.append("- 顶层是 list，每个元素代表一个候选路线")
            lines.append("- 每个元素包含：`id`（候选 ID）、`cost`（路线总代价）、`edges`（边列表）、`description`（描述）")
            lines.append("- `edges` 是三元组列表：`[u, v, attrs_dict]`，其中 `attrs_dict` 至少包含 `mode`、`cost`、`weight`")
            lines.append("")
            
            # 统计信息
            stats = result.get("stats", {})
            lines.append("### 统计信息")
            lines.append("")
            lines.append(f"- **候选数量：** {stats.get('n_candidates', 0):,}")
            lines.append(f"- **平均边数（每条候选）：** {stats.get('avg_edges_per_candidate', '0.00')}")
            lines.append("")
            
            mode_dist = stats.get("mode_distribution", {})
            if mode_dist:
                lines.append("**Mode 分布：**")
                lines.append("")
                for mode, count in sorted(mode_dist.items(), key=lambda x: x[1], reverse=True):
                    lines.append(f"- `{mode}`: {count:,}")
                lines.append("")
    
    return "\n".join(lines)


def main():
    """主函数"""
    print("=" * 80)
    print("生成 Data Dictionary")
    print("=" * 80)
    print(f"\n输入目录: {PROCESSED_DIR}")
    print(f"输出文件: {OUTPUT_PATH}")
    print()
    
    # 检查输入目录
    if not PROCESSED_DIR.exists():
        print(f"❌ 错误: 输入目录不存在: {PROCESSED_DIR}")
        sys.exit(1)
    
    # 生成 Markdown
    print("扫描文件并生成文档...")
    markdown_content = generate_markdown()
    
    # 写入文件
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        f.write(markdown_content)
    
    print(f"\n✅ 文档已生成: {OUTPUT_PATH}")
    print(f"   文件大小: {OUTPUT_PATH.stat().st_size:,} bytes")
    
    # 统计
    lines_count = len(markdown_content.splitlines())
    print(f"   行数: {lines_count}")
    
    print("\n" + "=" * 80)
    print("✅ 完成")
    print("=" * 80)


if __name__ == "__main__":
    main()
