"""
baselines.py
Fast, approximate baseline solvers for initial solutions or comparison.

1. random_feasible: Generate N random positions, decode, repair, evaluate. Return best.
2. greedy_construct: Placeholder for domain-specific greedy construction.
"""
from __future__ import annotations

import numpy as np
from typing import Any, Tuple
from .problem import OptimizationProblem

def random_feasible(
    problem: OptimizationProblem, 
    n_samples: int = 100, 
    seed: int = 42
) -> Tuple[Any, float]:
    """
    Sample n random solutions, repair them, find the best.
    
    Args:
        problem: The optimization problem.
        problem.lb/ub must be set if using random position generation.
        n_samples: Number of samples.
        
    Returns:
        (best_solution, best_cost)
    """
    rng = np.random.default_rng(seed)
    
    # Check if we can generate random positions
    if problem.lb is None or problem.ub is None:
        # Fallback: cannot generate random without bounds
        # Try to rely on problem providing a method `sample_random_solution` if it exists
        # Or raise error. For our templates, lb/ub are set.
        raise ValueError("Problem must define lb/ub for random sampling.")
        
    dim = len(problem.lb)
    best_sol = None
    best_cost = float('inf')
    
    # Generate batch of random positions
    # Uniform sample in [lb, ub]
    # Handle int/float mismatch later via decoder
    for _ in range(n_samples):
        # Sample one by one to save memory if n_samples large? 
        # Or batch? Batch is faster for numpy but decoding usually 1-by-1.
        raw_pos = rng.uniform(problem.lb, problem.ub)
        
        # Decode & Repair & Eval
        # Check problem.evaluate_position logic
        # It calls decode -> evaluate_solution (which calls repair)
        # We can use that directly
        
        cost = problem.evaluate_position(raw_pos)
        
        if cost < best_cost:
            best_cost = cost
            # Re-decode to get solution object
            best_sol = problem.repair_solution(problem.decode(raw_pos))
            
    return best_sol, best_cost

def greedy_construct(problem: OptimizationProblem) -> Tuple[Any, float]:
    """
    Try to build a solution incrementally.
    This is usually domain specific.
    Currently falls back to random_feasible(n=10) if no specific greedy hook found.
    """
    # If problem has a `greedy_init` method, use it
    if hasattr(problem, "greedy_init"):
       sol = getattr(problem, "greedy_init")()
       cost = problem.evaluate_solution(sol)
       return sol, cost
       
    # Fallback
    return random_feasible(problem, n_samples=10)
