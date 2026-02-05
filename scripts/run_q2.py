import sys
import os
import pandas as pd
import numpy as np
from tqdm import tqdm

# Ensure project root is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from configs.constants import (
    Problem, Elevator, Rocket, RELIABILITY_PRESETS, ReliabilityPreset
)
from src.q2 import analytics, simulator, metrics, plots

OUTPUT_DIR = "outputs/q2"
FIG_DIR = os.path.join(OUTPUT_DIR, "figs")
os.makedirs(FIG_DIR, exist_ok=True)

def run_analytic_study():
    print("Running Analytical Study...")
    results = []
    
    # 1. Effect of Reliability Presets on Capacity & Alpha
    C_E_nominal = Elevator.NUM_HARBOURS * Elevator.CAPACITY_PER_HARBOUR_TPY
    K = Rocket.MAX_SITES
    q = (Rocket.PAYLOAD_RANGE_TON[0] + Rocket.PAYLOAD_RANGE_TON[1]) / 2.0
    r = Rocket.DAILY_RATE_SET[0] # Base rate
    
    for name, preset in RELIABILITY_PRESETS.items():
        c_e = analytics.elevator_effective_capacity(C_E_nominal, preset.A_E)
        c_r = analytics.rocket_effective_capacity(
            K, r, q, preset.A_B, preset.P_R, preset.TAU_RESET_DAYS
        )
        alpha = analytics.alpha_star(c_e, c_r)
        
        # Expected Time
        t_exp = Problem.TOTAL_MASS_TONS / (c_e + c_r) if (c_e + c_r) > 0 else float('inf')
        
        results.append({
            'Preset': name,
            'A_E': preset.A_E,
            'P_R': preset.P_R,
            'C_E_eff': c_e,
            'C_R_eff': c_r,
            'Alpha_Star': alpha,
            'Expected_Time_Years': t_exp
        })
        
    df = pd.DataFrame(results)
    df.to_csv(os.path.join(OUTPUT_DIR, "q2_analytic.csv"), index=False)
    print("Saved q2_analytic.csv")
    
    # 2. Alpha Drift Data
    drift_data = []
    base_preset = RELIABILITY_PRESETS['MODERATE']
    for ae in np.linspace(0.5, 1.0, 20):
        c_e = analytics.elevator_effective_capacity(C_E_nominal, ae)
        c_r = analytics.rocket_effective_capacity(
            K, r, q, base_preset.A_B, base_preset.P_R, base_preset.TAU_RESET_DAYS
        )
        alpha = analytics.alpha_star(c_e, c_r)
        drift_data.append({'A_E': ae, 'alpha_star': alpha})
        
    drift_df = pd.DataFrame(drift_data)
    drift_out_path = os.path.join(OUTPUT_DIR, "data", "alpha_drift.csv")
    os.makedirs(os.path.dirname(drift_out_path), exist_ok=True)
    drift_df.to_csv(drift_out_path, index=False)
    
    plots.plot_alpha_drift(drift_data, 'A_E', os.path.join(FIG_DIR, "alpha_drift.png"))
    
    # 3. Feasibility Region Plot
    ce_range = np.linspace(0, 3_000_000, 100)
    cr_range = np.linspace(0, 6_000_000, 100)

    sys_points = []
    colors = {'MILD': '#4caf50', 'MODERATE': '#ff9800', 'SEVERE': '#f44336'}
    for res in results:
        name = res['Preset']
        sys_points.append({
            'label': name,
            'C_E': res['C_E_eff'],
            'C_R': res['C_R_eff'],
            'color': colors.get(name, 'blue'),
            'marker': 'o'
        })

    plots.plot_feasibility_region(
        ce_range, cr_range, Problem.TOTAL_MASS_TONS, 100.0, sys_points,
        os.path.join(FIG_DIR, "feasibility_region.png")
    )

