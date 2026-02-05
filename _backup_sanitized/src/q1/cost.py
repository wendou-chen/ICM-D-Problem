import math
from typing import Dict, Tuple

def cost_scenario_A(total_mass_ton: float,
                    c_elevator_per_ton: float,
                    c_apex_launch: float,
                    q_apex_ton: float) -> float:
    """
    Cost for Scenario A (Elevator Only).
    Cost = (C_elevator_ops + C_apex_launch_ops)
    Note: Usually Apex launch is cheaper.
    """
    # Number of transfers from Apex to Moon
    if q_apex_ton <= 0: return float('inf')
    n_transfers = math.ceil(total_mass_ton / q_apex_ton)
    
    cost_elevator = total_mass_ton * c_elevator_per_ton
    cost_apex_transfer = n_transfers * c_apex_launch
    
    return cost_elevator + cost_apex_transfer

def cost_scenario_B(n_launches: int, c_launch: float) -> float:
    """
    Cost for Scenario B (Rocket Only).
    Cost = N_launches * C_launch
    """
    return n_launches * c_launch

def cost_scenario_C(alpha: float,
                    total_mass_ton: float,
                    c_elevator_per_ton: float,
                    c_apex_per_ton: float,
                    c_rocket_per_ton: float) -> float:
    """
    Cost for Scenario C (Hybrid).
    alpha: Fraction of mass via Elevator (0..1)
    
    Cost = Cost_Elevator(alpha * M) + Cost_Rocket((1-alpha) * M)
    """
    mass_elevator = alpha * total_mass_ton
    mass_rocket = (1.0 - alpha) * total_mass_ton
    
    cost_e = mass_elevator * (c_elevator_per_ton + c_apex_per_ton)
    cost_r = mass_rocket * c_rocket_per_ton
    
    return cost_e + cost_r
