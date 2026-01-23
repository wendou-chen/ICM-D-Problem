import numpy as np
from scipy.optimize import linprog, milp, LinearConstraint, Bounds
from typing import Optional, Dict, Union, Tuple, List

class OptimizationSolver:
    """
    针对 ICM D 题封装的精确优化算法库 (LP & MIP)。
    基于 Scipy.optimize 实现，提供矩阵化接口，符合数学建模标准形式。
    """

    def __init__(self, c: np.ndarray, 
                 A_ub: Optional[np.ndarray] = None, b_ub: Optional[np.ndarray] = None,
                 A_eq: Optional[np.ndarray] = None, b_eq: Optional[np.ndarray] = None,
                 bounds: Optional[List[Tuple[float, float]]] = None,
                 integrality: Optional[np.ndarray] = None):
        """
        初始化优化模型：min c^T x
        :param c: 目标函数系数向量 (注意：Scipy 默认求最小化，若是最大化需取反)
        :param A_ub: 不等式约束矩阵 (A_ub * x <= b_ub)
        :param b_ub: 不等式约束右端项
        :param A_eq: 等式约束矩阵 (A_eq * x == b_eq)
        :param b_eq: 等式约束右端项
        :param bounds: 变量取值范围 [(min, max), ...], 默认 (0, inf)
        :param integrality: 整数约束向量。0=连续, 1=整数, 2=半连续。默认为 None (全连续 LP)。
                            例如：[1, 1, 0] 表示前两个变量是整数，第三个是连续。
        """
        self.c = np.array(c)
        self.A_ub = np.array(A_ub) if A_ub is not None else None
        self.b_ub = np.array(b_ub) if b_ub is not None else None
        self.A_eq = np.array(A_eq) if A_eq is not None else None
        self.b_eq = np.array(b_eq) if b_eq is not None else None
        self.bounds = bounds
        self.integrality = np.array(integrality) if integrality is not None else None
        
        self.result = None

    def solve(self, method: str = 'highs') -> Dict:
        """
        求解优化问题。自动判断是 LP 还是 MIP。
        :param method: 求解器方法，推荐 'highs' (Scipy 新版最强求解器)
        :return: 结果字典 {'x': 最优解, 'fun': 最优值, 'status': 状态, 'success': 是否成功}
        """
        # 判断是否为混合整数规划 (MIP)
        is_mip = self.integrality is not None and np.any(self.integrality > 0)

        if is_mip:
            return self._solve_mip()
        else:
            return self._solve_lp(method)

    def _solve_lp(self, method) -> Dict:
        """求解线性规划 (Linear Programming)"""
        res = linprog(c=self.c, A_ub=self.A_ub, b_ub=self.b_ub, 
                      A_eq=self.A_eq, b_eq=self.b_eq, 
                      bounds=self.bounds, method=method)
        
        self.result = res
        return {
            'x': res.x,
            'fun': res.fun,
            'success': res.success,
            'message': res.message,
            # LP 特有的灵敏度分析数据 (Shadow Prices / Duals)
            # 注意：highs 方法目前返回 slack 但不直接返回 duals，单纯形法(simplex)才有
            'slack': res.slack, 
            'con': res.con
        }

    def _solve_mip(self) -> Dict:
        """求解混合整数规划 (Mixed Integer Programming)"""
        # Scipy 的 milp 接口稍微有点不同，需要封装 LinearConstraint
        constraints = []
        
        # 处理不等式约束: -inf <= A_ub * x <= b_ub
        if self.A_ub is not None:
            lb_ub = -np.inf * np.ones_like(self.b_ub)
            constraints.append(LinearConstraint(self.A_ub, lb_ub, self.b_ub))
            
        # 处理等式约束: b_eq <= A_eq * x <= b_eq
        if self.A_eq is not None:
            constraints.append(LinearConstraint(self.A_eq, self.b_eq, self.b_eq))
            
        # 处理变量边界
        if self.bounds is None:
            l, u = 0, np.inf
        else:
            # Unzip bounds
            l, u = zip(*self.bounds)
        
        res = milp(c=self.c, constraints=constraints, 
                   integrality=self.integrality, 
                   bounds=Bounds(l, u))
        
        self.result = res
        return {
            'x': res.x,
            'fun': res.fun,
            'success': res.success,
            'message': res.message
        }

    def sensitivity_analysis(self) -> str:
        """
        简单的灵敏度分析报告 (仅适用于 LP)。
        O 奖核心：分析资源的“影子价格”(Shadow Price)。
        """
        if self.integrality is not None:
            return "Sensitivity analysis is not available for MIP (Integer Problems)."
        
        if self.result is None or not self.result.success:
            return "Optimization failed or not run yet."

        # 注意：使用 'highs' 求解器时，scipy 1.9+ 可能不直接返回 lambda (dual values)
        # 这里只是一个占位符，提示你要去检查约束的松弛度 (Slack)
        # Slack = 0 意味着该约束是“紧”的 (Binding Constraint)，即资源已耗尽，是瓶颈。
        
        report = "--- Sensitivity Analysis (Slackness) ---\n"
        if self.A_ub is not None:
            for i, s in enumerate(self.result.slack):
                status = "Binding (Bottleneck)" if s < 1e-5 else "Non-binding (Surplus)"
                report += f"Inequality Constraint {i}: Slack = {s:.4f} -> {status}\n"
        
        return report

# --- 辅助函数：快速生成常见的 Gurobi 风格变量 ---
def binary_vec(n: int) -> np.ndarray:
    """生成长度为 n 的全 1 向量，用于标记变量为整数"""
    return np.ones(n)