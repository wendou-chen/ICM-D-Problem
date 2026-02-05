import pandas as pd
import matplotlib.pyplot as plt
import os
import numpy as np
from configs.constants import Problem, Elevator, Rocket
from src.q1.capacity import elevator_total_capacity_tpy, rocket_annual_capacity_tpy
from src.utils.plot_style import apply_style

def plot_cumulative_mass(df_baseline: pd.DataFrame, out_dir: str) -> None:
    """
    Plot Cumulative Mass Delivered over Time for selected scenarios.
    """
    # Global Font Update
    apply_style()

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

    # C (Optimal)
    mask_c_opt = df_baseline['scenario'] == 'C_hybrid_optimal'
    row_c_opt = df_baseline[mask_c_opt].iloc[0] if mask_c_opt.any() else None

    # C (Base: r=1, q=100)
    mask_c_base = (df_baseline['scenario'] == 'C_hybrid') & (df_baseline['r_daily'] == 1) & (df_baseline['payload_ton'] == 100.0)
    row_c_base = df_baseline[mask_c_base].iloc[0] if mask_c_base.any() else None

    # C (Best: r=2, q=150)
    mask_c_best = (df_baseline['scenario'] == 'C_hybrid') & (df_baseline['r_daily'] == 2) & (df_baseline['payload_ton'] == 150.0)
    row_c_best = df_baseline[mask_c_best].iloc[0] if mask_c_best.any() else None

    scenarios_to_plot = []
    if row_a is not None:
        scenarios_to_plot.append((row_a, 'Scenario A (Elevator)', 'blue'))
    if row_b_base is not None:
        scenarios_to_plot.append((row_b_base, 'Scenario B (Rocket r=1, q=100)', 'red'))
    if row_b is not None:
        scenarios_to_plot.append((row_b, 'Scenario B (Rocket r=2, q=150)', 'darkred'))

    # Add new C lines
    if row_c_base is not None:
        scenarios_to_plot.append((row_c_base, 'Scenario C (Hybrid r=1, q=100)', 'mediumorchid'))
    if row_c_best is not None:
        scenarios_to_plot.append((row_c_best, 'Scenario C (Hybrid r=2, q=150)', 'purple'))

    # We can keep optimal C if we want, but it might overlap with C (Best) if optimal is r=2, q=150.
    # The baseline code uses max(r) and max(q) for Optimal C, so C_hybrid_optimal and C(r=2,q=150) should be identical.
    # Let's plot Optimal C as a check or skip it if redundant.
    # I'll plot it with a distinct style if it's there, but user specifically asked for the two specific ones.
    # To avoid clutter, I will plot the two specific ones requested.
    # (Optional: uncomment next lines to include "Optimal" label explicitly if needed)
    # if row_c_opt is not None:
    #    scenarios_to_plot.append((row_c_opt, 'Scenario C (Optimal)', 'gold'))

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

    plt.savefig(os.path.join(out_dir, 'cum_mass_vs_year.png'), dpi=600)
    plt.savefig(os.path.join(out_dir, 'cum_mass_vs_year.pdf'))
    plt.close()

def plot_pareto_alpha(out_dir: str) -> None:
    """
    Plot Time vs Alpha for Scenario C.
    """
    # Global Font Update
    apply_style()

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

    plt.savefig(os.path.join(out_dir, 'pareto_alpha.png'), dpi=600)
    plt.close()

