import sys
import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

# Ensure project root is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from configs.constants import WaterDemand, Elevator, ReliabilityPreset, RELIABILITY_PRESETS
from src.q3 import analytics

OUTPUT_DIR = "outputs/q3/step1"
os.makedirs(OUTPUT_DIR, exist_ok=True)

def run_step1_demand_analysis():
    print("Running Step 1: Demand Analysis & Physical Feasibility...")
    
    results = []
    
    # Use constants from WaterDemand
    P = WaterDemand.POPULATION
    w_baseline = WaterDemand.W_L_PER_PERSON_DAY
    # Include both the preset list and a finer scan for plotting
    eta_scan = np.unique(np.concatenate([
        list(WaterDemand.ETA_RECYCLE_LIST), 
        np.linspace(0, 0.99, 50)
    ]))
    eta_scan.sort()
    
    # Elevator Capacity Benchmark (Physical Upper Limit)
    # 3 Harbours * 179,000 tpy
    C_E_total_year = Elevator.NUM_HARBOURS * Elevator.CAPACITY_PER_HARBOUR_TPY
    
    for eta in eta_scan:
        metrics = analytics.calculate_demand(P, w_baseline, eta)
        d_year = metrics['annual_tons']
        
        # Feasibility check: Can elevator handle it?
        # Ratio > 1.0 means infeasible even if elevator does nothing else
        capacity_load_ratio = d_year / C_E_total_year
        
        results.append({
            'eta': eta,
            'net_per_capita_lpd': metrics['net_per_capita_lpd'],
            'annual_tons': d_year,
            'capacity_load_ratio': capacity_load_ratio,
            'feasible_elevator_only': capacity_load_ratio <= 1.0
        })
        
    df = pd.DataFrame(results)
    csv_path = os.path.join(OUTPUT_DIR, "step1_summary.csv")
    df.to_csv(csv_path, index=False)
    print(f"Saved Step 1 summary to {csv_path}")
    
    # --- Plotting ---
    
    # 1. Demand Sensitivity Curve
    plt.figure(figsize=(10, 6))
    sns.lineplot(data=df, x='eta', y='annual_tons', linewidth=3, label='Annual Water Demand')
    
    # Add Capacity Reference Lines
    plt.axhline(y=C_E_total_year, color='red', linestyle='--', linewidth=2, label='Total Elevator Capacity (3 Harbours)')
    plt.axhline(y=C_E_total_year/3, color='orange', linestyle='--', linewidth=2, label='Single Elevator Capacity')
    
    plt.xlabel('Recycling Efficiency ($\eta$)')
    plt.ylabel('Annual Transport Requirement (Tons)')
    plt.title(f'Water Demand Sensitivity vs Elevator Capacity (Pop={P:,})')
    plt.yscale('log') # Log scale because 0% is massive
    plt.grid(True, which="both", ls="-", alpha=0.2)
    plt.legend()
    plt.savefig(os.path.join(OUTPUT_DIR, "fig1_demand_sensitivity.png"))
    plt.close()
    
    # 2. Feasibility "Explosion" Point
    # Filter for the preset eta list to show discrete points
    subset = df[df['eta'].isin(WaterDemand.ETA_RECYCLE_LIST)]
    
    plt.figure(figsize=(10, 6))
    colors = ['green' if x <= 1.0 else 'red' for x in subset['capacity_load_ratio']]
    sns.barplot(data=subset, x='eta', y='capacity_load_ratio', palette=colors)
    
    plt.axhline(y=1.0, color='black', linestyle='-', label='Physical Capacity Limit')
    plt.xlabel('Recycling Efficiency ($\eta$)')
    plt.ylabel('Load Ratio (Demand / Total Elevator Capacity)')
    plt.title('Physical Feasibility Check: Will Water Break the Elevator?')
    plt.legend()
    
    for index, row in subset.iterrows():
        # Label the bars
        plt.text(row.name, row.capacity_load_ratio, f"{row.capacity_load_ratio:.1%}", 
                 color='black', ha="center", va="bottom")

    plt.savefig(os.path.join(OUTPUT_DIR, "fig2_capacity_vs_demand.png"))
    plt.close()
    
    print("Step 1 Plots Generated.")

if __name__ == "__main__":
    run_step1_demand_analysis()
