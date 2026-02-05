"""
Q1 Cost Model Implementation.
Handles learning curves and interval arithmetic for cost estimation.
"""

import math
from typing import Tuple

def rocket_cost_per_launch(
    year: int,
    C0_usd: float,
    start_year: int,
    decay_rate: float,
    period_yr: int,
    floor_usd: float
) -> float:
    """
    Calculate cost per launch for a specific year using a step-wise learning curve.
    Formula: C(y) = max(Floor, C0 * (1 - rho)^floor((y - Y0)/period))
    """
    if year < start_year:
        return C0_usd

    elapsed_years = year - start_year
    steps = elapsed_years // period_yr

    decay_factor = (1.0 - decay_rate) ** steps
    current_cost = C0_usd * decay_factor

    return max(current_cost, floor_usd)

def total_rocket_cost_over_schedule(
    n_launches_required: int,
    launches_per_year: int,
    start_year: int,
    C0_usd: float,
    decay_rate: float,
    period_yr: int,
    floor_usd: float
) -> float:
    """
    Calculate total cost by summing annual costs, accounting for cost decay over time.
    """
    total_cost = 0.0
    launches_remaining = n_launches_required
    current_year = start_year

    while launches_remaining > 0:
        launches_this_year = min(launches_remaining, launches_per_year)
        cost_this_year = rocket_cost_per_launch(
            current_year, C0_usd, start_year, decay_rate, period_yr, floor_usd
        )

        total_cost += launches_this_year * cost_this_year

        launches_remaining -= launches_this_year
        current_year += 1

    return total_cost
