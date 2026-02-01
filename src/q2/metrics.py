import numpy as np
from typing import List, Dict, Tuple

def var_cvar(data: List[float], alpha: float = 0.95) -> Tuple[float, float]:
    """
    Calculate Value at Risk (VaR) and Conditional Value at Risk (CVaR).
    For completion time (bad), we usually look at the upper tail.
    VaR_95 is the 95th percentile.
    CVaR_95 is the mean of values > VaR_95.
    """
    if not data:
        return 0.0, 0.0
        
    arr = np.array(sorted(data))
    n = len(arr)
    index = int(alpha * n)
    if index >= n:
        index = n - 1
        
    var_val = arr[index]
    
    # CVaR is average of values >= VaR (approx)
    tail = arr[index:]
    if len(tail) > 0:
        cvar_val = np.mean(tail)
    else:
        cvar_val = var_val
        
    return var_val, cvar_val

def p_on_time(data: List[float], target_year: float) -> float:
    """
    Calculate probability of completing on or before target_year.
    """
    if not data:
        return 0.0
    count = sum(1 for x in data if x <= target_year)
    return count / len(data)
