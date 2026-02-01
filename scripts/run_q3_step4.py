import sys
import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

# Ensure project root is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from configs.constants import WaterDemand, WaterPolicy, Elevator, Rocket, Cost, RELIABILITY_PRESETS
from src.q3 import analytics, simulation

OUTPUT_DIR = "outputs/q3/step4"
os.makedirs(OUTPUT_DIR, exist_ok=True)

def run_step4_cost_analysis():
    print("Running Step 4: Cost Analysis (Severe Scenario, Year 1)...")

    # 1. Define Parameters
    eta = 0.98
    P = WaterDemand.POPULATION
    w = WaterDemand.W_L_PER_PERSON_DAY

    # Demand Calculation
    metrics = analytics.calculate_demand(P, w, eta)
    d_day_ton = metrics['daily_tons']
    annual_demand_ton = metrics['annual_tons']
    print(f"  Annual Demand: {annual_demand_ton:,.0f} tons (eta={eta})")

    # Policy
    L_safe = 15
    B_buffer = 15
    initial_inv = (L_safe + B_buffer) * d_day_ton
    policy = WaterPolicy(L_SAFE_DAYS=L_safe, B_BUFFER_DAYS=B_buffer, USE_DYNAMIC_SURGE=True)

    # Reliability
    preset_name = "SEVERE"
    preset = RELIABILITY_PRESETS[preset_name]

    # Costs (Mean Values)
    c_E_per_kg = np.mean(Cost.ELEVATOR_OPEX_PER_KG_RANGE_USD)
    c_E_per_ton = c_E_per_kg * 1000.0

    C_L_launch = np.mean(Cost.ROCKET_LAUNCH_COST_2050_RANGE_USD)
    q_payload = np.mean(Rocket.PAYLOAD_RANGE_TON)

    beta_apex = np.mean(Cost.BETA_APEX_RANGE)

    # Apex Cost
    rocket_cost_per_ton_direct = C_L_launch / q_payload
    apex_cost_per_ton = beta_apex * rocket_cost_per_ton_direct

    print(f"  Cost Parameters (Mean):")
    print(f"    Elevator Lift OPEX: ${c_E_per_ton:,.2f}/ton")
    print(f"    Rocket Launch Cost: ${C_L_launch:,.2f}/launch (Payload: {q_payload:.1f}t)")
    print(f"    Rocket Cost/Ton:    ${rocket_cost_per_ton_direct:,.2f}/ton")
    print(f"    Apex Discount Beta: {beta_apex:.3f}")
    print(f"    Apex Transfer Cost: ${apex_cost_per_ton:,.2f}/ton")

    # Simulation Config
    C_E_nominal_day = (Elevator.NUM_HARBOURS * Elevator.CAPACITY_PER_HARBOUR_TPY) / 365.0
    rocket_config = {
        'K': Rocket.MAX_SITES,
        'q': q_payload,
        'r_base': Rocket.R_BASE
    }

    N_ITER = 100
    print(f"  Simulating {N_ITER} years...")

    results_xE = []
    results_xR = []

    for i in range(N_ITER):
        res = simulation.simulate_inventory_trajectory(
            duration_days=365,
            initial_inventory_tons=initial_inv,
            daily_demand_tons=d_day_ton,
            daily_supply_cap_elevator_tons=C_E_nominal_day,
            rocket_config=rocket_config,
            preset=preset,
            policy=policy
        )
        results_xE.append(res['total_shipped_E'])
        results_xR.append(res['total_shipped_R'])

    avg_xE = np.mean(results_xE)
    avg_xR = np.mean(results_xR)

    print(f"  Average Shipments per Year:")
    print(f"    Elevator (X_E): {avg_xE:,.0f} tons")
    print(f"    Rocket   (X_R): {avg_xR:,.0f} tons")
    print(f"    Total Supply:   {avg_xE + avg_xR:,.0f} tons")
    print(f"    (Demand: {annual_demand_ton:,.0f} tons)")

    # Cost Calculation
    # Elevator Cost = X_E * c_E + X_E * ApexCostPerTon
    cost_elevator_lift = avg_xE * c_E_per_ton
    cost_elevator_apex = avg_xE * apex_cost_per_ton
    total_cost_elevator = cost_elevator_lift + cost_elevator_apex

    # Rocket Cost = (X_R / q) / s_R * C_L
    s_R = 1.0 - preset.P_R
    num_successful_launches = avg_xR / q_payload
    num_attempts = num_successful_launches / s_R
    total_cost_rocket = num_attempts * C_L_launch

    total_annual_cost = total_cost_elevator + total_cost_rocket

    # --- Output to CSV ---
    summary_data = {
        'Scenario': [preset_name],
        'Eta': [eta],
        'Avg_XE_Tons': [avg_xE],
        'Avg_XR_Tons': [avg_xR],
        'Cost_Elevator_Total': [total_cost_elevator],
        'Cost_Rocket_Total': [total_cost_rocket],
        'Total_Annual_Cost': [total_annual_cost],
        'Rocket_Attempts': [num_attempts],
        'Rocket_Success_Rate': [s_R]
    }
    df_summary = pd.DataFrame(summary_data)
    csv_path = os.path.join(OUTPUT_DIR, "step4_summary.csv")
    df_summary.to_csv(csv_path, index=False)
    print(f"Saved Step 4 summary data to {csv_path}")

    # --- Visualization ---

    # Plot 1: Cost Breakdown (Stacked Bar)
    plt.figure(figsize=(8, 6))
    components = [cost_elevator_lift, cost_elevator_apex, total_cost_rocket]
    labels = ['Elevator Lift Ops', 'Apex Transfer', 'Rocket Launches']
    colors = ['#4caf50', '#81c784', '#f44336'] # Green shades for elevator, Red for rocket

    # Create single stacked bar
    bottom = 0
    for val, label, color in zip(components, labels, colors):
        plt.bar('Annual Cost', val, bottom=bottom, color=color, label=label, width=0.5)
        # Add text label in middle of bar segment
        if val > 0:
            plt.text('Annual Cost', bottom + val/2, f"${val/1e9:.1f}B",
                     ha='center', va='center', color='white', fontweight='bold')
        bottom += val

    plt.ylabel('Cost (USD)')
    plt.title(f'Annual Water Supply Cost Structure (Total: ${total_annual_cost/1e9:.1f}B)')
    plt.legend(loc='upper right')
    plt.grid(True, axis='y', alpha=0.3)

    # Format y-axis to Billions
    current_values = plt.gca().get_yticks()
    plt.gca().set_yticklabels(['${:,.0f}B'.format(x/1e9) for x in current_values])

    plt.savefig(os.path.join(OUTPUT_DIR, "fig_step4_cost_breakdown.png"))
    plt.close()

    # Plot 2: Asymmetry Dual-Axis Chart
    # Compare Volume Share vs Cost Share
    total_mass = avg_xE + avg_xR
    mass_shares = [avg_xE / total_mass, avg_xR / total_mass]

    total_cost = total_annual_cost
    cost_shares = [total_cost_elevator / total_cost, total_cost_rocket / total_cost]

    categories = ['Elevator System', 'Rocket System']
    x = np.arange(len(categories))
    width = 0.35

    fig, ax1 = plt.subplots(figsize=(10, 6))

    # Mass Share Bars (Left Axis)
    rects1 = ax1.bar(x - width/2, mass_shares, width, label='Transport Mass Share', color='#2196f3', alpha=0.8)
    ax1.set_ylabel('Share of Total Mass Transported', color='#1565c0')
    ax1.set_ylim(0, 1.1)
    ax1.tick_params(axis='y', labelcolor='#1565c0')

    # Cost Share Bars (Right Axis - actually same scale 0-1 but distinct visual)
    # To make it "Dual Axis" effectively, we can just use grouped bars on same scale
    # since both are percentages (0.0 - 1.0).
    # Let's keep one axis but group them to show the inversion.

    rects2 = ax1.bar(x + width/2, cost_shares, width, label='Share of Total Cost', color='#ff9800', alpha=0.8)

    # Add labels
    def autolabel(rects):
        for rect in rects:
            height = rect.get_height()
            ax1.annotate(f'{height:.1%}',
                        xy=(rect.get_x() + rect.get_width() / 2, height),
                        xytext=(0, 3),  # 3 points vertical offset
                        textcoords="offset points",
                        ha='center', va='bottom')

    autolabel(rects1)
    autolabel(rects2)

    ax1.set_xticks(x)
    ax1.set_xticklabels(categories)
    ax1.set_title('Structural Asymmetry: Mass vs. Cost (Severe Scenario)')
    ax1.legend(loc='best')
    ax1.grid(True, axis='y', alpha=0.3)

    plt.savefig(os.path.join(OUTPUT_DIR, "fig_step4_asymmetry_dualaxis.png"))
    plt.close()

    # Plot 3: Cost Distribution Boxplot (Optional but good)
    # Calculate array of total costs
    costs_arr = []
    for i in range(len(results_xE)):
        # Recalculate cost for each simulation instance
        xe = results_xE[i]
        xr = results_xR[i]

        c_elev = xe * (c_E_per_ton + apex_cost_per_ton)

        # Approximate attempts for this instance (using average success rate)
        # In a real step 5 we'd track actual failures, but here we estimate
        attempts = (xr / q_payload) / s_R
        c_rock = attempts * C_L_launch

        costs_arr.append(c_elev + c_rock)

    plt.figure(figsize=(8, 6))
    sns.boxplot(y=costs_arr, color='skyblue')
    plt.ylabel('Annual Cost (USD)')
    plt.title('Annual Cost Distribution (N=100 Simulations)')

    # Format y-axis
    current_values = plt.gca().get_yticks()
    plt.gca().set_yticklabels(['${:,.1f}B'.format(x/1e9) for x in current_values])

    plt.grid(True, alpha=0.3)
    plt.savefig(os.path.join(OUTPUT_DIR, "fig_step4_cost_boxplot.png"))
    plt.close()

    print("\n" + "="*40)
    print("FINAL COST ANALYSIS (SEVERE SCENARIO)")
    print("="*40)
    print(f"Elevator Cost: ${total_cost_elevator:,.0f}")
    print(f"Rocket Cost:   ${total_cost_rocket:,.0f}")
    print("-" * 40)
    print(f"TOTAL ANNUAL COST: ${total_annual_cost:,.0f}")
    print("="*40)

if __name__ == "__main__":
    run_step4_cost_analysis()
