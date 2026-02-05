from typing import Dict, Tuple, List

def interval_time_A(total_mass_ton: float, C_elevator_tpy: float, delta: float) -> Tuple[float, float]:
    """
    Calculate time interval for Scenario A given uncertainty delta in capacity.
    Capacity range: [C * (1-delta), C * (1+delta)]
    """
    c_min = C_elevator_tpy * (1 - delta)
    c_max = C_elevator_tpy * (1 + delta)
    
    t_max = total_mass_ton / c_min if c_min > 0 else float('inf')
    t_min = total_mass_ton / c_max
    return (t_min, t_max)

def interval_time_B(total_mass_ton: float, 
                    K_range: Tuple[int, int],
                    r_set: Tuple[int, ...], 
                    q_range: Tuple[float, float]) -> Dict[str, float]:
    """
    Calculate best and worst case times for Scenario B.
    """
    # Worst case: Min K, Min r, Min q
    # Best case: Max K, Max r, Max q
    
    k_min, k_max = min(K_range), max(K_range)
    r_min, r_max = min(r_set), max(r_set)
    q_min, q_max = min(q_range), max(q_range)
    
    cap_min = k_min * r_min * 365 * q_min
    cap_max = k_max * r_max * 365 * q_max
    
    t_worst = total_mass_ton / cap_min if cap_min > 0 else float('inf')
    t_best = total_mass_ton / cap_max
    
    return {
        "best_time_years": t_best,
        "worst_time_years": t_worst,
        "cap_min_tpy": cap_min,
        "cap_max_tpy": cap_max
    }

def interval_time_C_lower_bound(total_mass_ton: float, 
                                C_elevator_tpy: float,
                                K_range: Tuple[int, int], 
                                r_set: Tuple[int, ...], 
                                q_range: Tuple[float, float]) -> Dict[str, float]:
    """
    Calculate best and worst case times for Scenario C (Hybrid).
    Using fixed Elevator capacity (or could add delta), and Rocket intervals.
    """
    res_b = interval_time_B(total_mass_ton, K_range, r_set, q_range)
    
    c_r_min = res_b["cap_min_tpy"]
    c_r_max = res_b["cap_max_tpy"]
    
    t_worst = total_mass_ton / (C_elevator_tpy + c_r_min)
    t_best = total_mass_ton / (C_elevator_tpy + c_r_max)
    
    return {
        "hybrid_best_time_years": t_best,
        "hybrid_worst_time_years": t_worst
    }
