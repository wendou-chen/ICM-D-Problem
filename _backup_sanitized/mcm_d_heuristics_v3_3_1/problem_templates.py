"""
problem_templates.py
Common optimization problem templates for ICM D Heuristics.

Implementations:
1. BinarySelectionProblem: 0/1 Knapsack/Selection
2. IntegerAllocationProblem: Resource allocation
3. PermutationScheduleProblem: TSP/Sequencing
4. GraphDesignProblem: Network topology selection
5. ContinuousOptimizationProblem: Function optimization

Each template implements the OptimizationProblem contract, including plotting and demo.
"""
from __future__ import annotations

import numpy as np
import matplotlib.pyplot as plt
from typing import Any, List, Optional, Tuple, Callable, Union
import time

try:
    import networkx as nx
except ImportError:
    nx = None

from .problem import OptimizationProblem, decode_sigmoid_to_binary, decode_random_keys_to_permutation, decode_round_to_integer
from .pso import ParticleSwarmOptimizer, PSOConfig
from .ga import GeneticAlgorithm, GAConfig

# Dummy objective for bypassing dataclass validation when overriding evaluate_solution
def _dummy_objective(x: Any) -> float:
    return 0.0

class BinarySelectionProblem(OptimizationProblem):
    """
    Template for 0/1 Selection Problems.
    """
    def __init__(self, costs: np.ndarray, values: np.ndarray, budget: float, name: str = "BinarySelection"):
        # Pass dummy objective
        super().__init__(objective=_dummy_objective)
        self.costs = np.asarray(costs)
        self.values = np.asarray(values)
        self.budget = budget
        self.name = name
        self.n = len(costs)
        
        # Bounds for PSO
        self.lb = np.zeros(self.n)
        self.ub = np.ones(self.n)
        
    def decode(self, position: np.ndarray) -> np.ndarray:
        return decode_sigmoid_to_binary(position)
    
    def repair_solution(self, solution: np.ndarray) -> np.ndarray:
        """Greedy repair."""
        cost = np.sum(solution * self.costs)
        if cost <= self.budget:
            return solution
        
        indices = np.where(solution == 1)[0]
        efficiency = self.values[indices] / (self.costs[indices] + 1e-9)
        sorted_idx = indices[np.argsort(efficiency)] 
        
        y = solution.copy()
        current_cost = cost
        
        for idx in sorted_idx:
            if current_cost <= self.budget:
                break
            y[idx] = 0
            current_cost -= self.costs[idx]
            
        return y
    
    def evaluate_solution(self, solution: np.ndarray, **kwargs) -> float:
        cost = np.sum(solution * self.costs)
        val = np.sum(solution * self.values)
        penalty = 0.0
        if cost > self.budget:
            penalty = (cost - self.budget) * 1e6
        return -val + penalty
    
    def plot_solution(self, solution: np.ndarray, ax: Optional[plt.Axes] = None) -> plt.Axes:
        if ax is None:
            _, ax = plt.subplots(figsize=(8, 4))
        indices = np.arange(self.n)
        colors = ['red' if s else 'lightgray' for s in solution]
        ax.bar(indices, self.values, color=colors)
        ax.set_title(f"{self.name}: Value={np.sum(solution*self.values):.1f}, Cost={np.sum(solution*self.costs):.1f}/{self.budget}")
        return ax

    @staticmethod
    def demo_run():
        print("--- BinarySelectionProblem Demo ---")
        n = 20
        rng = np.random.default_rng(42)
        costs = rng.uniform(10, 50, n)
        values = rng.uniform(20, 100, n)
        budget = np.sum(costs) * 0.4
        problem = BinarySelectionProblem(costs, values, budget)
        cfg = GAConfig(encoding="binary", n_genes=n, n_pop=50, max_gen=30, seed=42)
        ga = GeneticAlgorithm(problem, cfg)
        best, cost = ga.run()
        print(f"Best Cost: {cost}")
        try:
            problem.plot_solution(best)
            plt.close()
        except Exception:
            pass

