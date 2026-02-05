"""
nsga2.py
Non-dominated Sorting Genetic Algorithm II (NSGA-II) implementation.
"""
import numpy as np
from dataclasses import dataclass
from typing import List, Tuple, Optional
from .problem import OptimizationProblem

@dataclass
class NSGA2Config:
    pop_size: int = 100
    max_gen: int = 200
    crossover_rate: float = 0.9
    mutation_rate: float = 0.1
    eta_c: float = 20.0  # Distribution index for SBX crossover
    eta_m: float = 20.0  # Distribution index for Polynomial mutation
    seed: int = 42

class NSGA2:
    def __init__(self, problem: OptimizationProblem, config: NSGA2Config):
        self.problem = problem
        self.config = config
        self.rng = np.random.default_rng(config.seed)
        
        # Determine number of objectives by evaluating a random solution
        # This requires the problem to implement evaluate_objectives
        if not hasattr(self.problem, 'evaluate_objectives'):
            raise ValueError("Problem must implement evaluate_objectives for NSGA-II")
            
        dummy_sol = self.problem.decode(self.problem.lb)
        dummy_objs = self.problem.evaluate_objectives(dummy_sol)
        self.n_obj = len(dummy_objs)
        self.n_var = len(self.problem.lb)

    def _initialize_population(self) -> np.ndarray:
        return self.rng.uniform(self.problem.lb, self.problem.ub, size=(self.config.pop_size, self.n_var))

    def _fast_non_dominated_sort(self, objectives: np.ndarray) -> List[List[int]]:
        N = len(objectives)
        S = [[] for _ in range(N)]
        n = np.zeros(N, dtype=int)
        rank = np.zeros(N, dtype=int)
        fronts = [[]]

        for p in range(N):
            S[p] = []
            n[p] = 0
            for q in range(N):
                # Domination check: p dominates q?
                # Minimization assumed
                diff = objectives[p] - objectives[q]
                if np.all(diff <= 0) and np.any(diff < 0):
                    S[p].append(q)
                elif np.all(diff >= 0) and np.any(diff > 0):
                    n[p] += 1
            if n[p] == 0:
                rank[p] = 0
                fronts[0].append(p)

        i = 0
        while len(fronts[i]) > 0:
            Q = []
            for p in fronts[i]:
                for q in S[p]:
                    n[q] -= 1
                    if n[q] == 0:
                        rank[q] = i + 1
                        Q.append(q)
            i += 1
            if len(Q) > 0:
                fronts.append(Q)
            else:
                break
                
        return fronts

    def _crowding_distance_assignment(self, objectives: np.ndarray, front: List[int]) -> np.ndarray:
        l = len(front)
        distances = np.zeros(l)
        if l == 0:
            return distances
            
        for m in range(self.n_obj):
            # Sort by objective m
            sorted_idx = np.argsort(objectives[front, m])
            
            # Boundary points get infinity
            distances[sorted_idx[0]] = np.inf
            distances[sorted_idx[-1]] = np.inf
            
            obj_range = objectives[front[sorted_idx[-1]], m] - objectives[front[sorted_idx[0]], m]
            if obj_range == 0:
                continue
                
            # Intermediate points
            # dist[i] += (obj[i+1] - obj[i-1]) / range
            # Note: sorted_idx[i] corresponds to the i-th individual in the sorted list
            for i in range(1, l - 1):
                distances[sorted_idx[i]] += (objectives[front[sorted_idx[i+1]], m] - objectives[front[sorted_idx[i-1]], m]) / obj_range
                
        return distances

    def _tournament_selection(self, pop: np.ndarray, ranks: np.ndarray, distances: np.ndarray) -> np.ndarray:
        # Binary tournament
        N = len(pop)
        p1 = self.rng.integers(0, N, size=N)
        p2 = self.rng.integers(0, N, size=N)
        
        selected_idx = []
        for i in range(N):
            a, b = p1[i], p2[i]
            # Select better rank (lower is better)
            if ranks[a] < ranks[b]:
                selected_idx.append(a)
            elif ranks[b] < ranks[a]:
                selected_idx.append(b)
            else:
                # Same rank, select larger crowding distance
                if distances[a] > distances[b]:
                    selected_idx.append(a)
                else:
                    selected_idx.append(b)
                    
        return pop[selected_idx]

    def _sbx_crossover(self, pop: np.ndarray) -> np.ndarray:
        # Simulated Binary Crossover
        offspring = []
        N = len(pop)
        
        # Shuffle for pairing
        idx = self.rng.permutation(N)
        
        for i in range(0, N, 2):
            p1 = pop[idx[i]]
            # Handle odd population
            p2 = pop[idx[i+1]] if i+1 < N else pop[idx[0]]
            
            if self.rng.random() < self.config.crossover_rate:
                c1 = np.zeros_like(p1)
                c2 = np.zeros_like(p2)
                
                for j in range(self.n_var):
                    if self.rng.random() <= 0.5:
                        if abs(p1[j] - p2[j]) > 1e-14:
                            y1 = min(p1[j], p2[j])
                            y2 = max(p1[j], p2[j])
                            lb, ub = self.problem.lb[j], self.problem.ub[j]
                            
                            rand = self.rng.random()
                            beta = 1.0 + (2.0 * (y1 - lb) / (y2 - y1))
                            alpha = 2.0 - beta**-(self.config.eta_c + 1.0)
                            
                            if rand <= (1.0 / alpha):
                                beta_q = (rand * alpha)**(1.0 / (self.config.eta_c + 1.0))
                            else:
                                beta_q = (1.0 / (2.0 - rand * alpha))**(1.0 / (self.config.eta_c + 1.0))
                                
                            c1[j] = 0.5 * ((y1 + y2) - beta_q * (y2 - y1))
                            
                            beta = 1.0 + (2.0 * (ub - y2) / (y2 - y1))
                            alpha = 2.0 - beta**-(self.config.eta_c + 1.0)
                            
                            if rand <= (1.0 / alpha):
                                beta_q = (rand * alpha)**(1.0 / (self.config.eta_c + 1.0))
                            else:
                                beta_q = (1.0 / (2.0 - rand * alpha))**(1.0 / (self.config.eta_c + 1.0))
                                
                            c2[j] = 0.5 * ((y1 + y2) + beta_q * (y2 - y1))
                            
                            c1[j] = np.clip(c1[j], lb, ub)
                            c2[j] = np.clip(c2[j], lb, ub)
                        else:
                            c1[j] = p1[j]
                            c2[j] = p2[j]
                    else:
                        c1[j] = p1[j]
                        c2[j] = p2[j]
                offspring.append(c1)
                offspring.append(c2)
            else:
                offspring.append(p1)
                offspring.append(p2)
                
        return np.array(offspring)[:N]

    def _polynomial_mutation(self, pop: np.ndarray) -> np.ndarray:
        mutated = pop.copy()
        for i in range(len(mutated)):
            if self.rng.random() < self.config.mutation_rate:
                for j in range(self.n_var):
                    if self.rng.random() < (1.0 / self.n_var):
                        y = mutated[i, j]
                        lb, ub = self.problem.lb[j], self.problem.ub[j]
                        delta_1 = (y - lb) / (ub - lb)
                        delta_2 = (ub - y) / (ub - lb)
                        
                        rand = self.rng.random()
                        mut_pow = 1.0 / (self.config.eta_m + 1.0)
                        
                        if rand <= 0.5:
                            val = 2.0 * rand + (1.0 - 2.0 * rand) * (1.0 - delta_1)**(self.config.eta_m + 1.0)
                            delta_q = val**mut_pow - 1.0
                        else:
                            val = 2.0 * (1.0 - rand) + 2.0 * (rand - 0.5) * (1.0 - delta_2)**(self.config.eta_m + 1.0)
                            delta_q = 1.0 - val**mut_pow
                            
                        y = y + delta_q * (ub - lb)
                        mutated[i, j] = np.clip(y, lb, ub)
        return mutated

    def run(self):
        pop = self._initialize_population()
        # Evaluate initial population
        objs = np.array([self.problem.evaluate_objectives(ind) for ind in pop])
        
        for gen in range(self.config.max_gen):
            # Create Offspring
            # Need ranks/dist for selection first
            fronts = self._fast_non_dominated_sort(objs)
            ranks = np.zeros(len(pop), dtype=int)
            dists = np.zeros(len(pop))
            
            for r, front in enumerate(fronts):
                if not front: continue
                ranks[front] = r
                d_front = self._crowding_distance_assignment(objs, front)
                # Map back to original indices
                for idx_in_front, idx_global in enumerate(front):
                    dists[idx_global] = d_front[idx_in_front]
            
            # Selection
            mating_pool = self._tournament_selection(pop, ranks, dists)
            
            # Crossover & Mutation
            offspring = self._sbx_crossover(mating_pool)
            offspring = self._polynomial_mutation(offspring)
            
            # Repair
            offspring = np.array([self.problem.repair_solution(ind) for ind in offspring])
            
            # Evaluate Offspring
            off_objs = np.array([self.problem.evaluate_objectives(ind) for ind in offspring])
            
            # Merge
            combined_pop = np.vstack([pop, offspring])
            combined_objs = np.vstack([objs, off_objs])
            
            # Non-dominated Sort Combined
            fronts = self._fast_non_dominated_sort(combined_objs)
            
            # Fill next population
            next_pop_idx = []
            for front in fronts:
                if len(next_pop_idx) + len(front) <= self.config.pop_size:
                    next_pop_idx.extend(front)
                else:
                    # Crowding Sort the last front
                    d_front = self._crowding_distance_assignment(combined_objs, front)
                    # Sort front by distance descending
                    # Note: Need to map local front indices to global combined indices
                    # d_front corresponds to indices in 'front' list
                    
                    # Create tuples (idx_in_combined, dist)
                    idx_dist = [(front[i], d_front[i]) for i in range(len(front))]
                    # Sort by dist descending
                    idx_dist.sort(key=lambda x: x[1], reverse=True)
                    
                    needed = self.config.pop_size - len(next_pop_idx)
                    next_pop_idx.extend([x[0] for x in idx_dist[:needed]])
                    break
            
            pop = combined_pop[next_pop_idx]
            objs = combined_objs[next_pop_idx]
            
            if (gen+1) % 10 == 0:
                print(f"Gen {gen+1}/{self.config.max_gen} Complete. Front 0 size: {len(fronts[0])}")
        
        # Return Pareto Front (Rank 0)
        fronts = self._fast_non_dominated_sort(objs)
        pareto_idx = fronts[0]
        return pop[pareto_idx], objs[pareto_idx]
