import pandas as pd
import numpy as np
import math
from configs.constants import Problem, Elevator, Rocket, Cost
from src.q1.capacity import (
    elevator_total_capacity_tpy,
    rocket_annual_capacity_tpy,
    rocket_launches_required,
    completion_time_years
)
from src.q1.feasibility import lower_bound_time_years, alpha_star
from src.q1.cost_model import total_rocket_cost_over_schedule, rocket_cost_per_launch

def build_q1_baseline_table() -> pd.DataFrame:
    """
    Generate the baseline comparison table for Scenarios A, B, and C.
    Now includes interval cost calculations.
    """
    rows = []

    # Common Cost Parameters
    c0_low = Cost.ROCKET_LAUNCH_COST_2050_RANGE_USD[0]
    c0_high = Cost.ROCKET_LAUNCH_COST_2050_RANGE_USD[1]
    decay = Cost.ROCKET_COST_DECAY_RATE_PER_5YR
    period = Cost.ROCKET_COST_DECAY_PERIOD_YR
    floor = Cost.ROCKET_COST_FLOOR_USD

    elev_opex_low = Cost.ELEVATOR_OPEX_PER_KG_RANGE_USD[0] * 1000.0 # to ton
    elev_opex_high = Cost.ELEVATOR_OPEX_PER_KG_RANGE_USD[1] * 1000.0 # to ton

    beta_low = Cost.BETA_APEX_RANGE[0]
    beta_high = Cost.BETA_APEX_RANGE[1]

    # --- Scenario A: Elevator Only ---
    cap_a = elevator_total_capacity_tpy(Elevator.NUM_HARBOURS, Elevator.CAPACITY_PER_HARBOUR_TPY)
    time_a = completion_time_years(Problem.TOTAL_MASS_TONS, cap_a)

    # Cost A: Elevator OPEX (Low/High) + Apex Transfer (Low/High)
    # Apex Transfer: Requires rockets from Apex.
    # Assume Apex launches follow same decay logic, but with beta discount.
    # Annual Apex launches approx = capacity / q_rocket?
    # Or just total mass / q_rocket? Let's use total mass.
    # We assume q for Apex transfer is same as Earth launch (conservative).
    q_apex = Rocket.PAYLOAD_RANGE_TON[1] # Optimistic payload for Apex
    n_apex_launches = rocket_launches_required(Problem.TOTAL_MASS_TONS, q_apex)
    launches_per_year_apex = math.ceil(cap_a / q_apex) # Limited by elevator throughput

    # 1. Elevator OPEX Total
    cost_a_opex_low = Problem.TOTAL_MASS_TONS * elev_opex_low
    cost_a_opex_high = Problem.TOTAL_MASS_TONS * elev_opex_high

    # 2. Apex Transfer Total (using rocket cost model * beta)
    raw_rocket_cost_low = total_rocket_cost_over_schedule(n_apex_launches, launches_per_year_apex, Problem.START_YEAR, c0_low, decay, period, floor)
    raw_rocket_cost_high = total_rocket_cost_over_schedule(n_apex_launches, launches_per_year_apex, Problem.START_YEAR, c0_high, decay, period, floor)

    cost_a_apex_low = raw_rocket_cost_low * beta_low
    cost_a_apex_high = raw_rocket_cost_high * beta_high

    rows.append({
        "scenario": "A_elevator_only",
        "K_sites": 0,
        "r_daily": 0,
        "payload_ton": 0,
        "annual_capacity_tpy": cap_a,
        "launches_required": 0, # Earth launches
        "time_years": time_a,
        "finish_year": Problem.START_YEAR + time_a,
        "cost_low_usd": cost_a_opex_low + cost_a_apex_low,
        "cost_high_usd": cost_a_opex_high + cost_a_apex_high,
        "cost_note": f"ElevOPEX + ApexTransfer(beta={beta_low}-{beta_high})"
    })

    # --- Scenario B: Rocket Only ---
    # Combinations: K=10, r in {1, 2}, q in {100, 150}
    K = Rocket.MAX_SITES
    for r in Rocket.DAILY_RATE_SET:
        for q in Rocket.PAYLOAD_RANGE_TON:
            cap_b = rocket_annual_capacity_tpy(K, r, q)
            launches = rocket_launches_required(Problem.TOTAL_MASS_TONS, q)
            time_b = completion_time_years(Problem.TOTAL_MASS_TONS, cap_b)

            # Cost B: Traditional Rocket
            launches_per_year = 365 * K * r
            cost_b_low = total_rocket_cost_over_schedule(launches, launches_per_year, Problem.START_YEAR, c0_low, decay, period, floor)
            cost_b_high = total_rocket_cost_over_schedule(launches, launches_per_year, Problem.START_YEAR, c0_high, decay, period, floor)

            rows.append({
                "scenario": "B_rocket_only",
                "K_sites": K,
                "r_daily": r,
                "payload_ton": q,
                "annual_capacity_tpy": cap_b,
                "launches_required": launches,
                "time_years": time_b,
                "finish_year": Problem.START_YEAR + time_b,
                "cost_low_usd": cost_b_low,
                "cost_high_usd": cost_b_high,
                "cost_note": f"Rocket(C0={c0_low/1e6}M-{c0_high/1e6}M)"
            })

    # --- Scenario C: Hybrid (Configs) ---
    # User requested: Optimal C, plus C(r=1,q=100) and C(r=2,q=150)

    # 1. Optimal C (as before, uses max capacity rocket)
    r_best = max(Rocket.DAILY_RATE_SET)
    q_best = max(Rocket.PAYLOAD_RANGE_TON)
    cap_r_best = rocket_annual_capacity_tpy(K, r_best, q_best)

    time_c_min = lower_bound_time_years(Problem.TOTAL_MASS_TONS, cap_a, cap_r_best)
    alpha_opt = alpha_star(cap_a, cap_r_best)

    # Cost C Optimal
    mass_elev_opt = Problem.TOTAL_MASS_TONS * alpha_opt
    mass_rock_opt = Problem.TOTAL_MASS_TONS * (1 - alpha_opt)

    cost_c_elev_opex_low = mass_elev_opt * elev_opex_low
    cost_c_elev_opex_high = mass_elev_opt * elev_opex_high

    n_launches_apex_c = rocket_launches_required(mass_elev_opt, q_best)
    launches_per_year_apex_c = math.ceil(n_launches_apex_c / time_c_min)
    raw_apex_cost_c_low = total_rocket_cost_over_schedule(n_launches_apex_c, launches_per_year_apex_c, Problem.START_YEAR, c0_low, decay, period, floor)
    raw_apex_cost_c_high = total_rocket_cost_over_schedule(n_launches_apex_c, launches_per_year_apex_c, Problem.START_YEAR, c0_high, decay, period, floor)

    n_launches_rock_c = rocket_launches_required(mass_rock_opt, q_best)
    launches_per_year_rock_c = math.ceil(n_launches_rock_c / time_c_min)
    cost_rock_c_low = total_rocket_cost_over_schedule(n_launches_rock_c, launches_per_year_rock_c, Problem.START_YEAR, c0_low, decay, period, floor)
    cost_rock_c_high = total_rocket_cost_over_schedule(n_launches_rock_c, launches_per_year_rock_c, Problem.START_YEAR, c0_high, decay, period, floor)

    cost_c_low = cost_c_elev_opex_low + (raw_apex_cost_c_low * beta_low) + cost_rock_c_low
    cost_c_high = cost_c_elev_opex_high + (raw_apex_cost_c_high * beta_high) + cost_rock_c_high

    rows.append({
        "scenario": "C_hybrid_optimal",
        "K_sites": K,
        "r_daily": r_best,
        "payload_ton": q_best,
        "annual_capacity_tpy": cap_a + cap_r_best,
        "launches_required": n_launches_rock_c,
        "time_years": time_c_min,
        "finish_year": Problem.START_YEAR + time_c_min,
        "cost_low_usd": cost_c_low,
        "cost_high_usd": cost_c_high,
        "cost_note": f"Alpha={alpha_opt:.3f}, Parallel (Optimal)"
    })

    # 2. Specific C Configs: (r=1, q=100) and (r=2, q=150)
    c_configs = [(1, 100.0), (2, 150.0)]

    for r_c, q_c in c_configs:
        cap_r_c = rocket_annual_capacity_tpy(K, r_c, q_c)

        # Calculate time and alpha for this specific config
        time_c_spec = lower_bound_time_years(Problem.TOTAL_MASS_TONS, cap_a, cap_r_c)
        alpha_spec = alpha_star(cap_a, cap_r_c)

        # Cost C Specific
        mass_elev_spec = Problem.TOTAL_MASS_TONS * alpha_spec
        mass_rock_spec = Problem.TOTAL_MASS_TONS * (1 - alpha_spec)

        cost_c_elev_opex_low_s = mass_elev_spec * elev_opex_low
        cost_c_elev_opex_high_s = mass_elev_spec * elev_opex_high

        n_launches_apex_c_s = rocket_launches_required(mass_elev_spec, q_c) # Use q_c for Apex too
        launches_per_year_apex_c_s = math.ceil(n_launches_apex_c_s / time_c_spec)
        raw_apex_cost_c_low_s = total_rocket_cost_over_schedule(n_launches_apex_c_s, launches_per_year_apex_c_s, Problem.START_YEAR, c0_low, decay, period, floor)
        raw_apex_cost_c_high_s = total_rocket_cost_over_schedule(n_launches_apex_c_s, launches_per_year_apex_c_s, Problem.START_YEAR, c0_high, decay, period, floor)

        n_launches_rock_c_s = rocket_launches_required(mass_rock_spec, q_c)
        launches_per_year_rock_c_s = math.ceil(n_launches_rock_c_s / time_c_spec)
        cost_rock_c_low_s = total_rocket_cost_over_schedule(n_launches_rock_c_s, launches_per_year_rock_c_s, Problem.START_YEAR, c0_low, decay, period, floor)
        cost_rock_c_high_s = total_rocket_cost_over_schedule(n_launches_rock_c_s, launches_per_year_rock_c_s, Problem.START_YEAR, c0_high, decay, period, floor)

        cost_c_low_s = cost_c_elev_opex_low_s + (raw_apex_cost_c_low_s * beta_low) + cost_rock_c_low_s
        cost_c_high_s = cost_c_elev_opex_high_s + (raw_apex_cost_c_high_s * beta_high) + cost_rock_c_high_s

        rows.append({
            "scenario": "C_hybrid",
            "K_sites": K,
            "r_daily": r_c,
            "payload_ton": q_c,
            "annual_capacity_tpy": cap_a + cap_r_c,
            "launches_required": n_launches_rock_c_s,
            "time_years": time_c_spec,
            "finish_year": Problem.START_YEAR + time_c_spec,
            "cost_low_usd": cost_c_low_s,
            "cost_high_usd": cost_c_high_s,
            "cost_note": f"Alpha={alpha_spec:.3f}, Parallel (r={r_c}, q={q_c})"
        })

    return pd.DataFrame(rows)
