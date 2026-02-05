"""
graph_io.py
图数据接口层：读取邻接矩阵 / edge list，并提供最短路距离查询 + 路径修复/播种工具。

D题典型输入：
- 邻接矩阵 (Adjacency Matrix) / 边列表 (Edge List)
- 代价不是欧氏距离，而是“链路权重”和“最短路距离”

本模块提供：
- read_adjacency_csv / read_edge_list_csv
- adjacency_to_edges / edges_to_graph
- GraphDistance: all-pairs Dijkstra cache
- build_shortest_path_matrix: dist_matrix for algorithms that want matrices
- k_shortest_paths: 用于 GA/SA 初始种群播种（避免随机死路）
- repair_path: 把“断路/不连通/带环”的路径修复成可走路径
- biased_random_walk_path: 面向终点的偏置随机游走，用于大图播种
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, Iterator, List, Optional, Sequence, Tuple, Union

import numpy as np

try:
    import networkx as nx
except Exception:  # pragma: no cover
    nx = None


def _require_nx() -> Any:
    if nx is None:
        raise ImportError("networkx is required for graph-related functions. Please pip install networkx.")
    return nx


def read_adjacency_csv(path: str, delimiter: str = ",") -> np.ndarray:
    """
    读取 csv 邻接矩阵（含权重）。
    约定：0 或空值表示无边（可按需要修改）。
    """
    mat = np.genfromtxt(path, delimiter=delimiter)
    if mat.ndim != 2 or mat.shape[0] != mat.shape[1]:
        raise ValueError("Adjacency matrix must be square 2D array.")
    return mat.astype(float)


def adjacency_to_edges(adj: np.ndarray, zero_means_no_edge: bool = True) -> List[Tuple[int, int, float]]:
    edges: List[Tuple[int, int, float]] = []
    n = int(adj.shape[0])
    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            w = float(adj[i, j])
            if zero_means_no_edge and (w == 0.0 or np.isnan(w)):
                continue
            if not zero_means_no_edge and np.isnan(w):
                continue
            edges.append((i, j, w))
    return edges


def read_edge_list_csv(
    path: str,
    delimiter: str = ",",
    has_header: bool = True,
    src_col: int = 0,
    dst_col: int = 1,
    w_col: int = 2,
) -> List[Tuple[int, int, float]]:
    """
    Read edge list from csv: (u, v, weight).
    """
    data = np.genfromtxt(path, delimiter=delimiter, skip_header=1 if has_header else 0)
    if data.ndim == 1 and data.size >= 3:
        data = data.reshape(1, -1)
    edges: List[Tuple[int, int, float]] = []
    for row in data:
        u = int(row[src_col])
        v = int(row[dst_col])
        w = float(row[w_col])
        edges.append((u, v, w))
    return edges


def edges_to_graph(edges: Sequence[Tuple[Any, Any, float]], directed: bool = True) -> Any:
    _nx = _require_nx()
    G = _nx.DiGraph() if directed else _nx.Graph()
    for u, v, w in edges:
        G.add_edge(u, v, weight=float(w))
    return G


@dataclass
class GraphDistance:
    """
    Cache all-pairs shortest path distances using Dijkstra.
    For contest-sized graphs this is usually fine; for very large graphs consider on-demand caching.
    """
    G: Any
    weight: str = "weight"
    _dist: Optional[Dict[Any, Dict[Any, float]]] = None

    def build(self) -> None:
        _nx = _require_nx()
        self._dist = dict(_nx.all_pairs_dijkstra_path_length(self.G, weight=self.weight))

    def dist(self, u: Any, v: Any) -> float:
        if self._dist is None:
            self.build()
        assert self._dist is not None
        return float(self._dist.get(u, {}).get(v, float("inf")))


def build_shortest_path_matrix(G: Any, nodes: Optional[Sequence[Any]] = None, weight: str = "weight") -> np.ndarray:
    """
    Build dist_matrix[i,j] = shortest path length between nodes[i] and nodes[j], inf if unreachable.
    """
    _nx = _require_nx()
    if nodes is None:
        nodes = list(G.nodes())
    nodes = list(nodes)
    idx = {n: i for i, n in enumerate(nodes)}
    n = len(nodes)
    mat = np.full((n, n), float("inf"), dtype=float)
    for i in range(n):
        mat[i, i] = 0.0
    for u, dists in _nx.all_pairs_dijkstra_path_length(G, weight=weight):
        if u not in idx:
            continue
        i = idx[u]
        for v, d in dists.items():
            if v in idx:
                mat[i, idx[v]] = float(d)
    return mat


def adjacency_csv_to_problem_matrix(path: str, delimiter: str = ",", directed: bool = True, zero_means_no_edge: bool = True) -> np.ndarray:
    """
    Convenience: csv adjacency -> Graph -> shortest-path dist matrix.
    """
    adj = read_adjacency_csv(path, delimiter=delimiter)
    edges = adjacency_to_edges(adj, zero_means_no_edge=zero_means_no_edge)
    G = edges_to_graph(edges, directed=directed)
    return build_shortest_path_matrix(G)


def k_shortest_paths(G: Any, source: Any, target: Any, k: int = 20, weight: str = "weight") -> List[List[Any]]:
    """
    Generate up to k shortest simple paths from source to target.

    ⚠️ 不推荐使用 all_simple_paths：路径数可能指数爆炸。
    对竞赛更稳健的做法是 k-shortest（Yen/shortest_simple_paths）。
    """
    _nx = _require_nx()
    if not _nx.has_path(G, source, target):
        return []
    gen = _nx.shortest_simple_paths(G, source, target, weight=weight)
    paths = []
    for p in gen:
        paths.append(list(p))
        if len(paths) >= k:
            break
    return paths


def path_cost(G: Any, path: Sequence[Any], weight: str = "weight") -> float:
    """Sum of edge weights along a path; inf if any edge missing."""
    if path is None or len(path) < 2:
        return float("inf")
    total = 0.0
    for a, b in zip(path[:-1], path[1:]):
        if not G.has_edge(a, b):
            return float("inf")
        total += float(G[a][b].get(weight, 1.0))
    return float(total)


def _remove_cycles(path: List[Any]) -> List[Any]:
    """Remove loops by cutting between repeated nodes."""
    seen: Dict[Any, int] = {}
    out: List[Any] = []
    for node in path:
        if node in seen:
            # cut loop: remove nodes after first occurrence
            cut = seen[node]
            out = out[: cut + 1]
            # refresh seen
            seen = {n: i for i, n in enumerate(out)}
        else:
            out.append(node)
            seen[node] = len(out) - 1
    return out


def repair_path(
    G: Any,
    path: Sequence[Any],
    source: Any,
    target: Any,
    weight: str = "weight",
    max_nodes: Optional[int] = None,
) -> List[Any]:
    """
    Repair a possibly disconnected / invalid path into a valid path.

    Strategy (robust for D题):
    1) Force endpoints to be source/target
    2) For each consecutive pair (u,v) in path, if edge missing, replace with shortest path u->v
    3) If any segment unreachable, fallback to shortest path from current node to target
    4) Remove cycles
    5) Optional: truncate length
    """
    _nx = _require_nx()
    if path is None or len(path) == 0:
        if _nx.has_path(G, source, target):
            return list(_nx.shortest_path(G, source, target, weight=weight))
        return [source, target]

    p = list(path)
    if p[0] != source:
        p = [source] + p
    if p[-1] != target:
        p = p + [target]

    repaired: List[Any] = [p[0]]
    for nxt in p[1:]:
        cur = repaired[-1]
        if cur == nxt:
            continue
        if G.has_edge(cur, nxt):
            repaired.append(nxt)
            continue
        # connect via shortest path segment
        if _nx.has_path(G, cur, nxt):
            seg = list(_nx.shortest_path(G, cur, nxt, weight=weight))
            repaired.extend(seg[1:])
        else:
            # cannot reach nxt; go directly to target if possible
            if _nx.has_path(G, cur, target):
                seg = list(_nx.shortest_path(G, cur, target, weight=weight))
                repaired.extend(seg[1:])
                break
            else:
                repaired.append(nxt)  # last resort: keep it (will be infeasible)
    repaired = _remove_cycles(repaired)
    if max_nodes is not None and len(repaired) > max_nodes:
        repaired = repaired[: max_nodes - 1] + [target]
        repaired = _remove_cycles(repaired)
        if repaired[-1] != target:
            repaired.append(target)
    return repaired


def biased_random_walk_path(
    G: Any,
    source: Any,
    target: Any,
    max_steps: int = 120,
    weight: str = "weight",
    beta: float = 2.0,
    p_explore: float = 0.3,
    avoid_loops: float = 0.8,
    directed: Optional[bool] = None,
    rng: Optional[np.random.Generator] = None,
) -> List[Any]:
    """Biased random walk from source to target.

    Motivation
    ----------
    D题大图播种时，纯 random-walk 很难走到终点；逐步调用 nx.has_path(...) 也很慢。
    这里预先计算 dist_to_target(v)（反向 Dijkstra），并用 softmax(exp(-beta*dist))
    给邻居赋权，从而“更大概率朝终点方向走”。

    Parameters
    ----------
    beta:
        偏置强度。越大越贪心地朝 dist 更小的邻居走。
    p_explore:
        探索概率。以该概率随机选邻居（保留多样性）。
    avoid_loops:
        若下一步会形成环，则以该概率拒绝该动作并重采样。

    Returns
    -------
    A possibly incomplete path; recommended to pass through repair_path(...).
    """
    _nx = _require_nx()
    if directed is None:
        directed = isinstance(G, _nx.DiGraph)

    if not _nx.has_node(G, source) or not _nx.has_node(G, target):
        return [source, target]

    # dist_to_target via reverse graph Dijkstra (one run)
    RG = G.reverse(copy=False) if directed else G
    try:
        dist_to_t = _nx.single_source_dijkstra_path_length(RG, target, weight=weight)
    except Exception:
        dist_to_t = {target: 0.0}

    if rng is None:
        rng = np.random.default_rng()
    cur = source
    path: List[Any] = [cur]

    def _neighbors(u: Any) -> List[Any]:
        return list(G.successors(u)) if directed else list(G.neighbors(u))

    steps = 0
    while cur != target and steps < max_steps:
        neigh = _neighbors(cur)
        if not neigh:
            break

        # exploration
        if rng.random() < p_explore:
            nxt = neigh[int(rng.integers(0, len(neigh)))]
        else:
            # exploit: softmax over exp(-beta*dist)
            scores = []
            for v in neigh:
                d = dist_to_t.get(v, float("inf"))
                if np.isfinite(d):
                    scores.append(np.exp(-beta * float(d)))
                else:
                    scores.append(0.0)
            s = float(np.sum(scores))
            if s <= 0:
                nxt = neigh[int(rng.integers(0, len(neigh)))]
            else:
                probs = np.asarray(scores, dtype=float) / s
                nxt = neigh[int(rng.choice(len(neigh), p=probs))]

        # loop-avoid
        if nxt in path and rng.random() < avoid_loops:
            steps += 1
            continue

        path.append(nxt)
        cur = nxt
        steps += 1

    return path
