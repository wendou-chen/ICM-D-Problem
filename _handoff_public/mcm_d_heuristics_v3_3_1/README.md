# mcm_d_heuristics (for MCM/ICM D)

这个小工具箱的目标：把 **“会变的部分（目标/约束/数据/解码）”** 从 **“不变的部分（迭代/更新/降温/交叉/变异）”** 中剥离出来，
让你在赛场上**只改 Problem 层，不动 Algorithm 层**。

## 1) 目录
- `problem.py`：统一的 `OptimizationProblem`（objective/decoder/constraints/penalty/bounds）
- `pso.py`：通用 PSO（gbest/lbest、自适应参数、反射边界、速度上限）
- `ga.py`：通用 GA（Permutation/Binary/Real/Integer + 显式 Elitism）
- `sa.py`：通用 SA（多邻域算子随机选择）
- `graph_io.py`：邻接矩阵/边表 + 最短路距离缓存（NetworkX）
- `viz.py`：收敛曲线 / 网络图 / 甘特图
- `examples/`：可直接运行的最小示例

## 2) 安装/运行
把本文件夹放到你的工程根目录，确保 Python 能找到它：

```bash
# 方式 A：在工程根目录运行
python -m examples.test_x2

# 方式 B：手动设置 PYTHONPATH
export PYTHONPATH=/path/to/your/project:$PYTHONPATH
python examples/test_x2.py
```

依赖：`numpy`, `matplotlib`；`networkx`（用于图数据部分）。

## 3) 你在赛场上要改的地方（通常只有这里）
```python
from mcm_d_heuristics import OptimizationProblem, Penalty

def objective(solution):
    ...

def constraint1(solution):  # 返回 violation >= 0
    ...

problem = OptimizationProblem(
    objective=objective,
    decoder=...,             # PSO离散化映射等
    constraints=[constraint1, ...],
    penalty=Penalty(weight=1e9),
    lb=..., ub=...           # PSO/连续决策用
)
```

然后随便换算法：
```python
best_sol, best_cost = GeneticAlgorithm(problem, GAConfig(...)).run()
# or
best_sol, best_cost = ParticleSwarmOptimizer(problem, PSOConfig(...)).run()
# or
best_sol, best_cost = SimulatedAnnealing(problem, init_solution, neighbor_ops, SAConfig(...)).run()
```
