import sys
import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from tqdm import tqdm

# Ensure project root is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from configs.constants import WaterDemand, WaterPolicy, Elevator, Rocket, RELIABILITY_PRESETS, WaterCapacityShare
from src.q3 import analytics, simulation
from src.utils.plot_style import apply_style

OUTPUT_DIR = "outputs/q3/step3"
os.makedirs(OUTPUT_DIR, exist_ok=True)

def run_step3_reliability_analysis():
    print("Running Step 3: Inventory Reliability Analysis...")
    apply_style()

    # 1. Define Baseline Scenario (Must be physically feasible)
    # Based on Step 1, we NEED eta >= 0.95. Let's use eta=0.98 (ISS standard).
    eta = 0.98
    P = WaterDemand.POPULATION
    w = WaterDemand.W_L_PER_PERSON_DAY
    
    metrics = analytics.calculate_demand(P, w, eta)
    d_day_ton = metrics['daily_tons']
    
    print(f"  Scenario: Pop={P}, w={w}, eta={eta}")
    print(f"  Net Daily Demand: {d_day_ton:.2f} tons/day")
    
    # 2. Define Supply Capacity (Severe Scenario)
    preset = RELIABILITY_PRESETS['SEVERE'] # Worst case reliability
    
    # Elevator Capacity: 3 Harbours, but subject to failures
    C_E_nominal_day = (Elevator.NUM_HARBOURS * Elevator.CAPACITY_PER_HARBOUR_TPY) / 365.0
    
    # Rocket Config
    rocket_config = {
        'K': Rocket.MAX_SITES,
        'q': (Rocket.PAYLOAD_RANGE_TON[0] + Rocket.PAYLOAD_RANGE_TON[1]) / 2.0,
        'r_base': Rocket.R_BASE
    }
    
    # 3. Simulation Scan: Vary Safety Stock Days (L)
    # Buffer B is fixed (e.g. 15 days) to handle lead time variability?
    # Or we just vary L and assume B=0 for simplicity in this specific "Initial Inventory" scan.
    # The prompt asked for "Initial Inventory Buffer". Let's map Initial Inventory = L * Demand.
    
    L_scan_days = [5, 10, 15, 20, 25, 30, 40, 50, 60]
    B_fixed = 15
    
    results = []
    
    # We want to find P(No Stockout) > 0.95
    
    for L in L_scan_days:
        # Create policy object
        policy = WaterPolicy(
            L_SAFE_DAYS=L, 
            B_BUFFER_DAYS=B_fixed, 
            USE_DYNAMIC_SURGE=True
        )
        
        # Initial Inventory is usually set to Target Level S = (L+B)*d
        # Or just L*d? Let's use Target Level S to be safe and consistent with Order-Up-To.
        initial_inv = (policy.L_SAFE_DAYS + policy.B_BUFFER_DAYS) * d_day_ton
        
        success_count = 0
        n_iter = 100
        
        # Store one trace for plotting
        example_trace = None
        
        for i in range(n_iter):
            # Capture trace for the first run of L=30
            capture = (L == 30 and i < 5)
            
            res = simulation.simulate_inventory_trajectory(
                duration_days=365,
                initial_inventory_tons=initial_inv,
                daily_demand_tons=d_day_ton,
                daily_supply_cap_elevator_tons=C_E_nominal_day,
                rocket_config=rocket_config,
                preset=preset,
                policy=policy,
                phi_e=1.0, # Water gets priority
                phi_r=1.0,
                return_trajectory=capture
            )
            
            if res['stockout_days'] == 0:
                success_count += 1
                
            if capture:
                if example_trace is None: example_trace = []
                example_trace.append(res['trajectory'])
        
        p_success = success_count / n_iter
        
        results.append({
            'L_safe_days': L,
            'initial_inv_tons': initial_inv,
            'p_success': p_success
        })
        
        print(f"  L={L} days: P(Success)={p_success:.2f}")
        
        # Plot traces for L=30
        if L == 30 and example_trace:
            # Save Trace Data for Plotting
            df_trace = pd.DataFrame(example_trace).T
            df_trace.columns = [f'Sim_{i}' for i in range(len(example_trace))]
            df_trace.to_csv(os.path.join(OUTPUT_DIR, f"plot_data_trace_L{L}.csv"), index_label="Day")

            plt.figure(figsize=(12, 6))
            for tr in example_trace:
                plt.plot(tr, alpha=0.6)
            plt.axhline(0, color='red', linestyle='--', label='Stockout Threshold')
            plt.title(f'Inventory Trajectories (L={L} days, Severe Scenario)')
            plt.xlabel('Day')
            plt.ylabel('Inventory (Tons)')
            plt.grid(True, alpha=0.3)
            plt.savefig(os.path.join(OUTPUT_DIR, f"trace_L{L}.png"))
            plt.close()

    # 4. Save & Plot Results
    df = pd.DataFrame(results)
    df.to_csv(os.path.join(OUTPUT_DIR, "step3_reliability.csv"), index=False)

    # Save Reliability Curve Data for Plotting
    df.to_csv(os.path.join(OUTPUT_DIR, "plot_data_reliability_curve.csv"), index=False)

    plt.figure(figsize=(10, 6))
    sns.lineplot(data=df, x='L_safe_days', y='p_success', marker='o', linewidth=2)
    plt.axhline(0.95, color='green', linestyle='--', label='95% Reliability Target')
    plt.xlabel('Safety Stock Level (Days)')
    plt.ylabel('Probability of Continuous Service (1 Year)')
    plt.title('Reliability vs Safety Stock (Severe Scenario, $\eta$=0.98)')
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.savefig(os.path.join(OUTPUT_DIR, "fig3_reliability_curve.png"))
    plt.close()
    
    print("Step 3 Analysis Completed.")

if __name__ == "__main__":
    run_step3_reliability_analysis()