class IntegerAllocationProblem(OptimizationProblem):
    """
    Template for Integer Allocation.
    """
    def __init__(self, n_vars: int, lower: int, upper: int, target_sum: int):
        super().__init__(objective=_dummy_objective)
        self.n_vars = n_vars
        self.int_lb = np.full(n_vars, lower, dtype=int)
        self.int_ub = np.full(n_vars, upper, dtype=int)
        self.target_sum = target_sum
        self.lb = self.int_lb.astype(float)
        self.ub = self.int_ub.astype(float)
        
    def decode(self, position: np.ndarray) -> np.ndarray:
        return decode_round_to_integer(position, self.int_lb, self.int_ub)
    
    def repair_solution(self, solution: np.ndarray) -> np.ndarray:
        current_sum = np.sum(solution)
        diff =  self.target_sum - current_sum 
        y = solution.copy()
        iters = 0
        while diff != 0 and iters < 100:
            idx = np.random.randint(0, self.n_vars)
            if diff > 0: 
                if y[idx] < self.int_ub[idx]:
                    y[idx] += 1
                    diff -= 1
            else:
                if y[idx] > self.int_lb[idx]:
                    y[idx] -= 1
                    diff += 1
            iters += 1
        return y
        
    def evaluate_solution(self, solution: np.ndarray, **kwargs) -> float:
        target_violation = abs(np.sum(solution) - self.target_sum)
        variance = np.var(solution)
        return float(variance + target_violation * 1000)
    
    def plot_solution(self, solution: np.ndarray, ax: Optional[plt.Axes] = None) -> plt.Axes:
        if ax is None:
            _, ax = plt.subplots()
        ax.bar(range(self.n_vars), solution)
        ax.set_title(f"Allocation: Sum={np.sum(solution)} (Target={self.target_sum})")
        return ax

    @staticmethod
    def demo_run():
        print("--- IntegerAllocationProblem Demo ---")
        problem = IntegerAllocationProblem(n_vars=10, lower=1, upper=10, target_sum=50)
        cfg = GAConfig(encoding="integer", n_genes=10, lb=problem.int_lb, ub=problem.int_ub, n_pop=40, max_gen=20)
        ga = GeneticAlgorithm(problem, cfg)
        best, cost = ga.run()
        print(f"Best: {best}, Cost: {cost}")
        problem.plot_solution(best)
        plt.close()

class PermutationScheduleProblem(OptimizationProblem):
    """
    Template for Permutation Problems (TSP).
    """
    def __init__(self, coords: np.ndarray):
        super().__init__(objective=_dummy_objective)
        self.coords = coords
        self.n = len(coords)
        self.lb = np.zeros(self.n)
        self.ub = np.ones(self.n)

    def decode(self, position: np.ndarray) -> np.ndarray:
        return decode_random_keys_to_permutation(position)
    
    def repair_solution(self, solution: np.ndarray) -> np.ndarray:
        return solution
    
    def evaluate_solution(self, solution: np.ndarray, **kwargs) -> float:
        dist = 0.0
        for i in range(self.n - 1):
            u, v = solution[i], solution[i+1]
            dist += np.linalg.norm(self.coords[u] - self.coords[v])
        dist += np.linalg.norm(self.coords[solution[-1]] - self.coords[solution[0]])
        return dist
    
    def plot_solution(self, solution: np.ndarray, ax: Optional[plt.Axes] = None) -> plt.Axes:
        if ax is None:
            _, ax = plt.subplots()
        route = self.coords[solution]
        route = np.vstack([route, route[0]]) 
        ax.plot(route[:,0], route[:,1], 'o-')
        ax.set_title(f"TSP Cost: {self.evaluate_solution(solution):.2f}")
        return ax

    @staticmethod
    def demo_run():
        print("--- PermutationScheduleProblem Demo ---")
        rng = np.random.default_rng(42)
        coords = rng.uniform(0, 100, (15, 2))
        problem = PermutationScheduleProblem(coords)
        cfg = GAConfig(encoding="permutation", perm_size=15, n_pop=50, max_gen=50)
        ga = GeneticAlgorithm(problem, cfg)
        best, cost = ga.run()
        print(f"Best Cost: {cost}")
        problem.plot_solution(best)
        plt.close()