def plot_pareto_cost_time_band(df_scan_alpha: pd.DataFrame, out_dir: str, r_val: int = 2, q_val: float = 150.0) -> None:
    """
    Plot Cost vs Time trade-off (Full Curve: Inefficient + Efficient).
    X: Time (Years)
    Y: Cost (Trillion USD)
    Band: Low to High Cost
    """
    # 1. Global Font Update
    apply_style()

    os.makedirs(out_dir, exist_ok=True)

    plt.figure(figsize=(10, 6))

    # 2. Calculate mean cost for visualization
    df = df_scan_alpha.copy()
    df['cost_mean'] = (df['cost_low_usd'] + df['cost_high_usd']) / 2

    # 3. Find the anchor point: Minimum Time (Optimal Hybrid)
    min_time_idx = df['time_years'].idxmin()
    row_opt = df.loc[min_time_idx]
    opt_alpha = row_opt['alpha']
    t_opt = row_opt['time_years']
    c_opt_mean = row_opt['cost_mean']

    # 4. Split Data into Inefficient (Rocket-Heavy) and Efficient (Elevator-Heavy)
    # The curve is typically V-shaped in Time.
    # Inefficient: alpha <= opt_alpha.
    df_ineff = df[df['alpha'] <= opt_alpha].sort_values("time_years")
    df_eff = df[df['alpha'] >= opt_alpha].sort_values("time_years")

    # 5. Plot Inefficient Band (Rocket-Heavy) -> Purple
    if not df_ineff.empty:
        t = df_ineff["time_years"]
        c_low = df_ineff["cost_low_usd"] / 1e12
        c_high = df_ineff["cost_high_usd"] / 1e12
        c_mean = (c_low + c_high) / 2

        # Use same color 'purple' with alpha. Overlap will naturally be darker.
        plt.fill_between(t, c_low, c_high, color='purple', alpha=0.2)
        plt.plot(t, c_mean, color='purple', linewidth=2, linestyle='--', label="Inefficient Region (Rocket-Heavy)")

    # 6. Plot Efficient Frontier (Elevator-Heavy) -> Purple
    if not df_eff.empty:
        t = df_eff["time_years"]
        c_low = df_eff["cost_low_usd"] / 1e12
        c_high = df_eff["cost_high_usd"] / 1e12
        c_mean = (c_low + c_high) / 2

        plt.fill_between(t, c_low, c_high, color='purple', alpha=0.2, label="Cost Uncertainty Band")
        plt.plot(t, c_mean, color='purple', linewidth=2, label="Efficient Frontier (Mean)")

    # 7. Add Markers

    # Pure Rocket (alpha=0)
    # Find row with alpha closest to 0
    row_rock = df.iloc[0] # alphas are sorted 0..1
    if abs(row_rock['alpha'] - 0.0) < 1e-6:
         plt.scatter([row_rock['time_years']], [row_rock['cost_mean']/1e12], color='red', s=100, zorder=10, edgecolors='black', marker='^', label="Pure Rocket")

    # Optimal Hybrid
    plt.scatter([t_opt], [c_opt_mean/1e12], color='gold', s=150, zorder=11, edgecolors='black', label=f"Optimal Hybrid (T={t_opt:.1f}y)\n(r={r_val}, q={q_val})")

    # Pure Elevator (alpha=1)
    row_elev = df.iloc[-1]
    if abs(row_elev['alpha'] - 1.0) < 1e-6:
        plt.scatter([row_elev['time_years']], [row_elev['cost_mean']/1e12], color='blue', s=100, zorder=10, edgecolors='black', marker='s', label=f"Pure Elevator (T={row_elev['time_years']:.1f}y)")

    plt.title("Cost-Time Trade-off: Full Landscape", fontsize=16)
    plt.xlabel("Time to Completion (Years)", fontsize=12)
    plt.ylabel("Total Cost (Trillion USD)", fontsize=12)
    plt.grid(True, alpha=0.3)
    plt.legend(loc='best')

    # Adjust axes
    # Ensure we see the whole V shape
    x_min = df["time_years"].min()
    x_max = df["time_years"].max()
    padding = (x_max - x_min) * 0.1
    plt.xlim(left=max(0, x_min - padding), right=x_max + padding)

    plt.tight_layout()
    plt.savefig(os.path.join(out_dir, "pareto_cost_time_band.png"), dpi=600)
    plt.savefig(os.path.join(out_dir, "pareto_cost_time_band.svg"))
    plt.savefig(os.path.join(out_dir, "pareto_cost_time_band.pdf"))
    plt.close()
