"""
data_clean.py
数据清洗脚本 - 读取 raw CSV，执行严格清洗与类型规范，写入 data/processed/，并生成结构化日志。

输入 (默认):
    - data/raw/nodes_all.csv
    - data/raw/edges_all.csv
    - data/raw/Bus_Stops.csv

输出:
    - data/processed/nodes_clean.csv
    - data/processed/edges_clean.csv
    - data/processed/bus_stops_clean.csv
    - data/processed/cleaning_log.md (包含稳定统计口径)

用法:
    python scripts/data_clean.py [--outdir data/processed]
"""

import argparse
import os
import re
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd


# ==================
# 清洗规则参数 (全局常量)
# ==================
CONFIG = {
    # 空间筛选: bbox (quantile)
    "bbox_quantile_low": 0.001,
    "bbox_quantile_high": 0.999,
    
    # 空间筛选: bus stops 扩展 margin (度)
    "bbox_margin_deg": 0.02,
    
    # Edges 填充默认值
    "lanes_default": 1,
    "maxspeed_default_mph": 25,
    "length_upper_m": 200000,  # 200km 阈值
}


# ==================
# 辅助解析函数
# ==================
def parse_lanes(raw_val) -> int:
    """解析lanes: 提取数字列表取最大值, 失败返回-1"""
    if pd.isna(raw_val):
        return -1
    s = str(raw_val)
    # 匹配各类数字
    nums = re.findall(r"\d+", s)
    if not nums:
        return -1
    try:
        # 取max
        return max(map(int, nums))
    except:
        return -1

def parse_maxspeed(raw_val) -> float:
    """解析maxspeed: 提取数字列表取最大值, 失败返回-1.0"""
    if pd.isna(raw_val):
        return -1.0
    s = str(raw_val).lower()
    # 匹配浮点数或整数
    nums = re.findall(r"[-+]?\d*\.\d+|\d+", s)
    if not nums:
        return -1.0
    try:
        vals = list(map(float, nums))
        return max(vals)
    except:
        return -1.0

def parse_oneway(raw_val):
    """
    解析oneway: 
    True: yes, true, 1, t
    False: no, false, 0, f
    -1: "-1" (逆向单行) -> 这里记录为 "minus1" 类别，但在布尔转换时不做特殊支持，
        按原需求: "若值为 -1：仅记录为 True（不要在 data_clean 改边方向）"
        等下，需求说 "若值为 -1：仅记录为 True"。
        这意味着 oneway_clean 列依然是 bool 或 int? 
        通常 oneway 字段 True/False 表示是否单行。-1 表示逆向单行。
        如果需求说 "记录为 True"，那我们就返回 True, 并且在计数里记为 minus1。
    """
    if pd.isna(raw_val):
        return None
    s = str(raw_val).lower().strip()
    if s in ("yes", "true", "1", "t"):
        return True
    if s in ("no", "false", "0", "f"):
        return False
    if s == "-1":
        return -1 # 特殊标记
    return None


# ==================
# 核心清洗逻辑
# ==================

def check_required_cols(df, required, filename, buffer):
    missing = [c for c in required if c not in df.columns]
    if missing:
        msg = f"❌ Error: {filename} missing required columns: {missing}"
        print(msg)
        buffer.append(f"\n{msg}\n")
        raise ValueError(msg)

