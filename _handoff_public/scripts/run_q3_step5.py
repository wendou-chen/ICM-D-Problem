import sys
import os
import yaml
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Ensure project root is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from configs.constants import WaterDemand, WaterPolicy, ReliabilityPreset, RELIABILITY_PRESETS
from src.q3 import simulation
from src.utils.plot_style import apply_style

# Load config
def load_config(path="configs/risk_params.yaml"):
    with open(path, 'r') as f:
        return yaml.safe_load(f)

class RiskSimulatorWrapper:
    def __init__(self, config, L_safe_days):
        self.config = config
        self.L = L_safe_days
        
        # Parse Config to match simulation.py signature
        dem = config['demand']
        cap = config['capacity']
        risk = config['risk']
        
        self.daily_demand = (dem['population'] * dem['w_L_per_person_day'] * (1 - dem['eta_recycle'])) / 1000.0
        self.C_E_day = (cap['phi_E'] * cap['C_E_year_ton']) / 365.0
        
        self.rocket_config = {
            'K': cap['K_sites'],
            'q': cap['q_ton_per_launch'],
            'r_base': cap['r_launches_per_site_per_day']
        }
        
        # Policy
        self.policy = WaterPolicy(
            L_SAFE_DAYS=self.L,
            B_BUFFER_DAYS=dem['B_buffer_days'],
            USE_DYNAMIC_SURGE=True
        )
        
        # Initial Inventory
        self.init_inv = (self.L + dem['B_buffer_days']) * self.daily_demand
        
        # Risk Params for Step 5
        self.risk_params = risk
        
        # Dummy Preset (Step 5 overrides it)
        self.preset = RELIABILITY_PRESETS['SEVERE']
        
        # Cost Params
        self.cost_L = cap['C_L_per_launch']
        self.cost_E_ton = cap['c_E_per_kg'] * 1000.0
        self.cost_A_trans = cap['C_A_per_transfer'] # Per transfer unit (q_A)
        self.q_A = cap['q_A_ton']

    def run_year(self):
        res = simulation.simulate_inventory_trajectory(
            duration_days=self.config['simulation']['horizon_days'],
            initial_inventory_tons=self.init_inv,
            daily_demand_tons=self.daily_demand,
            daily_supply_cap_elevator_tons=self.C_E_day,
            rocket_config=self.rocket_config,
            preset=self.preset,
            policy=self.policy,
            phi_e=self.config['capacity']['phi_E'],
            phi_r=self.config['capacity']['phi_R'],
            return_trajectory=True,
            step5_mode=True,
            risk_params=self.risk_params
        )
        
        # Calculate Costs
        # Elevator
        xE = res['total_shipped_E']
        cost_E_opex = xE * self.cost_E_ton
        # Apex transfers
        n_trans = np.ceil(xE / self.q_A)
        cost_E_apex = n_trans * self.cost_A_trans
        
        # Rocket
        # Base cost for all attempts
        attempts = res['total_attempts_R']
        cost_R_total = attempts * self.cost_L
        
        # We can try to split R cost into "Base" (Success) and "Waste" (Fail)
        # Failures = attempts - successes? No, track explicitly
        failures = res['total_failures_R']
        successes = attempts - failures
        cost_R_base = successes * self.cost_L
        cost_R_waste = failures * self.cost_L
        
        total_cost = cost_E_opex + cost_E_apex + cost_R_total
        
        res['cost_components'] = {
            'Elevator_OPEX': cost_E_opex,
            'Apex_Transfer': cost_E_apex,
            'Rocket_Base': cost_R_base,
            'Rocket_Waste': cost_R_waste
        }
        res['total_cost'] = total_cost
        res['availability_E'] = res['elevator_up_days'] / 365.0
        
        return res

