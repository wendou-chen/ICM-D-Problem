import matplotlib.pyplot as plt
import numpy as np
import os
import seaborn as sns
from typing import List, Dict, Any

def plot_alpha_drift(
    results: List[Dict[str, Any]], 
    param_name: str, 
    output_path: str
):
    """
    Plot alpha* drift vs a parameter (A_E or P_R).
    results: list of dicts with keys {param_name, 'alpha_star'}
    """
    x = [r[param_name] for r in results]
    y = [r['alpha_star'] for r in results]
    
    plt.figure(figsize=(8, 6))
    plt.plot(x, y, 'o-', linewidth=2)
    plt.xlabel(param_name)
    plt.ylabel(r'Optimal Elevator Share ($\alpha^*$)')
    plt.title(f'Alpha* Drift vs {param_name}')
    plt.grid(True, alpha=0.3)
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    plt.savefig(output_path)
    plt.close()

def plot_boxplot_time(
    data_map: Dict[str, List[float]], 
    output_path: str
):
    """
    Boxplot of completion times for different scenarios.
    data_map: {'ScenarioName': [times...], ...}
    """
    labels = list(data_map.keys())
    values = list(data_map.values())
    
    plt.figure(figsize=(12, 6))
    plt.boxplot(values, labels=labels)
    plt.ylabel('Completion Time (Years)')
    plt.title('Completion Time Distribution by Scenario')
    plt.xticks(rotation=45)
    plt.grid(True, axis='y', alpha=0.3)
    plt.tight_layout()
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    plt.savefig(output_path)
    plt.close()

def plot_feasibility_region(
    C_E_range: np.ndarray,
    C_R_range: np.ndarray,
    M: float,
    T_target: float,
    system_points: List[Dict[str, Any]],
    output_path: str
):
    """
    Plot feasibility region (C_E vs C_R).
    Feasible if C_E + C_R >= M/T

    Args:
        C_E_range: range of elevator capacities
        C_R_range: range of rocket capacities
        M: Total mass
        T_target: target years (e.g. 20)
        system_points: list of dicts {'label': str, 'C_E': float, 'C_R': float, 'color': str}
        output_path: file path
    """
    X, Y = np.meshgrid(C_E_range, C_R_range)
    # Primary Target
    Z_target = (X + Y) >= (M / T_target)

    plt.figure(figsize=(10, 8))

    # 1. Shade regions
    # Infeasible: Red-ish, Feasible: Green-ish
    # Using contourf with custom levels
    plt.contourf(X, Y, Z_target, levels=[-0.1, 0.5, 1.1], colors=['#ffebee', '#e8f5e9'], alpha=0.7)

    # 2. Add multiple time horizons lines
    horizons = [20, 40, 60, 80, 100]
    # Use a colormap
    cmap = plt.get_cmap('viridis')
    colors = [cmap(i) for i in np.linspace(0, 0.9, len(horizons))]
    styles = ['-', '--', '-.', ':', (0, (3, 1, 1, 1))]

    for i, T in enumerate(horizons):
        req_cap = M / T
        # Plot line C_E + C_R = req_cap => C_R = req_cap - C_E
        # Only plot where C_R >= 0
        line_x = np.linspace(0, max(C_E_range), 200)
        line_y = req_cap - line_x
        valid = (line_y >= 0) & (line_y <= max(C_R_range))

        if np.any(valid):
            plt.plot(line_x[valid], line_y[valid],
                    linestyle=styles[i%len(styles)],
                    color=colors[i],
                    linewidth=2,
                    label=f'T = {T} years')

    # 3. Plot System Points
    # Markers: ^ for A, s for B, o for C
    # But usually we just plot the "Effective Capacity" of the system under MILD/MOD/SEV
    for pt in system_points:
        ce = pt['C_E']
        cr = pt['C_R']
        label = pt['label']
        color = pt.get('color', 'blue')
        marker = pt.get('marker', 'o')

        plt.scatter(ce, cr, c=color, marker=marker, s=100, edgecolors='k', zorder=10, label=label)

        # Calculate gap to T_target
        current_cap = ce + cr
        req_cap = M / T_target
        gap = max(0, req_cap - current_cap)

        if gap > 0:
            plt.text(ce + 10000, cr + 10000, f"ΔC ≈ {gap/1e6:.1f}M tpy", fontsize=9, color='#c62828')

    plt.xlabel('Elevator Effective Capacity (tons/year)')
    plt.ylabel('Rocket Effective Capacity (tons/year)')
    plt.title(f'Feasibility Region & System Operating Points (Target T={T_target}y)')
    plt.legend(loc='upper right')
    plt.grid(True, alpha=0.3)
    plt.xlim(0, max(C_E_range))
    plt.ylim(0, max(C_R_range))

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    plt.savefig(output_path)
    plt.close()

def plot_gamma_scan(
    df_var: Any, # pandas dataframe for VaR
    df_prob: Any, # pandas dataframe for Probability (long format)
    output_path_var: str,
    output_path_prob: str
):
    """
    Plot Gamma Scan results.
    df_var columns: scenario_level, gamma, VaR_95
    df_prob columns: scenario_level, gamma, horizon, probability
    """
    import pandas as pd
    
    # 1. VaR 95 vs Gamma
    plt.figure(figsize=(10, 6))
    sns.lineplot(data=df_var, x='gamma', y='VaR_95', hue='scenario_level', style='scenario_level', markers=True, dashes=False)
    plt.xlabel(r'Emergency Surge Multiplier ($\gamma$)')
    plt.ylabel('95% VaR Completion Time (Years)')
    plt.title('Risk Reduction via Dynamic Backup (Gamma Scan)')
    plt.grid(True, alpha=0.3)
    plt.savefig(output_path_var)
    plt.close()

    # 2. Probability of Success vs Gamma (Faceted by Scenario)
    # FacetGrid: Col = scenario_level, Hue = horizon
    g = sns.relplot(
        data=df_prob,
        x="gamma", 
        y="probability",
        hue="horizon",
        col="scenario_level",
        kind="line",
        marker="o",
        palette="viridis",
        height=5, 
        aspect=1
    )
    g.set_axis_labels(r"Surge Multiplier ($\gamma$)", "Probability of Success")
    g.fig.suptitle("Success Probability vs Surge Multiplier by Horizon", y=1.02)
    
    plt.savefig(output_path_prob)
    plt.close()