def clean_nodes(raw_path, out_path, stats_dict, buffer):
    """
    stats_dict: 用于回传 bbox 信息给 bus stops 清洗使用
    """
    buffer.append(f"\n## 1. Nodes Cleaning ({os.path.basename(raw_path)})")
    
    if not os.path.exists(raw_path):
        msg = f"❌ Error: Raw file not found: {raw_path}"
        print(msg)
        buffer.append(msg)
        raise FileNotFoundError(msg)
        
    df = pd.read_csv(raw_path, low_memory=False)
    
    # 统计项初始化
    st = {
        "N_raw": len(df),
        "N_clean": 0,
        "N_drop_missing_or_non_numeric_xy": 0,
        "N_drop_invalid_range_xy": 0,
        "N_drop_duplicate_osmid": 0,
        "N_drop_bbox_outlier": 0,
        "bbox_x_lo": 0.0, "bbox_x_hi": 0.0, "bbox_y_lo": 0.0, "bbox_y_hi": 0.0
    }
    
    # 0. 必填列检查
    check_required_cols(df, ["osmid", "x", "y"], "nodes_all.csv", buffer)
    
    # 1. 类型规范: x, y 转 float
    df["x"] = pd.to_numeric(df["x"], errors="coerce")
    df["y"] = pd.to_numeric(df["y"], errors="coerce")
    
    # 删除 NA
    before = len(df)
    df = df.dropna(subset=["x", "y"])
    st["N_drop_missing_or_non_numeric_xy"] = before - len(df)
    
    # 2. 坐标合法性 [-180, 180], [-90, 90]
    mask_valid = (df["x"] >= -180) & (df["x"] <= 180) & (df["y"] >= -90) & (df["y"] <= 90)
    invalid_count = (~mask_valid).sum()
    st["N_drop_invalid_range_xy"] = invalid_count
    df = df[mask_valid].copy()
    
    # 3. 去重
    before = len(df)
    df = df.drop_duplicates(subset=["osmid"], keep="first")
    st["N_drop_duplicate_osmid"] = before - len(df)
    
    if len(df) == 0:
        print("Warning: No valid nodes left after basic cleaning!")
        st["N_clean"] = 0
        return st
    
    # 4. 漂移点剔除 (Quantile BBox)
    x_lo = df["x"].quantile(CONFIG["bbox_quantile_low"])
    x_hi = df["x"].quantile(CONFIG["bbox_quantile_high"])
    y_lo = df["y"].quantile(CONFIG["bbox_quantile_low"])
    y_hi = df["y"].quantile(CONFIG["bbox_quantile_high"])
    
    st["bbox_x_lo"] = x_lo
    st["bbox_x_hi"] = x_hi
    st["bbox_y_lo"] = y_lo
    st["bbox_y_hi"] = y_hi
    
    # 记录 BBox 供 Bus Stops 使用
    stats_dict["bbox"] = (x_lo, x_hi, y_lo, y_hi)
    
    mask_bbox = (df["x"] >= x_lo) & (df["x"] <= x_hi) & (df["y"] >= y_lo) & (df["y"] <= y_hi)
    outlier_count = (~mask_bbox).sum()
    st["N_drop_bbox_outlier"] = outlier_count
    df = df[mask_bbox].copy()
    
    # Final save
    st["N_clean"] = len(df)
    df.to_csv(out_path, index=False)
    
    return st

