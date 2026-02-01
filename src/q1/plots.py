import pandas as pd
import matplotlib.pyplot as plt
import os
import numpy as np
from configs.constants import Problem, Elevator, Rocket
from src.q1.capacity import elevator_total_capacity_tpy, rocket_annual_capacity_tpy

def plot_cumulative_mass(df_baseline: pd.DataFrame, out_dir: str) -> None:
    """
    Plot Cumulative Mass Delivered over Time for selected scenarios.
    """
    os.makedirs(out_dir, exist_ok=True)
    plt.figure(figsize=(10, 6))
    
    target_mass = Problem.TOTAL_MASS_TONS # 100M tons
    
    # Filter scenarios to plot
    # A
    row_a = df_baseline[df_baseline['scenario'] == 'A_elevator_only'].iloc[0]
    
    # B (Best: r=2, q=150)
    mask_b_best = (df_baseline['scenario'] == 'B_rocket_only') & (df_baseline['r_daily'] == 2) & (df_baseline['payload_ton'] == 150.0)
    row_b = df_baseline[mask_b_best].iloc[0] if mask_b_best.any() else None

    # B (Base: r=1, q=100)
    mask_b_base = (df_baseline['scenario'] == 'B_rocket_only') & (df_baseline['r_daily'] == 1) & (df_baseline['payload_ton'] == 100.0)
    row_b_base = df_baseline[mask_b_base].iloc[0] if mask_b_base.any() else None

    # C
    mask_c = df_baseline['scenario'] == 'C_hybrid_optimal'
    row_c = df_baseline[mask_c].iloc[0] if mask_c.any() else None
    
    scenarios_to_plot = []
    if row_a is not None: 
        scenarios_to_plot.append((row_a, 'Scenario A (Elevator)', 'blue'))
    if row_b_base is not None: 
        scenarios_to_plot.append((row_b_base, 'Scenario B (Rocket r=1, q=100)', 'red'))
    if row_b is not None: 
        scenarios_to_plot.append((row_b, 'Scenario B (Rocket r=2, q=150)', 'darkred'))
    if row_c is not None: 
        scenarios_to_plot.append((row_c, 'Scenario C (Hybrid)', 'purple'))
    
    for row, label, color in scenarios_to_plot:
        t_final = row['time_years']
        # Line from (0,0) to (t_final, M)
        plt.plot([0, t_final], [0, target_mass/1e6], label=f"{label} (T={t_final:.1f}y)", color=color, linewidth=2)
    
    plt.axhline(y=target_mass/1e6, color='black', linestyle='--', alpha=0.5, label='Target (100M t)')
    plt.xlabel('Time (Years from 2050)')
    plt.ylabel('Cumulative Mass Delivered (Million Tons)')
    plt.title('Cumulative Mass Delivery Progress (Q1 Baseline)')
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    plt.savefig(os.path.join(out_dir, 'cum_mass_vs_year.png'))
    plt.savefig(os.path.join(out_dir, 'cum_mass_vs_year.pdf'))
    plt.close()

def plot_pareto_alpha(out_dir: str) -> None:
    """
    Plot Time vs Alpha for Scenario C.
    """
    os.makedirs(out_dir, exist_ok=True)
    
    C_E = elevator_total_capacity_tpy(Elevator.NUM_HARBOURS, Elevator.CAPACITY_PER_HARBOUR_TPY)
    # Use best rocket config
    C_R = rocket_annual_capacity_tpy(Rocket.MAX_SITES, 2, 150.0) 
    M = Problem.TOTAL_MASS_TONS
    
    if C_E == 0: C_E = 1e-9
    if C_R == 0: C_R = 1e-9

    alphas = np.linspace(0, 1, 100)
    times = []
    
    for a in alphas:
        t_e = (a * M) / C_E
        t_r = ((1 - a) * M) / C_R
        times.append(max(t_e, t_r))
        
    plt.figure(figsize=(8, 6))
    plt.plot(alphas, times, label='Completion Time', color='green', linewidth=2)
    
    # Find min
    min_idx = np.argmin(times)
    opt_alpha = alphas[min_idx]
    min_time = times[min_idx]
    
    plt.scatter([opt_alpha], [min_time], color='gold', s=100, zorder=5, edgecolors='black', label=f'Optimal (α={opt_alpha:.2f}, T={min_time:.1f}y)')
    
    plt.xlabel('Alpha (Fraction of Mass via Elevator)')
    plt.ylabel('Completion Time (Years)')
    plt.title('Impact of Mass Split (Alpha) on Project Duration')
    plt.grid(True, alpha=0.3)
    plt.legend()
    
    plt.savefig(os.path.join(out_dir, 'pareto_alpha.png')) 
    plt.close()

