# OptimizationProblem 接口合同

本文档定义了 `mcm_d_heuristics` 框架中所有优化问题必须遵循的接口规范。

---

## 核心概念

| 术语 | 定义 |
|------|------|
| **Genome/Position** | 算法搜索空间中的表示（如连续向量、排列、二进制串） |
| **Solution** | 可行解/表型（经 decode 后的实际决策方案） |
| **Cost** | 标量化目标值（最小化方向） |

---

## 接口方法

### 1. `decode(genome) -> solution`

**用途**：将算法内部表示（Genome）映射为实际解（Solution）。

```python
def decode(self, genome: np.ndarray) -> Any:
    """
    将搜索空间表示转换为问题域的解。
    
    Args:
        genome: 算法使用的内部表示
            - PSO: 连续向量 [0,1]^D
            - GA (binary): 0/1 向量
            - GA (permutation): 排列数组
    
    Returns:
        solution: 问题域中的解表示
    
    Notes:
        - 如果 genome 和 solution 相同，可返回 genome.copy()
        - 用于 PSO 解离散问题（如 sigmoid -> binary）
    """
```

### 2. `repair_solution(solution) -> solution`

**用途**：修复不可行解，确保约束满足。

```python
def repair_solution(self, solution: Any) -> Any:
    """
    修复解以满足所有硬约束。
    
    Args:
        solution: 可能不可行的解
    
    Returns:
        solution: 修复后的可行解
    
    Notes:
        - 必须实现（即使是恒等函数）
        - 典型修复策略：
            - 预算约束：贪心删除/缩放
            - 路径约束：最短路修复
            - 容量约束：溢出重分配
    """
```

### 3. `evaluate_solution(solution) -> cost`

**用途**：计算解的目标函数值。

```python
def evaluate_solution(self, solution: Any) -> float:
    """
    评估解的成本（最小化目标）。
    
    Args:
        solution: 问题域中的解
    
    Returns:
        cost: 标量目标值（越小越好）
    
    Notes:
        - 多目标问题应内部标量化（加权和/主目标）
        - 约束违反可通过惩罚项加入 cost
        - 不可行解应返回 float('inf') 或极大值
    """
```

### 4. `evaluate_position(position) -> cost`

**用途**：端到端评估（decode + repair + evaluate）。

```python
def evaluate_position(self, position: np.ndarray) -> float:
    """
    从原始 position 一步到位计算 cost。
    
    等价于：
        solution = self.decode(position)
        solution = self.repair_solution(solution)
        return self.evaluate_solution(solution)
    """
```

### 5. `plot_solution(solution, ax=None) -> ax`

**用途**：可视化解，用于调试和论文图表。

```python
def plot_solution(self, solution: Any, ax: Optional[plt.Axes] = None) -> plt.Axes:
    """
    绘制解的可视化。
    
    Args:
        solution: 问题域中的解
        ax: matplotlib Axes 对象（可选，不提供则创建新图）
    
    Returns:
        ax: 绑定了绘图内容的 Axes 对象
    
    Notes:
        - 图类问题：绘制选中边/节点
        - 路径问题：绘制路线
        - 分配问题：柱状图/热力图
    """
```

---

## 可选方法

### `violation(solution) -> float`

返回约束违反总量（用于惩罚法或可行性检查）。

### `objective_vector(solution) -> np.ndarray`

返回多目标向量（供 Pareto 存档使用）。

---

## 类属性

| 属性 | 类型 | 说明 |
|------|------|------|
| `lb` | `np.ndarray` | 搜索空间下界（PSO 必需） |
| `ub` | `np.ndarray` | 搜索空间上界（PSO 必需） |
| `n_dim` | `int` | 搜索空间维度 |
| `constraints` | `List[Callable]` | 约束函数列表（可选） |

---

## 使用示例

```python
from mcm_d_heuristics_v3_3_1.problem_templates import BinarySelectionProblem

# 定义问题
problem = BinarySelectionProblem(
    costs=[10, 20, 15, 25],
    values=[5, 8, 6, 9],
    budget=50
)

# 算法调用
from mcm_d_heuristics_v3_3_1.pso import ParticleSwarmOptimizer, PSOConfig

pso = ParticleSwarmOptimizer(problem, PSOConfig())
best_sol, best_cost = pso.run()

# 可视化
problem.plot_solution(best_sol)
```

---

## 模板类继承关系

```
OptimizationProblem (Base)
├── BinarySelectionProblem    # 0/1 选择
├── IntegerAllocationProblem  # 离散分配
├── PermutationScheduleProblem # 排序/路由
├── GraphDesignProblem        # 图设计
└── ContinuousOptimizationProblem # 连续优化
```

---

## 验收标准

每个 Problem 实现必须通过以下检查：

1. `decode()` 返回有效解
2. `repair_solution()` 返回可行解
3. `evaluate_solution()` 返回有限浮点数
4. `plot_solution()` 不抛出异常
5. `demo_run()` 在 10 秒内完成

运行验收：
```bash
python run_all_acceptance.py
```