def clean_edges(raw_path, out_path, buffer):
    buffer.append(f"\n## 2. Edges Cleaning ({os.path.basename(raw_path)})")
    
    if not os.path.exists(raw_path):
        msg = f"❌ Error: Raw file not found: {raw_path}"
        print(msg)
        buffer.append(msg)
        raise FileNotFoundError(msg)
        
    df = pd.read_csv(raw_path, low_memory=False)
    
    st = {
        "E_raw": len(df),
        "E_clean": 0,
        "E_drop_missing_uvk": 0,
        "E_drop_self_loop": 0,
        "E_drop_length_na": 0, # 如果 length 列不存在则为 0
        "E_drop_nonpositive_length": 0,
        "E_drop_too_long": 0,
        "E_drop_full_duplicate": 0,
        
        "E_lanes_parse_success": 0,
        "E_lanes_parse_fail": 0,
        "E_lanes_fill_default": 0,
        
        "E_maxspeed_parse_success": 0,
        "E_maxspeed_parse_fail": 0,
        "E_maxspeed_fill_default": 0,
        
        "E_oneway_true": 0,
        "E_oneway_false": 0,
        "E_oneway_minus1": 0,
        "E_oneway_unknown": 0
    }
    
    # 0. 必填列检查
    check_required_cols(df, ["u", "v", "key"], "edges_all.csv", buffer)
    
    # 1. Missing u, v, key
    before = len(df)
    df = df.dropna(subset=["u", "v", "key"])
    st["E_drop_missing_uvk"] = before - len(df)
    
    # 2. Drop self loops
    mask_loop = df["u"] == df["v"]
    loop_count = mask_loop.sum()
    st["E_drop_self_loop"] = loop_count
    df = df[~mask_loop].copy()
    
    # 3. Length checks (if exists)
    if "length" in df.columns:
        # to numeric
        df["length"] = pd.to_numeric(df["length"], errors="coerce")
        
        # NA (generated by coerce or original)
        mask_na = df["length"].isna()
        st["E_drop_length_na"] = mask_na.sum()
        df = df[~mask_na].copy()
        
        # Non-positive
        mask_nonpos = df["length"] <= 0
        st["E_drop_nonpositive_length"] = mask_nonpos.sum()
        df = df[~mask_nonpos].copy()
        
        # Too long
        mask_long = df["length"] > CONFIG["length_upper_m"]
        st["E_drop_too_long"] = mask_long.sum()
        df = df[~mask_long].copy()
    
    # 4. Lanes parsing
    # apply parse_lanes to entire column if exists, otherwise create it?
    # Raw often has key 'lanes'. If missing, treat all as fill default.
    if "lanes" not in df.columns:
        df["lanes"] = CONFIG["lanes_default"]
        st["E_lanes_fill_default"] = len(df)
    else:
        # Vectorized apply is simpler for logic counting ? No, direct list comprehension easiest for complex parse
        parsed_vals = [parse_lanes(x) for x in df["lanes"]]
        
        # Count outcomes
        lanes_clean = []
        for v in parsed_vals:
            if v != -1:
                lanes_clean.append(v)
                st["E_lanes_parse_success"] += 1
            else:
                lanes_clean.append(CONFIG["lanes_default"])
                st["E_lanes_parse_fail"] += 1
                st["E_lanes_fill_default"] += 1 # fail implies fill default
        
        df["lanes"] = lanes_clean

    # 5. Maxspeed parsing
    if "maxspeed" not in df.columns:
        df["maxspeed"] = CONFIG["maxspeed_default_mph"]
        st["E_maxspeed_fill_default"] = len(df)
    else:
        parsed_vals = [parse_maxspeed(x) for x in df["maxspeed"]]
        
        speed_clean = []
        for v in parsed_vals:
            if v > 0: # valid speed
                speed_clean.append(v)
                st["E_maxspeed_parse_success"] += 1
            else:
                speed_clean.append(CONFIG["maxspeed_default_mph"])
                st["E_maxspeed_parse_fail"] += 1
                st["E_maxspeed_fill_default"] += 1
        
        df["maxspeed"] = speed_clean

    # 6. Oneway parsing
    if "oneway" in df.columns:
        oneway_clean = []
        for x in df["oneway"]:
            res = parse_oneway(x)
            if res is True:
                oneway_clean.append(True)
                st["E_oneway_true"] += 1
            elif res is False:
                oneway_clean.append(False)
                st["E_oneway_false"] += 1
            elif res == -1:
                # -1 treated as True for cleaning purpose (as per requirement D3-6)
                # But we log it separately
                oneway_clean.append(True)
                st["E_oneway_minus1"] += 1
            else:
                # Unknown -> False (default assumption for oneway usually False) or None?
                # Usually bidir is default unless highway implies otherwise.
                # Here we assume False if unknown
                oneway_clean.append(False)
                st["E_oneway_unknown"] += 1
        df["oneway"] = oneway_clean
    else:
        # If missing, assume False everywhere
        df["oneway"] = False
        st["E_oneway_unknown"] = len(df) # Effectively unknown

    # 7. Exact duplicates
    before = len(df)
    df = df.drop_duplicates()
    st["E_drop_full_duplicate"] = before - len(df)
    
    # Save
    st["E_clean"] = len(df)
    df.to_csv(out_path, index=False)
    
    return st

