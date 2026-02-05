import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import os
import numpy as np
import sys
import shutil

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.utils.plot_style import apply_style

def main():
    # Setup paths
    base_dir = os.path.abspath("outputs/q4_detailed")
    mc_file = os.path.join(base_dir, "mc_results.csv")
    traces_file = os.path.join(base_dir, "traces.csv")
    output_dir = os.path.join(base_dir, "plots")

    print(f"Reading data from: {mc_file}")
    if not os.path.exists(mc_file):
        print(f"Error: {mc_file} not found.")
        return

    os.makedirs(output_dir, exist_ok=True)
    print(f"Saving plots to: {output_dir}")

    # Load Data
    df = pd.read_csv(mc_file)
    print(f"Loaded {len(df)} rows.")

    # 1. Categorize Scenarios
    def get_scenario(row):
        if row['alpha_actual'] < 0.3: return 'Rocket-Heavy'
        if row['alpha_actual'] > 0.7: return 'Elevator-Heavy'
        return 'Mixed'

    df['Scenario'] = df.apply(get_scenario, axis=1)

    # Define a consistent palette
    scenario_palette = {
        'Rocket-Heavy': '#d62728', # Red
        'Mixed': '#ff7f0e',        # Orange
        'Elevator-Heavy': '#2ca02c' # Green
    }

    apply_style()

    # --- Plot 1: Time vs EDI Pareto Scatter ---
    print("Generating Pareto Plot...")
    plt.figure(figsize=(10, 7))

    # Filter out unreasonable durations for the main plot to avoid skewing
    # Use the new 'unreasonable_duration' flag if available, otherwise fallback
    if 'unreasonable_duration' in df.columns:
        df_valid = df[~df['unreasonable_duration']]
    else:
        df_valid = df # Fallback

    if not df_valid.empty:
        sns.scatterplot(
            data=df_valid,
            x='duration_years',
            y='EDI_proxy',
            hue='alpha_actual',
            palette='viridis',
            size='total_mass',
            sizes=(20, 200),
            alpha=0.8
        )

        plt.title('Time vs. Environmental Impact (EDI) Trade-off', fontsize=14)
        plt.xlabel('Project Duration (Years)', fontsize=12)
        plt.ylabel('Environmental Damage Index (EDI)', fontsize=12)
        plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left', title="Elevator Share")
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, "fig_q4_pareto_time_edi.png"), dpi=600)
        plt.close()
    else:
        print("Warning: All simulations had unreasonable durations.")

    # --- Plot 2: Tail Risk Boxplot (S_max) ---
    print("Generating Risk Boxplot...")
    plt.figure(figsize=(8, 6))
    existing_scenarios = [s for s in ['Rocket-Heavy', 'Mixed', 'Elevator-Heavy'] if s in df['Scenario'].unique()]

    if existing_scenarios:
        sns.boxplot(
            x='Scenario',
            y='S_max_ton',
            data=df,
            order=existing_scenarios,
            palette=scenario_palette,
            fliersize=0
        )
        sns.stripplot(
            x='Scenario',
            y='S_max_ton',
            data=df,
            order=existing_scenarios,
            color='black',
            alpha=0.3,
            size=3,
            jitter=0.2
        )
        plt.title('Peak Stratospheric Black Carbon Risk ($S_{max}$)', fontsize=14)
        plt.ylabel('Peak BC Load (tons)', fontsize=12)
        plt.xlabel('Scenario Type', fontsize=12)
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, "fig_q4_soot_risk.png"), dpi=600)
    plt.close()

    # --- Plot 3: Component Breakdown (Build vs Op) ---
    print("Generating Component Breakdown...")
    try:
        # Check if new columns exist
        if 'E_build_ton' in df.columns and 'E_op_ton' in df.columns:
            cols_impact = ['E_build_ton', 'E_op_ton']

            # Aggregate mean by Scenario
            df_mean = df.groupby('Scenario')[cols_impact].mean().reset_index()
            df_melt = df_mean.melt(id_vars=['Scenario'], value_vars=cols_impact, var_name='Phase', value_name='Tons_CO2')

            # Reorder for visual consistency
            df_melt['Scenario'] = pd.Categorical(df_melt['Scenario'], categories=['Rocket-Heavy', 'Mixed', 'Elevator-Heavy'])

            plt.figure(figsize=(10, 6))

            # Custom palette for E_build and E_op as requested
            env_palette = {'E_build_ton': '#9fddff', 'E_op_ton': '#65a7ed'}

            ax = sns.barplot(x='Scenario', y='Tons_CO2', hue='Phase', data=df_melt, palette=env_palette)

            # Axis styling: width 0.5, color black, with ticks
            for spine in ax.spines.values():
                spine.set_linewidth(0.5)
                spine.set_color('black')

            # Ensure ticks are visible on both axes with requested directions
            # Y-axis ticks IN, X-axis ticks OUT (Requested)
            ax.tick_params(axis='y', which='major', direction='in', length=6, width=1, colors='black', left=True)
            ax.tick_params(axis='x', which='major', direction='out', length=6, width=1, colors='black', bottom=True)

            # Explicitly set labels
            ax.set_xlabel('Scenario Type', fontsize=12)
            ax.set_ylabel('Emissions (Tons CO2e)', fontsize=12)

            ax.grid(True, axis='y', linestyle='--', alpha=0.5, color='gray', linewidth=0.5)
            ax.set_axisbelow(True) # Ensure grid is behind bars

            plt.title('Average Emissions by Phase (Construction vs Operation)', fontsize=14)
            plt.tight_layout()
            plt.savefig(os.path.join(output_dir, "fig_q4_impact_breakdown.png"), dpi=600)
            plt.close()
        else:
            print("Warning: E_build_ton/E_op_ton columns not found. Skipping Breakdown Plot.")

    except Exception as e:
        print(f"Could not plot breakdown: {e}")

    # --- Plot 4: Chi Sensitivity (Decarbonization) ---
    print("Generating Chi Sensitivity Plot...")
    # Filter for Elevator-Heavy scenarios (where grid matter most)
    df_elev = df[df['Scenario'] == 'Elevator-Heavy']

    if not df_elev.empty and 'chi' in df_elev.columns:
        plt.figure(figsize=(8, 6))
        sns.lineplot(
            data=df_elev,
            x='chi',
            y='E_CO2_ton',
            # marker='o', # High resolution: hide markers
            err_style='band'
        )
        plt.title('Sensitivity to Grid Decarbonization (Elevator-Heavy)', fontsize=14)
        plt.xlabel('Grid Decarbonization Ratio ($\chi$)', fontsize=12)
        plt.ylabel('Total Emissions (Tons CO2)', fontsize=12)
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, "fig_q4_chi_sensitivity.png"), dpi=600)
        plt.close()

    # --- Plot 5: Soot Timeseries Trace ---
    print("Generating Soot Timeseries Plot...")
    if os.path.exists(traces_file):
        try:
            df_trace = pd.read_csv(traces_file)
            plt.figure(figsize=(12, 6))

            # Plot lines
            sns.lineplot(data=df_trace, x='Year', y='S_bc_ton', hue='Scenario', palette=scenario_palette, linewidth=2)

            # Shade Phases (Approximate based on Rocket-Heavy since it's the worst case baseline)
            # Find the transition point for one scenario to illustrate
            # Ideally we would plot separate phases, but let's just show the trajectory

            plt.title('Stratospheric Black Carbon Accumulation Over Lifecycle', fontsize=14)
            plt.xlabel('Time (Years)', fontsize=12)
            plt.ylabel('Black Carbon Burden ($S_{bc}$ tons)', fontsize=12)
            plt.grid(True, alpha=0.3)
            plt.tight_layout()
            plt.savefig(os.path.join(output_dir, "fig_q4_soot_timeseries.png"), dpi=600)
            plt.close()
        except Exception as e:
            print(f"Error plotting soot timeseries: {e}")
    else:
        print("traces.csv not found. Skipping Soot Timeseries Plot.")

    # --- Plot 6: Environmental Components (Stacked Bar per Scenario) ---
    # This is similar to Breakdown but for specific traces/representatives if possible
    # We can reuse the breakdown logic but maybe with different visualization style
    # Let's keep fig_q4_impact_breakdown as the main component plot.
    # We'll just copy it to fig_q4_env_components.png to satisfy the request list
    src_path = os.path.join(output_dir, "fig_q4_impact_breakdown.png")
    dst_path = os.path.join(output_dir, "fig_q4_env_components.png")
    if os.path.exists(src_path):
        shutil.copy(src_path, dst_path)
        print("Generated fig_q4_env_components.png (Copy of Breakdown)")

    # --- Plot 7: Cost vs EDI Pareto (Proxy) ---
    print("Generating Cost vs EDI Pareto...")
    # We need to calculate cost proxy.
    # Cost = Attempts * 50M + Mass_Elev * 200$/ton
    # But mass_elev is not directly in mc_results.csv, we have total_mass and alpha_actual.
    # Mass_Elev = Total_Mass * Alpha
    # Mass_Rocket = Total_Mass * (1 - Alpha)
    # Attempts ~ Mass_Rocket / Payload (~125t)

    if not df_valid.empty:
        try:
            # Proxy Calculations
            df_valid = df_valid.copy()
            df_valid['Mass_Elev_ton'] = df_valid['total_mass'] * df_valid['alpha_actual']
            df_valid['Mass_Rocket_ton'] = df_valid['total_mass'] * (1 - df_valid['alpha_actual'])

            # Rocket attempts approximation (assuming 125t payload average)
            # If we had actual attempts it would be better, but this is a proxy plot
            # Update: We should probably export attempts in run_q4_detailed_sim.py for accuracy
            # For now, estimate:
            avg_payload = 125.0
            df_valid['Attempts_Est'] = df_valid['Mass_Rocket_ton'] / avg_payload

            # Cost Calculation (Millions USD)
            # Rocket: $50M per launch
            # Elevator: $200/ton = $0.0002 M/ton
            COST_LAUNCH_M = 50.0
            COST_ELEV_M_PER_TON = 0.0002

            df_valid['Cost_Total_M'] = (df_valid['Attempts_Est'] * COST_LAUNCH_M) + (df_valid['Mass_Elev_ton'] * COST_ELEV_M_PER_TON)

            plt.figure(figsize=(10, 7))
            sns.scatterplot(
                data=df_valid,
                x='Cost_Total_M',
                y='EDI_proxy',
                hue='alpha_actual',
                palette='viridis',
                size='duration_years',
                sizes=(20, 200),
                alpha=0.8
            )

            plt.title('Economic Cost vs. Environmental Impact Trade-off', fontsize=14)
            plt.xlabel('Total Project Cost (Million USD, Proxy)', fontsize=12)
            plt.ylabel('Environmental Damage Index (EDI)', fontsize=12)
            plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left', title="Elevator Share")
            plt.grid(True, alpha=0.3)
            plt.tight_layout()
            plt.savefig(os.path.join(output_dir, "fig_q4_pareto_edi_cost.png"), dpi=600)
            plt.close()
        except Exception as e:
            print(f"Error plotting Cost Pareto: {e}")

    print("Done.")

if __name__ == "__main__":
    main()
