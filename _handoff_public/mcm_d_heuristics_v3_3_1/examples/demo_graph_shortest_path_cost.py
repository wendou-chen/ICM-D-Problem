""" 
examples/demo_graph_shortest_path_cost.py
示例：D题常见“给拓扑图(邻接矩阵/边表)，两点代价 = 最短路权重”。

演示：
1) 构造稀疏加权无向图（边表）
2) 用 GraphDistance 预计算 all-pairs shortest path
3) 以“访问顺序(排列)”为决策变量，计算 tour 代价

注意
----
这里的 tour 只是演示“最短路代价接口”的用法。
相邻访问点之间不一定存在物理直连边；真实代价由最短路决定。
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import numpy as np

from mcm_d_heuristics_v3_3 import OptimizationProblem, Penalty
from mcm_d_heuristics_v3_3.graph_io import GraphDistance, edges_to_graph
from mcm_d_heuristics_v3_3.ga import GeneticAlgorithm, GAConfig
from mcm_d_heuristics_v3_3.viz import draw_network, plot_convergence

np.random.seed(1)

N = 15
# random sparse undirected graph edges
edges = []
for i in range(N):
    for j in range(i + 1, N):
        if np.random.rand() < 0.18:
            w = 1.0 + 9.0 * np.random.rand()
            edges.append((i, j, w))

# Ensure connectivity by adding a chain
for i in range(N - 1):
    edges.append((i, i + 1, 1.0 + 2.0 * np.random.rand()))

G = edges_to_graph(edges, directed=False)
# all-pairs distances cached on first call
Dist = GraphDistance(G)


def tour_cost(route: np.ndarray) -> float:
    r = np.asarray(route, dtype=int).reshape(-1)
    s = 0.0
    for k in range(N - 1):
        s += Dist.dist(r[k], r[k + 1])
    s += Dist.dist(r[-1], r[0])
    return float(s)


problem = OptimizationProblem(objective=tour_cost, decoder=None, constraints=[], penalty=Penalty(weight=1e9))

ga = GeneticAlgorithm(
    problem,
    GAConfig(
        encoding="permutation",
        perm_size=N,
        n_pop=140,
        max_gen=220,
        cx_rate=0.9,
        mut_rate=0.06,
        elitism_k=3,
        seed=4,
    ),
)
best_route, best_cost = ga.run()
print("best_cost:", best_cost)
plot_convergence(ga.history_best, "GA on shortest-path tour cost")

# visualize network + highlight tour edges (tour edges are visit order, not necessarily physical links)
highlight = [(int(best_route[i]), int(best_route[i + 1])) for i in range(N - 1)] + [
    (int(best_route[-1]), int(best_route[0]))
]
draw_network(edges, highlight_edges=highlight, title="Graph (highlight shows tour order, cost via shortest paths)")
