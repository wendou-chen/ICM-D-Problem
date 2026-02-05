import math

def elevator_total_capacity_tpy(num_harbours: int, cap_per_harbour_tpy: float) -> float:
    """
    Calculate total annual capacity for the Space Elevator system.
    C_E = H * C_p
    """
    return num_harbours * cap_per_harbour_tpy

def rocket_annual_capacity_tpy(K: int, r_daily: int, payload_ton: float) -> float:
    """
    Calculate total annual capacity for the Rocket system.
    C_R = K * r * 365 * q
    """
    return K * r_daily * 365.0 * payload_ton

def rocket_launches_required(total_mass_ton: float, payload_ton: float) -> int:
    """
    Calculate total number of launches required.
    N_B = ceil(M / q)
    """
    if payload_ton <= 0:
        raise ValueError("Payload must be positive")
    return math.ceil(total_mass_ton / payload_ton)

def completion_time_years(total_mass_ton: float, annual_capacity_tpy: float) -> float:
    """
    Calculate time to complete transport.
    T = M / C_annual
    """
    if annual_capacity_tpy <= 0:
        return float('inf')
    return total_mass_ton / annual_capacity_tpy