def main():
    print("Running Step 5: Risk Assessment...")
    apply_style()
    config = load_config()
    OUTPUT_DIR = "outputs/q3/step5"
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    L_values = [7, 15, 30, 45, 60]
    n_sims = config['simulation']['n_sims']
    
    summary = []
    
    for L in L_values:
        print(f"  Scanning Safety Stock L={L} days (N={n_sims})...")
        sim = RiskSimulatorWrapper(config, L)
        
        stockouts = 0
        costs = []
        min_Ws = []
        avails = []
        
        # For L=30, save trajectories
        trajectories = []
        components_list = []
        
        for i in range(n_sims):
            r = sim.run_year()
            
            if r['stockout_days'] > 0:
                stockouts += 1
                
            costs.append(r['total_cost'])
            min_Ws.append(r['min_inventory'])
            avails.append(r['availability_E'])
            
            if L == 30:
                if i < config['simulation']['n_spaghetti']:
                    trajectories.append(r['trajectory'])
                if i < 100:
                    components_list.append(r['cost_components'])
        
        p_stockout = stockouts / n_sims
        mean_cost = np.mean(costs)
        var95_cost = np.quantile(costs, 0.95)
        mean_avail = np.mean(avails)
        
        summary.append({
            'L_safe_days': L,
            'P_stockout': p_stockout,
            'MeanCost_B': mean_cost / 1e9,
            'VaR95Cost_B': var95_cost / 1e9,
            'Mean_Avail_E': mean_avail
        })
        
        if L == 30:
            # Save Spaghetti Data
            np.save(os.path.join(OUTPUT_DIR, "spaghetti_L30.npy"), trajectories)
            # Save Cost Components
            pd.DataFrame(components_list).to_csv(os.path.join(OUTPUT_DIR, "cost_components_L30.csv"), index=False)

            # Save Plot Source Data (User Request)
            # 1. Spaghetti Data (CSV format for easier plotting elsewhere)
            # Transpose so columns are simulations, rows are days
            df_spaghetti = pd.DataFrame(trajectories).T
            df_spaghetti.columns = [f'Sim_{i}' for i in range(len(trajectories))]
            df_spaghetti.to_csv(os.path.join(OUTPUT_DIR, "plot_data_spaghetti_L30.csv"), index_label="Day")

            # 2. Pareto Cost Data (Mean of components)
            # We already have cost_components_L30.csv, which IS the source data for distribution analysis.
            # But let's also save the summarized means for the Pareto bar chart specifically.
            df_comp = pd.DataFrame(components_list)
            df_pareto = df_comp.mean().sort_values(ascending=False).reset_index()
            df_pareto.columns = ['Component', 'Mean_Cost_USD']
            df_pareto.to_csv(os.path.join(OUTPUT_DIR, "plot_data_pareto_cost_L30.csv"), index=False)

    # Output Summary
    df = pd.DataFrame(summary)
    csv_path = os.path.join(OUTPUT_DIR, "risk_summary.csv")
    df.to_csv(csv_path, index=False)
    print("\nRisk Assessment Summary:")
    print(df.to_string(index=False))
    print(f"\nSaved results to {OUTPUT_DIR}")
    
    # Plotting (Simple generation here, detailed formatting in separate files usually, but let's do quick ones)
    # Spaghetti Plot L=30
    traj_data = np.load(os.path.join(OUTPUT_DIR, "spaghetti_L30.npy"))
    plt.figure(figsize=(10, 6))
    for t in traj_data:
        plt.plot(t, color='gray', alpha=0.3, linewidth=1)
    plt.axhline(0, color='red', linestyle='--', linewidth=2, label='Stockout')
    plt.title('Inventory Risk: Spaghetti Plot (L=30 days)')
    plt.xlabel('Day')
    plt.ylabel('Inventory (Tons)')
    plt.legend()
    plt.savefig(os.path.join(OUTPUT_DIR, "fig_spaghetti_L30.png"))
    plt.close()
    
    # Pareto Cost (L=30)
    comp_df = pd.read_csv(os.path.join(OUTPUT_DIR, "cost_components_L30.csv"))
    means = comp_df.mean().sort_values(ascending=False)
    
    plt.figure(figsize=(8, 6))
    means.plot(kind='bar', color='skyblue')
    plt.title('Average Cost Structure (Pareto Components)')
    plt.ylabel('Cost (USD)')
    plt.grid(True, axis='y', alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, "fig_pareto_cost_L30.png"))
    plt.close()

if __name__ == "__main__":
    main()
