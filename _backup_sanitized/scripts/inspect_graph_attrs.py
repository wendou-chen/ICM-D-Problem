"""
inspect_graph_attrs.py
读取 graph.pkl，统计边属性名出现频次，检查潜在的单位不一致问题。
"""
import pickle
from collections import Counter, defaultdict
from pathlib import Path
import networkx as nx
import numpy as np

GRAPH_PATH = Path("data/processed/graph.pkl")  # 修正路径

with open(GRAPH_PATH, "rb") as f:
    G = pickle.load(f)

print("=" * 60)
print("Graph type:", type(G).__name__)
print(f"Is MultiGraph: {G.is_multigraph()}")
print(f"Is Directed:   {G.is_directed()}")
print(f"nV = {G.number_of_nodes():,}   nE = {G.number_of_edges():,}")
print("=" * 60)

# ========== Step A: 统计边属性名出现频次 ==========
counter = Counter()
attr_values = defaultdict(list)  # 收集每个属性的数值用于范围分析

NUMERIC_ATTRS = {"weight", "cost", "time", "travel_time", "time_min", "time_s",
                 "length", "length_m", "length_km", "distance", "capacity", "speed"}

if G.is_multigraph():
    edges_iter = G.edges(keys=True, data=True)
else:
    edges_iter = ((u, v, None, d) for u, v, d in G.edges(data=True))

for u, v, k, data in edges_iter:
    counter.update(data.keys())
    for attr in NUMERIC_ATTRS:
        if attr in data:
            val = data[attr]
            if isinstance(val, (int, float)) and np.isfinite(val):
                attr_values[attr].append(float(val))

print("\n[Step A] Top edge attribute keys (frequency):")
for key, cnt in counter.most_common(30):
    print(f"  {key:25s}  {cnt:>10,}")

# ========== Step B: 数值范围分析 (检测单位不一致) ==========
print("\n[Step B] Numeric attribute value ranges:")
for attr in sorted(attr_values.keys()):
    vals = attr_values[attr]
    if len(vals) == 0:
        continue
    arr = np.array(vals)
    print(f"  {attr:20s}  n={len(vals):>8,}  "
          f"min={arr.min():.4g}  max={arr.max():.4g}  "
          f"mean={arr.mean():.4g}  std={arr.std():.4g}")

# ========== Step C: 隐含速度检查 (length / time) ==========
print("\n[Step C] Implied speed check (length / time):")
length_attrs = [a for a in attr_values if "length" in a or "distance" in a]
time_attrs = [a for a in attr_values if "time" in a]

if length_attrs and time_attrs:
    # 取第一对进行检查
    len_attr = length_attrs[0]
    time_attr = time_attrs[0]
    print(f"  Using: {len_attr} / {time_attr}")
    
    speeds = []
    if G.is_multigraph():
        edges_iter = G.edges(keys=True, data=True)
    else:
        edges_iter = ((u, v, None, d) for u, v, d in G.edges(data=True))
    
    for u, v, k, data in edges_iter:
        L = data.get(len_attr)
        T = data.get(time_attr)
        if L is not None and T is not None and T > 1e-9:
            speeds.append(float(L) / float(T))
    
    if speeds:
        arr = np.array(speeds)
        print(f"  Implied speed: n={len(speeds):,}  "
              f"min={arr.min():.4g}  max={arr.max():.4g}  mean={arr.mean():.4g}")
        if arr.max() > 500:
            print("  ⚠️ WARNING: max speed > 500, possible unit mismatch (m vs km, s vs min)?")
else:
    print("  (No matching length/time attribute pair found)")

# ========== Step D: 样本边数据 ==========
print("\n[Step D] Sample edge data (first 3 edges):")
if G.number_of_edges() > 0:
    if G.is_multigraph():
        for i, (u, v, k, data) in enumerate(G.edges(keys=True, data=True)):
            if i >= 3:
                break
            print(f"  Edge {i+1}: ({u}, {v}, key={k})")
            print(f"    {data}")
    else:
        for i, (u, v, data) in enumerate(G.edges(data=True)):
            if i >= 3:
                break
            print(f"  Edge {i+1}: ({u}, {v})")
            print(f"    {data}")

print("\n" + "=" * 60)
print("Inspection complete.")

