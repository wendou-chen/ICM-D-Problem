"""
operators.py
Heuristic Operator Zoo: A functional-style collection of mutation/neighbor operators.

Interface:
    op(solution, rng, **kwargs) -> new_solution

Categories:
    1. Binary (flip)
    2. Integer (step, redistribute)
    3. Permutation (swap, insert, 2-opt)
    4. Continuous (gaussian)
    5. LNS (destroy/repair)
"""
from __future__ import annotations
import numpy as np
from typing import Any, Callable, List, Dict, Optional

Solution = Any
RNG = np.random.Generator

# -----------------------------------------------------------
# Binary Operators (0/1 Vectors)
# -----------------------------------------------------------

def op_binary_flip_1(sol: np.ndarray, rng: RNG) -> np.ndarray:
    """Flip exactly one bit."""
    y = sol.copy()
    idx = rng.integers(0, len(y))
    y[idx] = 1 - y[idx]
    return y

def op_binary_flip_k(sol: np.ndarray, rng: RNG, k: int = 2) -> np.ndarray:
    """Flip k bits (randomly selected)."""
    y = sol.copy()
    n = len(y)
    if k >= n:
        return 1 - y
    indices = rng.choice(n, size=k, replace=False)
    y[indices] = 1 - y[indices]
    return y

def op_binary_swap_2(sol: np.ndarray, rng: RNG) -> np.ndarray:
    """Swap values of two random indices (preserves sum)."""
    y = sol.copy()
    n = len(y)
    if n < 2: return y
    i, j = rng.choice(n, size=2, replace=False)
    y[i], y[j] = y[j], y[i]
    return y

# -----------------------------------------------------------
# Integer Operators (Bounded Integers)
# -----------------------------------------------------------

def op_int_plus_minus_1(sol: np.ndarray, rng: RNG, lb: np.ndarray, ub: np.ndarray) -> np.ndarray:
    """Randomly increment or decrement one variable, respecting bounds."""
    y = sol.copy()
    idx = rng.integers(0, len(y))
    delta = rng.choice([-1, 1])
    val = y[idx] + delta
    # Check bounds
    if lb[idx] <= val <= ub[idx]:
        y[idx] = val
    return y

def op_int_redistribute(sol: np.ndarray, rng: RNG, lb: np.ndarray, ub: np.ndarray, amount: int = 1) -> np.ndarray:
    """Move 'amount' from one variable to another (preserves sum)."""
    y = sol.copy()
    n = len(y)
    if n < 2: return y
    
    # Try multiple times to find valid move
    for _ in range(5):
        i, j = rng.choice(n, size=2, replace=False)
        # Attempt move i -> j
        if y[i] - amount >= lb[i] and y[j] + amount <= ub[j]:
            y[i] -= amount
            y[j] += amount
            break
    return y

# -----------------------------------------------------------
# Permutation Operators (Sequence)
# -----------------------------------------------------------

def op_perm_swap(sol: np.ndarray, rng: RNG) -> np.ndarray:
    """Swap two elements."""
    y = sol.copy()
    n = len(y)
    if n < 2: return y
    i, j = rng.choice(n, size=2, replace=False)
    y[i], y[j] = y[j], y[i]
    return y

def op_perm_insert(sol: np.ndarray, rng: RNG) -> np.ndarray:
    """Remove element at i and insert at j."""
    y = list(sol)
    n = len(y)
    if n < 2: return np.array(y)
    i = rng.integers(0, n)
    val = y.pop(i)
    j = rng.integers(0, n) # n-1 existing + 1 new position
    y.insert(j, val)
    return np.array(y)

def op_perm_2opt(sol: np.ndarray, rng: RNG) -> np.ndarray:
    """Reverse a sub-segment."""
    y = sol.copy()
    n = len(y)
    if n < 3: return y
    i, j = sorted(rng.choice(n, size=2, replace=False))
    # Reverse slice [i:j+1]
    y[i:j+1] = y[i:j+1][::-1]
    return y

# -----------------------------------------------------------
# Continuous Operators
# -----------------------------------------------------------

def op_cont_gaussian(sol: np.ndarray, rng: RNG, scale: float = 0.1, lb: Optional[np.ndarray] = None, ub: Optional[np.ndarray] = None) -> np.ndarray:
    """Add Gaussian noise."""
    noise = rng.normal(0, scale, size=sol.shape)
    y = sol + noise
    if lb is not None and ub is not None:
        y = np.clip(y, lb, ub)
    return y

# -----------------------------------------------------------
# LNS Operators (Destroy & Repair)
# -----------------------------------------------------------

def op_lns_destroy_random(sol: np.ndarray, rng: RNG, ratio: float = 0.2, null_val: Any = 0) -> Tuple[np.ndarray, np.ndarray]:
    """
    Randomly 'destroy' ratio of the solution variables (set to null_val).
    Returns (partial_solution, mask_of_destroyed_indices).
    """
    y = sol.copy()
    n = len(y)
    k = max(1, int(n * ratio))
    indices = rng.choice(n, size=k, replace=False)
    y[indices] = null_val
    return y, indices

# Greedy repair usually requires the problem context (cost function), 
# so it's typically a method on the Problem or a closure, not a pure generic operator.
