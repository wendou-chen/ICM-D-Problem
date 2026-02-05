import os
import sys
import pandas as pd
import numpy as np
import json
import math

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from configs.constants import Problem, Elevator, Rocket, Cost
from src.q1.baseline import build_q1_baseline_table
from src.q1.robustness_interval import interval_time_A, interval_time_B, interval_time_C_lower_bound
from src.q1.feasibility import alpha_star
from src.q1.plots import plot_cumulative_mass, plot_pareto_cost_time_band
from src.q1.capacity import elevator_total_capacity_tpy, rocket_annual_capacity_tpy, rocket_launches_required
from src.q1.cost_model import total_rocket_cost_over_schedule

def generate_alpha_scan_table() -> pd.DataFrame:
    """
    Generate data for Scenario C across alpha 0..1
    Returns DataFrame with [alpha, time_years, cost_low_usd, cost_high_usd]
    """
    # Params
    K = Rocket.MAX_SITES
    r = 2 # Best case rocket
    q = 150.0 # Best case rocket

    cap_elev = elevator_total_capacity_tpy(Elevator.NUM_HARBOURS, Elevator.CAPACITY_PER_HARBOUR_TPY)
    cap_rock = rocket_annual_capacity_tpy(K, r, q)

    c0_low = Cost.ROCKET_LAUNCH_COST_2050_RANGE_USD[0]
    c0_high = Cost.ROCKET_LAUNCH_COST_2050_RANGE_USD[1]
    decay = Cost.ROCKET_COST_DECAY_RATE_PER_5YR
    period = Cost.ROCKET_COST_DECAY_PERIOD_YR
    floor = Cost.ROCKET_COST_FLOOR_USD

    elev_opex_low = Cost.ELEVATOR_OPEX_PER_KG_RANGE_USD[0] * 1000.0
    elev_opex_high = Cost.ELEVATOR_OPEX_PER_KG_RANGE_USD[1] * 1000.0

    beta_low = Cost.BETA_APEX_RANGE[0]
    beta_high = Cost.BETA_APEX_RANGE[1]

    # Calculate exact optimal alpha to ensure we hit the true minimum time
    # This resolves discrepancy between discrete scan min and analytical min
    alpha_opt_exact = alpha_star(cap_elev, cap_rock)

    alphas = np.linspace(0, 1, 101)
    # Insert the exact optimal alpha into the scan array
    alphas = np.sort(np.unique(np.append(alphas, alpha_opt_exact)))

    rows = []

    for alpha in alphas:
        # Time
        # Parallel: max(Time_E, Time_R)
        mass_e = Problem.TOTAL_MASS_TONS * alpha
        mass_r = Problem.TOTAL_MASS_TONS * (1 - alpha)

        # Avoid div by zero
        time_e = mass_e / cap_elev if cap_elev > 0 else 9999
        time_r = mass_r / cap_rock if cap_rock > 0 else 9999

        # Scenario C logic: Parallel execution
        time_years = max(time_e, time_r)
        if time_years == 0: time_years = 0.01 # avoid zero

        # Cost
        # 1. Elevator Cost
        c_e_low = mass_e * elev_opex_low
        c_e_high = mass_e * elev_opex_high

        # 2. Apex Cost (Rocket for E-mass)
        n_apex = rocket_launches_required(mass_e, q)
        lpy_apex = math.ceil(n_apex / time_years)
        raw_apex_low = total_rocket_cost_over_schedule(n_apex, lpy_apex, Problem.START_YEAR, c0_low, decay, period, floor)
        raw_apex_high = total_rocket_cost_over_schedule(n_apex, lpy_apex, Problem.START_YEAR, c0_high, decay, period, floor)

        # 3. Rocket Cost (R-mass)
        n_rock = rocket_launches_required(mass_r, q)
        lpy_rock = math.ceil(n_rock / time_years)
        raw_rock_low = total_rocket_cost_over_schedule(n_rock, lpy_rock, Problem.START_YEAR, c0_low, decay, period, floor)
        raw_rock_high = total_rocket_cost_over_schedule(n_rock, lpy_rock, Problem.START_YEAR, c0_high, decay, period, floor)

        total_low = c_e_low + (raw_apex_low * beta_low) + raw_rock_low
        total_high = c_e_high + (raw_apex_high * beta_high) + raw_rock_high

        rows.append({
            "alpha": alpha,
            "time_years": time_years,
            "cost_low_usd": total_low,
            "cost_high_usd": total_high
        })

    return pd.DataFrame(rows)

def main():
    print("=== Running Q1 Analysis Pipeline (Final Cost Model) ===")

    out_dir_csv = os.path.join("outputs", "q1")
    os.makedirs(out_dir_csv, exist_ok=True)

    # 1. Generate Baseline Table
    print("[1/5] Generating Baseline Table...")
    df_baseline = build_q1_baseline_table()

    csv_path = os.path.join(out_dir_csv, "q1_baseline.csv")
    df_baseline.to_csv(csv_path, index=False)
    print(f"      Saved: {csv_path}")
    # Print a nice summary
    summary_cols = ["scenario", "time_years", "cost_low_usd", "cost_high_usd"]
    print(df_baseline[summary_cols].to_string())

    # 2. Generate Interval Robustness
    print("\n[2/5] Calculating Interval Robustness...")
    cap_a = elevator_total_capacity_tpy(Elevator.NUM_HARBOURS, Elevator.CAPACITY_PER_HARBOUR_TPY)
    res_a = interval_time_A(Problem.TOTAL_MASS_TONS, cap_a, delta=0.1)
    res_b = interval_time_B(
        Problem.TOTAL_MASS_TONS,
        K_range=(5, 10),
        r_set=(1, 2),
        q_range=(100.0, 150.0)
    )
    res_c = interval_time_C_lower_bound(
        Problem.TOTAL_MASS_TONS,
        cap_a,
        K_range=(5, 10),
        r_set=(1, 2),
        q_range=(100.0, 150.0)
    )

    robustness_data = {
        "Scenario_A_delta_10pct": {"time_range_years": res_a},
        "Scenario_B_interval": res_b,
        "Scenario_C_interval": res_c
    }
    json_path = os.path.join(out_dir_csv, "q1_interval.json")
    with open(json_path, "w") as f:
        json.dump(robustness_data, f, indent=2)
    print(f"      Saved: {json_path}")

    # 3. Generate Alpha Scan (Trade-off)
    print("\n[3/5] Generating Alpha Scan (Cost-Time Trade-off)...")
    df_scan = generate_alpha_scan_table()
    scan_path = os.path.join(out_dir_csv, "q1_tradeoff_alpha.csv")
    df_scan.to_csv(scan_path, index=False)
    print(f"      Saved: {scan_path}")

    # 4. Generate Plots
    print("\n[4/5] Generating Plots...")
    out_dir_figs = os.path.join(out_dir_csv, "figs")

    # Plot 1: Cumulative Mass
    plot_cumulative_mass(df_baseline, out_dir_figs)

    # Plot 2: Cost-Time Band
    # We used r=2, q=150 in generate_alpha_scan_table (lines 25-26)
    plot_pareto_cost_time_band(df_scan, out_dir_figs, r_val=2, q_val=150.0)

    print(f"      Saved figures to: {out_dir_figs}")

    print("\n[5/5] Pipeline Complete.")

if __name__ == "__main__":
    main()