def run_gamma_scan(n_iter=100):
    print("Running Gamma Scan Study...")

    C_E_nominal = Elevator.NUM_HARBOURS * Elevator.CAPACITY_PER_HARBOUR_TPY
    rocket_config = {
        'K': Rocket.MAX_SITES,
        'q': (Rocket.PAYLOAD_RANGE_TON[0] + Rocket.PAYLOAD_RANGE_TON[1]) / 2.0,
        'r_base': Rocket.R_BASE,
        'r_max': Rocket.R_MAX
    }
    M = Problem.TOTAL_MASS_TONS
    # horizons = [100, 120, 140, 160, 180] # No longer needed for prob plot

    results_var = []

    for preset_name, preset in RELIABILITY_PRESETS.items():
        print(f"  Scanning Gamma for {preset_name}...")
        for gamma in Rocket.GAMMA_SET:
            times = []
            for _ in range(n_iter):
                t = simulator.simulate_once(
                    'dynamic_backup', M, preset, C_E_nominal, rocket_config, gamma=gamma
                )
                times.append(t)

            mean_t = np.mean(times)
            var95, _ = metrics.var_cvar(times, 0.95)

            results_var.append({
                'scenario_level': preset_name,
                'gamma': gamma,
                'Mean_Time': mean_t,
                'VaR_95': var95
            })

    df_var = pd.DataFrame(results_var)

    df_var.to_csv(os.path.join(OUTPUT_DIR, "q2_gamma_scan_var.csv"), index=False)
    print("Saved q2_gamma_scan_var.csv")

    plots.plot_gamma_scan(
        df_var,
        os.path.join(FIG_DIR, "gamma_scan_var.png")
    )

def run_simulation_study(n_iter=100):
    print(f"Running Monte Carlo Simulation (N={n_iter})...")

    C_E_nominal = Elevator.NUM_HARBOURS * Elevator.CAPACITY_PER_HARBOUR_TPY
    rocket_config = {
        'K': Rocket.MAX_SITES,
        'q': (Rocket.PAYLOAD_RANGE_TON[0] + Rocket.PAYLOAD_RANGE_TON[1]) / 2.0,
        'r_base': Rocket.R_BASE,
        'r_max': Rocket.R_MAX
    }
    M = Problem.TOTAL_MASS_TONS

    scenarios = []
    for preset_name in ['MILD', 'MODERATE', 'SEVERE']:
        preset = RELIABILITY_PRESETS[preset_name]
        for policy in ['fixed_alpha_star', 'dynamic_backup']:
            scenarios.append((preset_name, preset, policy))

    summary_results = []
    raw_times_map = {}

    for name, preset, policy in scenarios:
        scenario_label = f"{name}_{policy}"
        print(f"  Simulating {scenario_label}...")

        times = []
        for _ in tqdm(range(n_iter), desc="Sims", leave=False):
            eff_gamma = 2.0 if policy == 'dynamic_backup' else 1.0
            t = simulator.simulate_once(policy, M, preset, C_E_nominal, rocket_config, gamma=eff_gamma)
            times.append(t)

        raw_times_map[scenario_label] = times

        mean_t = np.mean(times)
        std_t = np.std(times)
        var95, cvar95 = metrics.var_cvar(times, 0.95)
        p_20yr = metrics.p_on_time(times, 20.0)
        p_25yr = metrics.p_on_time(times, 25.0)

        summary_results.append({
            'Scenario': scenario_label,
            'Preset': name,
            'Policy': policy,
            'Mean_Time': mean_t,
            'Std_Time': std_t,
            'VaR_95': var95,
            'CVaR_95': cvar95,
            'P_Success_20yr': p_20yr,
            'P_Success_25yr': p_25yr
        })

    df = pd.DataFrame(summary_results)
    df.to_csv(os.path.join(OUTPUT_DIR, "q2_mc_summary.csv"), index=False)
    print("Saved q2_mc_summary.csv")
    # Save raw simulation data for boxplots (Wide format)
    raw_df = pd.DataFrame(raw_times_map)
    raw_data_path = os.path.join(OUTPUT_DIR, "data", "boxplot_raw_data.csv")
    os.makedirs(os.path.dirname(raw_data_path), exist_ok=True)
    raw_df.to_csv(raw_data_path, index=False)
    print(f"Saved raw simulation data to {raw_data_path}")

    plots.plot_boxplot_time(raw_times_map, os.path.join(FIG_DIR, "boxplot_time.png"))

if __name__ == "__main__":
    run_analytic_study()
    run_simulation_study(n_iter=100)
    run_gamma_scan(n_iter=100)
    print("Q2 Pipeline Completed.")