def plot_pareto_cost_time_band(df_scan_alpha: pd.DataFrame, out_dir: str) -> None:
    """
    Plot Cost vs Time trade-off (Efficient Frontier only).
    X: Time (Years)
    Y: Cost (Trillion USD)
    Band: Low to High Cost
    """
    os.makedirs(out_dir, exist_ok=True)
    
    plt.figure(figsize=(10, 6))
    
    # 1. Calculate mean cost for visualization
    df = df_scan_alpha.copy()
    df['cost_mean'] = (df['cost_low_usd'] + df['cost_high_usd']) / 2
    
    # 2. Find the anchor point: Minimum Time (Optimal Hybrid)
    min_time_idx = df['time_years'].idxmin()
    min_time = df.loc[min_time_idx, 'time_years']
    opt_alpha = df.loc[min_time_idx, 'alpha']
    
    # 3. Filter for Efficient Frontier: Alpha >= Opt_Alpha
    # This range represents the trade-off: moving towards pure elevator (Alpha=1)
    # increases time but significantly decreases cost.
    df_eff = df[df['alpha'] >= opt_alpha].sort_values("time_years")
    
    # 4. Plot Efficient Frontier
    if not df_eff.empty:
        t_eff = df_eff["time_years"]
        c_low_eff = df_eff["cost_low_usd"] / 1e12
        c_high_eff = df_eff["cost_high_usd"] / 1e12
        c_mean_eff = (c_low_eff + c_high_eff) / 2
        
        plt.fill_between(t_eff, c_low_eff, c_high_eff, color='purple', alpha=0.2, label="Cost Uncertainty Band")
        plt.plot(t_eff, c_mean_eff, color='purple', linewidth=2, label="Efficient Frontier (Mean)")
        
        # 5. Add Markers
        
        # Optimal Hybrid (Start of curve)
        # Use the first point of the sorted efficient dataframe
        row_opt = df_eff.iloc[0]
        t_opt = row_opt['time_years']
        c_opt = row_opt['cost_mean'] / 1e12
        plt.scatter([t_opt], [c_opt], color='gold', s=150, zorder=10, edgecolors='black', label=f"Optimal Hybrid (T={t_opt:.1f}y)")
        
        # Pure Elevator (End of curve)
        row_elev = df_eff.iloc[-1]
        t_elev = row_elev['time_years']
        c_elev = row_elev['cost_mean'] / 1e12
        plt.scatter([t_elev], [c_elev], color='blue', s=100, zorder=10, edgecolors='black', marker='s', label=f"Pure Elevator (T={t_elev:.1f}y)")

    plt.title("Cost-Time Trade-off: Efficient Frontier", fontsize=14)
    plt.xlabel("Time to Completion (Years)")
    plt.ylabel("Total Cost (Trillion USD)")
    plt.grid(True, alpha=0.3)
    plt.legend()
    
    # Allow autoscaling for X-axis (do not force start at 0)
    # But add a little padding
    if not df_eff.empty:
        x_min = df_eff["time_years"].min()
        x_max = df_eff["time_years"].max()
        padding = (x_max - x_min) * 0.1
        plt.xlim(left=max(0, x_min - padding), right=x_max + padding)
    
    plt.tight_layout()
    plt.savefig(os.path.join(out_dir, "pareto_cost_time_band.png"))
    plt.close()