def clean_bus_stops(raw_path, out_path, stats_dict, buffer):
    buffer.append(f"\n## 3. Bus Stops Cleaning ({os.path.basename(raw_path)})")
    
    if not os.path.exists(raw_path):
        msg = f"❌ Error: Raw file not found: {raw_path}"
        print(msg)
        buffer.append(msg)
        raise FileNotFoundError(msg)
        
    df = pd.read_csv(raw_path, low_memory=False)
    
    st = {
        "B_raw": len(df),
        "B_clean": 0,
        "B_drop_missing_or_non_numeric_coords": 0,
        "B_drop_invalid_range_coords": 0,
        "B_drop_duplicate_stop_id": 0,
        "B_drop_bbox_outlier": 0,
        "B_renamed_XY_to_stop_lonlat": False
    }

    # 1. 列名标准化: X->stop_lon, Y->stop_lat
    # 要求: 允许覆盖，即使 stop_lon 已存在也以 X 为准
    renamed = False
    if "X" in df.columns:
        df["stop_lon"] = df["X"]
        renamed = True
    if "Y" in df.columns:
        df["stop_lat"] = df["Y"]
        renamed = True
    
    st["B_renamed_XY_to_stop_lonlat"] = renamed
    
    # 0. 必填列检查 (in terms of final names)
    # At this point, stop_lon/lat should exist if X/Y existed, or if they existed originally.
    check_required_cols(df, ["stop_id", "stop_lon", "stop_lat"], "Bus_Stops.csv", buffer)
    
    # 2. 类型规范
    df["stop_lon"] = pd.to_numeric(df["stop_lon"], errors="coerce")
    df["stop_lat"] = pd.to_numeric(df["stop_lat"], errors="coerce")
    
    # 删除 NA
    before = len(df)
    df = df.dropna(subset=["stop_lon", "stop_lat"])
    st["B_drop_missing_or_non_numeric_coords"] = before - len(df)
    
    # 3. 坐标合法性
    mask_valid = (df["stop_lon"] >= -180) & (df["stop_lon"] <= 180) & \
                 (df["stop_lat"] >= -90) & (df["stop_lat"] <= 90)
    st["B_drop_invalid_range_coords"] = (~mask_valid).sum()
    df = df[mask_valid].copy()
    
    # 4. 去重
    before = len(df)
    df = df.drop_duplicates(subset=["stop_id"], keep="first")
    st["B_drop_duplicate_stop_id"] = before - len(df)
    
    # 5. BBox Consistency (with margin)
    if "bbox" in stats_dict:
        x_lo, x_hi, y_lo, y_hi = stats_dict["bbox"]
        margin = CONFIG["bbox_margin_deg"]
        
        bx_lo = x_lo - margin
        bx_hi = x_hi + margin
        by_lo = y_lo - margin
        by_hi = y_hi + margin
        
        mask_bbox = (df["stop_lon"] >= bx_lo) & (df["stop_lon"] <= bx_hi) & \
                    (df["stop_lat"] >= by_lo) & (df["stop_lat"] <= by_hi)
        st["B_drop_bbox_outlier"] = (~mask_bbox).sum()
        df = df[mask_bbox].copy()
    else:
        # 如果 Nodes 清洗失败或没跑，这里就没有 bbox 信息
        print("Warning: No Nodes BBox info available, skipping spatial filtering for stops.")
    
    # Save
    st["B_clean"] = len(df)
    df.to_csv(out_path, index=False)
    
    return st

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--outdir", default="data/processed")
    parser.add_argument("--nodes_raw", default="data/raw/nodes_all.csv")
    parser.add_argument("--edges_raw", default="data/raw/edges_all.csv")
    parser.add_argument("--bus_stops_raw", default="data/raw/Bus_Stops.csv")
    args = parser.parse_args()
    
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    
    log_buffer = []
    
    # Header
    log_buffer.append(f"# Data Cleaning Log")
    log_buffer.append(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log_buffer.append(f"Output Directory: `{args.outdir}`")
    log_buffer.append(f"\n### Config Snapshot")
    for k, v in CONFIG.items():
        log_buffer.append(f"- {k}: {v}")
    
    print("Starting data cleaning...")
    
    stats_share = {}
    
    # 1. Nodes
    st_nodes = clean_nodes(args.nodes_raw, outdir / "nodes_clean.csv", stats_share, log_buffer)
    
    # 2. Edges
    st_edges = clean_edges(args.edges_raw, outdir / "edges_clean.csv", log_buffer)
    
    # 3. Bus Stops
    st_bus = clean_bus_stops(args.bus_stops_raw, outdir / "bus_stops_clean.csv", stats_share, log_buffer)
    
    # Append Tables
    log_buffer.append("\n### Summary Table")
    log_buffer.append("| Dataset | Raw Rows | Clean Rows | Removed | Removed Rate |")
    log_buffer.append("|---|---|---|---|---|")
    
    def add_row(name, raw, clean):
        removed = raw - clean
        rate = f"{removed/raw*100:.2f}%" if raw > 0 else "0.00%"
        log_buffer.append(f"| {name} | {raw:,} | {clean:,} | {removed:,} | {rate} |")
        
    add_row("Nodes", st_nodes["N_raw"], st_nodes["N_clean"])
    add_row("Edges", st_edges["E_raw"], st_edges["E_clean"])
    add_row("BusStops", st_bus["B_raw"], st_bus["B_clean"])
    
    # Detailed stats block
    log_buffer.append("\n### Detailed Statistics (Ready for Paper)")
    log_buffer.append("#### Nodes Stats")
    for k, v in st_nodes.items():
        val = f"{v:.6f}" if isinstance(v, float) else f"{v}"
        log_buffer.append(f"{k}: {val}")
        
    log_buffer.append("\n#### Edges Stats")
    for k, v in st_edges.items():
        val = f"{v:.6f}" if isinstance(v, float) else f"{v}"
        log_buffer.append(f"{k}: {val}")
        
    log_buffer.append("\n#### Bus Stops Stats")
    for k, v in st_bus.items():
        val = f"{v:.6f}" if isinstance(v, float) else f"{v}"
        log_buffer.append(f"{k}: {val}")
        
    # Write Log
    log_path = outdir / "cleaning_log.md"
    with open(log_path, "w", encoding="utf-8") as f:
        f.write("\n".join(log_buffer))
        
    print(f"Done. Log saved to {log_path}")

if __name__ == "__main__":
    main()
