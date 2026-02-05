def feasible_within_T(total_mass_ton: float,
                      T_years: float,
                      C_elevator_tpy: float,
                      C_rocket_tpy: float) -> bool:
    """
    Check if combined capacity can meet the deadline T.
    Condition: (C_E + C_R) * T >= M
    """
    total_capacity = C_elevator_tpy + C_rocket_tpy
    return (total_capacity * T_years) >= total_mass_ton

def lower_bound_time_years(total_mass_ton: float,
                           C_elevator_tpy: float,
                           C_rocket_tpy: float) -> float:
    """
    Minimum time required with both systems running at full capacity.
    T_min = M / (C_E + C_R)
    """
    total_capacity = C_elevator_tpy + C_rocket_tpy
    if total_capacity <= 0:
        return float('inf')
    return total_mass_ton / total_capacity

def alpha_star(C_elevator_tpy: float, C_rocket_tpy: float) -> float:
    """
    Optimal mass split fraction for elevator (alpha) to minimize time.
    Under full utilization assumption: alpha = C_E / (C_E + C_R)
    This ensures both systems finish at the same time T_min.
    """
    total_capacity = C_elevator_tpy + C_rocket_tpy
    if total_capacity <= 0:
        return 0.0
    return C_elevator_tpy / total_capacity