class GraphDesignProblem(OptimizationProblem):
    """
    Template for Graph Design.
    """
    def __init__(self, n_nodes: int, all_edges: List[Tuple[int, int, float]], fixed_cost: float):
        super().__init__(objective=_dummy_objective)
        self.n_nodes = n_nodes
        self.all_edges = all_edges 
        self.fixed_cost = fixed_cost
        self.n_edges = len(all_edges)
        self.lb = np.zeros(self.n_edges)
        self.ub = np.ones(self.n_edges)

    def decode(self, position: np.ndarray) -> np.ndarray:
        return decode_sigmoid_to_binary(position)
    
    def repair_solution(self, solution: np.ndarray) -> np.ndarray:
        return solution

    def evaluate_solution(self, solution: np.ndarray, **kwargs) -> float:
        indices = np.where(solution == 1)[0]
        cost = 0.0
        if nx:
            G = nx.Graph()
            G.add_nodes_from(range(self.n_nodes))
            edge_list = []
            for idx in indices:
                u, v, w = self.all_edges[idx]
                cost += w
                edge_list.append((u, v))
            G.add_edges_from(edge_list)
            if not nx.is_connected(G):
                cost += 1e5 
        else:
            cost += 1e5
        return cost + self.fixed_cost * np.sum(solution)

    def plot_solution(self, solution: np.ndarray, ax: Optional[plt.Axes] = None) -> plt.Axes:
        if ax is None:
            _, ax = plt.subplots()
        if not nx:
            return ax
        G_full = nx.Graph()
        G_full.add_nodes_from(range(self.n_nodes))
        G_full.add_weighted_edges_from(self.all_edges)
        pos = nx.spring_layout(G_full, seed=42)
        nx.draw_networkx_nodes(G_full, pos, ax=ax, node_size=30, node_color='lightgray')
        nx.draw_networkx_edges(G_full, pos, ax=ax, alpha=0.1)
        indices = np.where(solution == 1)[0]
        sel_edges = [(self.all_edges[i][0], self.all_edges[i][1]) for i in indices]
        nx.draw_networkx_edges(G_full, pos, edgelist=sel_edges, ax=ax, edge_color='red', width=2)
        return ax

    @staticmethod
    def demo_run():
        print("--- GraphDesignProblem Demo ---")
        if nx is None: return
        import itertools
        rng = np.random.default_rng(42)
        edges = []
        for u, v in itertools.combinations(range(10), 2):
            w = rng.uniform(1, 10)
            edges.append((u, v, w))
        problem = GraphDesignProblem(10, edges, fixed_cost=2.0)
        cfg = PSOConfig(num_particles=30, max_iter=20)
        pso = ParticleSwarmOptimizer(problem, cfg)
        best, cost = pso.run()
        print(f"Best Cost: {cost}")
        problem.plot_solution(problem.decode(best))
        plt.close()

class ContinuousOptimizationProblem(OptimizationProblem):
    """
    Template for Continuous Function Optimization.
    """
    def __init__(self, dim: int = 10):
        super().__init__(objective=_dummy_objective)
        self.dim = dim
        self.lb = np.full(dim, -5.12)
        self.ub = np.full(dim, 5.12)
    
    def decode(self, position: np.ndarray) -> np.ndarray:
        return position
    
    def repair_solution(self, solution: np.ndarray) -> np.ndarray:
        return np.clip(solution, self.lb, self.ub)
    
    def evaluate_solution(self, solution: np.ndarray, **kwargs) -> float:
        A = 10
        return A * self.dim + np.sum(solution**2 - A * np.cos(2 * np.pi * solution))

    def plot_solution(self, solution: np.ndarray, ax: Optional[plt.Axes] = None) -> plt.Axes:
        if ax is None:
            _, ax = plt.subplots()
        ax.stem(solution)
        ax.set_ylim([-5.12, 5.12])
        return ax

    @staticmethod
    def demo_run():
        print("--- ContinuousOptimizationProblem Demo ---")
        problem = ContinuousOptimizationProblem(5)
        cfg = PSOConfig(num_particles=40, max_iter=50)
        pso = ParticleSwarmOptimizer(problem, cfg)
        best, cost = pso.run()
        print(f"Best: {cost:.4f}")
        problem.plot_solution(best)
        plt.close()
