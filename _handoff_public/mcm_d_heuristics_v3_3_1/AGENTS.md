# 核心优化库代理指南 (AGENTS.md)

## 1. 概述 (OVERVIEW)
`mcm_d_heuristics` 是一个专为数学建模竞赛（如 MCM/ICM D题）设计的启发式优化库。其核心目标是通过高度解耦的架构，让参赛者在赛场上能够快速迭代模型，而无需修改底层的算法逻辑。

## 2. 架构设计 (ARCHITECTURE)
本库采用 **“问题-算法分离”** 的设计哲学：
- **问题层 (OptimizationProblem)**：封装目标函数、约束条件、解的解码方式（Decoder）及修复机制（Repair）。
- **算法层 (Algorithms)**：GA, PSO, SA 等通用启发式算子，通过统一接口调用问题层进行评估。

**核心准则**：**“只改 Problem 层，不动 Algorithm 层”**。当优化目标或变量变化时，只需更新 `OptimizationProblem` 的定义。

## 3. 核心模块 (KEY MODULES)
- **`problem.py`**: 定义 `OptimizationProblem` 基类。支持 Big-M 惩罚机制 (`Penalty`)、可行解存档 (`ParetoArchive`) 及常用解码器（如随机键转排列）。
- **`ga.py`**: 通用遗传算法。支持排列、二进制、实数和整数编码，内置精英保留和停滞触发的启发式变异。
- **`pso.py`**: 粒子群算法。适用于连续空间搜索，常通过 `decoder` 映射到离散空间。
- **`sa.py`**: 模拟退火算法。支持多邻域算子随机切换，适合局部精修。
- **`hybrid.py`**: 混合流水线编排。支持 `PSO -> GA -> SA` 等多阶段策略，实现全局探索与局部开发的平衡。
- **`budget.py`**: 预算控制。基于时间或评估次数强制终止，确保在规定时间内产出结果。

## 4. 使用方法 (USAGE)
实现一个新问题通常只需定义以下组件：

```python
from mcm_d_heuristics import OptimizationProblem, Penalty

# 1. 定义目标函数
def objective(solution):
    return sum(solution)  # minimize

# 2. 定义约束 (返回 violation >= 0)
def constraint_v(solution):
    return max(0, sum(solution) - 100)

# 3. 实例化问题
problem = OptimizationProblem(
    objective=objective,
    constraints=[constraint_v],
    penalty=Penalty(weight=1e9), # 自动处理惩罚项
    lb=[0]*10, ub=[1]*10         # 搜索空间边界
)

# 4. 一键切换算法
from mcm_d_heuristics.ga import GeneticAlgorithm, GAConfig
algo = GeneticAlgorithm(problem, GAConfig(encoding="real", n_genes=10))
best_sol, best_cost = algo.run()
```

## 5. 进阶特性
- **解码器 (Decoder)**：通过 `position -> solution` 的映射，允许在连续空间进行离散问题的搜索。
- **修复机制 (Repair)**：在评估前自动将不可行解“拉回”可行域。
- **混合流水线**：利用 `hybrid.py` 中的 `recipe_pso_ga_sa` 自动完成种子传递和多算法接力。
