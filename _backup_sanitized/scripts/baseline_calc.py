"""
P0-2: Baseline Calculation Script for MCM 2026 Problem B
Calculates rough timeline and costs for Scenarios A and B based on constants.
"""

import sys
import os

# Ensure project root is in path
sys.path.append(os.getcwd())

from configs.constants import ProblemConstraints, Assumptions, Scenarios
from src.utils.units import format_currency, format_mass

def calc_scenario_a():
    """
    Scenario A: Space Elevator Only
    Limit: Harbour throughput
    """
    print("\n--- Scenario A: Space Elevator System ---")

    total_capacity_per_year = ProblemConstraints.NUM_HARBOURS * ProblemConstraints.ELEVATOR_CAPACITY_TONS_PER_YEAR_PER_PORT

    years_needed = ProblemConstraints.TARGET_MASS_TONS / total_capacity_per_year

    # Cost: OPEX (Earth->Apex) + Transfer (Apex->Moon)
    cost_per_ton = Assumptions.ELEVATOR_OPEX_PER_TON_USD + Assumptions.APEX_TO_MOON_COST_PER_TON_USD
    total_cost = ProblemConstraints.TARGET_MASS_TONS * cost_per_ton

    print(f"System Capacity: {format_mass(total_capacity_per_year)} / year")
    print(f"Time to completion: {years_needed:.2f} years")
    print(f"Estimated OPEX: {format_currency(total_cost)}")
    print(f"Completion Year: {ProblemConstraints.START_YEAR + years_needed:.1f}")

def calc_scenario_b():
    """
    Scenario B: Rockets Only
    Limit: Launch frequency and Launch sites
    """
    print("\n--- Scenario B: Traditional Rockets ---")

    avg_payload = Assumptions.ROCKET_PAYLOAD_AVG_TONS
    launches_per_year = ProblemConstraints.NUM_LAUNCH_SITES * Assumptions.LAUNCHES_PER_SITE_PER_YEAR

    mass_per_year = launches_per_year * avg_payload

    years_needed = ProblemConstraints.TARGET_MASS_TONS / mass_per_year
    total_launches = ProblemConstraints.TARGET_MASS_TONS / avg_payload

    total_cost = total_launches * Assumptions.ROCKET_LAUNCH_COST_USD

    print(f"assumed Launches/Year: {launches_per_year} ({Assumptions.LAUNCHES_PER_SITE_PER_YEAR} per site)")
    print(f"Mass Transport/Year: {format_mass(mass_per_year)}")
    print(f"Total Launches Required: {total_launches:,.0f}")
    print(f"Time to completion: {years_needed:.2f} years")
    print(f"Estimated Cost: {format_currency(total_cost)}")
    print(f"Completion Year: {ProblemConstraints.START_YEAR + years_needed:.1f}")

def main():
    print(f"Target: Transport {format_mass(ProblemConstraints.TARGET_MASS_TONS)} to Moon Colony.")
    print(f"Start Year: {ProblemConstraints.START_YEAR}")

    calc_scenario_a()
    calc_scenario_b()

if __name__ == "__main__":
    main()
