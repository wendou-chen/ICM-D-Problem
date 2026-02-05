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

class ISRUSweepSimulator:
    def __init__(self, config):
        self.config = config

        # Parse Config
        dem = config['demand']
        cap = config['capacity']
        risk = config['risk']

        # 1. Calculate Baseline Demand (Total Need)
        # d_day_total = P * w * (1 - eta) / 1000
        self.total_daily_demand = (dem['population'] * dem['w_L_per_person_day'] * (1 - dem['eta_recycle'])) / 1000.0

        # 2. Capacity & Cost Params
        self.C_E_day = (cap['phi_E'] * cap['C_E_year_ton']) / 365.0

        self.rocket_config = {
            'K': cap['K_sites'],
            'q': cap['q_ton_per_launch'],
            'r_base': cap['r_launches_per_site_per_day']
        }

        self.risk_params = risk
        self.preset = RELIABILITY_PRESETS['SEVERE']

        # Cost Params
        self.cost_L = cap['C_L_per_launch']
        self.cost_E_ton = cap['c_E_per_kg'] * 1000.0
        self.cost_A_trans = cap['C_A_per_transfer']
        self.q_A = cap['q_A_ton']

        # Inventory Policy Params
        # Note: We keep L and B fixed in days, but the actual TONS depends on the shipped demand.
        # However, physically, the tank size might be fixed?
        # The prompt implies: "Inventory dynamics remain completely unchanged (just replace demand term)"
        # W_{t+1} = W_t + ... - d_{ship}
        # The policy checks: need = Target - Inventory.
        # Target = (L+B) * d_ship.
        # If d_ship drops to 0, Target drops to 0?
        # Wait, if we produce locally, we still need a buffer?
        # The prompt says: "If u >= d_day, then d_ship=0 and Earth-based transportation is only needed for contingency buffers"
        # This implies the target stock is defined relative to the *shipping* need?
        # Or relative to total consumption?
        # "Target stock S = (L + B) * daily_demand_tons" in simulation.py.
        # If we pass `daily_demand_tons = d_ship` to the simulation function, then the Target Stock scales down with Gamma.
        # This makes sense: if we import less, we buffer less imports. The ISRU supply is assumed "constant/reliable" inside the `u` term (netted out).
        # So we just pass `d_ship` as the demand to the engine.

        self.L_safe = dem['L_safe_days_baseline']
        self.B_buffer = dem['B_buffer_days']

        self.policy = WaterPolicy(
            L_SAFE_DAYS=self.L_safe,
            B_BUFFER_DAYS=self.B_buffer,
            USE_DYNAMIC_SURGE=True
        )

    def run_scenario(self, gamma):
        """
        Run simulation for a specific ISRU coverage ratio gamma.
        d_ship = d_total * (1 - gamma)
        """
        # A. Calculate Net Shipping Demand
        u_isru = gamma * self.total_daily_demand
        d_ship = max(0.0, self.total_daily_demand - u_isru)

        # B. Initial Inventory
        # Scale initial inventory to match the new flow rate?
        # Usually yes, start at steady state target.
        init_inv = (self.L_safe + self.B_buffer) * d_ship

        # C. Run Monte Carlo
        n_sims = self.config['simulation']['n_sims']
        costs = []
        stockouts = 0
        min_Ws = []

        print(f"    Running Gamma={gamma:.1f} (ISRU={u_isru:.1f}t, Ship={d_ship:.1f}t)...")

        for i in range(n_sims):
            # We pass `d_ship` as `daily_demand_tons` to the engine
            res = simulation.simulate_inventory_trajectory(
                duration_days=self.config['simulation']['horizon_days'],
                initial_inventory_tons=init_inv,
                daily_demand_tons=d_ship,
                daily_supply_cap_elevator_tons=self.C_E_day,
                rocket_config=self.rocket_config,
                preset=self.preset,
                policy=self.policy,
                phi_e=self.config['capacity']['phi_E'],
                phi_r=self.config['capacity']['phi_R'],
                return_trajectory=False,
                step5_mode=True,
                risk_params=self.risk_params
            )

            # Check Stockout
            if res['stockout_days'] > 0:
                stockouts += 1

            # Calculate Cost (Same logic as Step 5)
            xE = res['total_shipped_E']
            cost_E_opex = xE * self.cost_E_ton
            n_trans = np.ceil(xE / self.q_A)
            cost_E_apex = n_trans * self.cost_A_trans

            attempts = res['total_attempts_R']
            cost_R_total = attempts * self.cost_L

            total_cost = cost_E_opex + cost_E_apex + cost_R_total
            costs.append(total_cost)
            min_Ws.append(res['min_inventory'])

        # D. Aggregation
        p_stockout = stockouts / n_sims
        mean_cost = np.mean(costs)
        var95_cost = np.quantile(costs, 0.95)

        return {
            'gamma': gamma,
            'u_isru_ton': u_isru,
            'd_ship_ton': d_ship,
            'P_stockout': p_stockout,
            'MeanCost_B': mean_cost / 1e9,
            'VaR95Cost_B': var95_cost / 1e9
        }

def main():
    print("Running Step 6: ISRU Sensitivity Sweep...")
    apply_style()
    config = load_config()

    OUTPUT_DIR = "outputs/q3/isru"
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # 1. Define Grid
    gamma_grid = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]

    # 2. Run Sweep
    sim = ISRUSweepSimulator(config)
    results = []

    for gamma in gamma_grid:
        res = sim.run_scenario(gamma)
        results.append(res)

    # 3. Save Results
    df = pd.DataFrame(results)
    csv_path = os.path.join(OUTPUT_DIR, "summary_isru_sweep.csv")
    df.to_csv(csv_path, index=False)

    print("\nISRU Sweep Results:")
    print(df.to_string(index=False))

    # 4. Visualization
    sns.set_style("whitegrid")

    # Fig 1: Gamma vs Stockout
    plt.figure(figsize=(8, 6))
    plt.plot(df['gamma'], df['P_stockout'], marker='o', linewidth=2, color='#e74c3c')
    plt.title('Impact of ISRU Coverage on Stockout Risk')
    plt.xlabel('ISRU Coverage Ratio ($\gamma$)')
    plt.ylabel('Annual Stockout Probability')
    plt.ylim(-0.05, 1.05)
    plt.grid(True, alpha=0.3)
    plt.savefig(os.path.join(OUTPUT_DIR, "fig_isru_gamma_vs_stockout.png"))
    plt.close()

    # Fig 2: Gamma vs Cost (VaR95)
    plt.figure(figsize=(8, 6))
    plt.plot(df['gamma'], df['VaR95Cost_B'], marker='s', linewidth=2, color='#2c3e50', label='95% VaR Cost')
    plt.plot(df['gamma'], df['MeanCost_B'], marker='^', linestyle='--', color='#95a5a6', label='Mean Cost')
    plt.title('Impact of ISRU Coverage on Annual Logistics Budget')
    plt.xlabel('ISRU Coverage Ratio ($\gamma$)')
    plt.ylabel('Annual Cost (Billion USD)')
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.savefig(os.path.join(OUTPUT_DIR, "fig_isru_gamma_vs_varcost.png"))
    plt.close()

    print(f"\nSaved plots and data to {OUTPUT_DIR}")

if __name__ == "__main__":
    main()
