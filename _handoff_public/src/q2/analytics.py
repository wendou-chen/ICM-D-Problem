import numpy as np
from configs.constants import ReliabilityPreset

def elevator_effective_capacity(C_E_nominal: float, A_E: float) -> float:
    """
    Calculate effective elevator capacity.
    C_E_tilde = C_E * A_E
    """
    return C_E_nominal * A_E

def rocket_f_eff(r: int, p_R: float, tau_reset: int) -> float:
    """
    Calculate rocket effective efficiency factor f_eff.
    s = 1 - p_R
    E_S = sum_{i=1..r} s^i  (Note: strictly following prompt formula)
    E_L = 1 + tau_reset * (1 - s^r)
    f_eff = E_S / E_L
    """
    s = 1.0 - p_R
    
    # E_S = s + s^2 + ... + s^r
    # Geometric series: s * (1 - s^r) / (1 - s)
    if abs(1 - s) < 1e-9: # s approx 1
        E_S = float(r)
    else:
        E_S = s * (1 - s**r) / (1 - s)
        
    E_L = 1.0 + tau_reset * (1.0 - s**r)
    
    if E_L == 0:
        return 0.0
        
    return E_S / E_L

def rocket_effective_capacity(K: int, r: int, q: float, A_B: float, p_R: float, tau_reset: int) -> float:
    """
    Calculate effective rocket capacity (tons/year).
    C_R_tilde = K * q * A_B * f_eff * 365
    """
    f = rocket_f_eff(r, p_R, tau_reset)
    return K * q * A_B * f * 365.0

def alpha_star(C_E_tilde: float, C_R_tilde: float) -> float:
    """
    Calculate optimal share for elevator alpha*.
    If both 0, return 0.
    alpha* = C_E_tilde / (C_E_tilde + C_R_tilde)
    """
    total = C_E_tilde + C_R_tilde
    if total <= 0:
        return 0.0
    return C_E_tilde / total

def feasible(C_E_tilde: float, C_R_tilde: float, M: float, T_target_years: float) -> bool:
    """
    Check if the configuration is analytically feasible within target time.
    (C_E_tilde + C_R_tilde) >= M / T_target_years
    """
    total_capacity_per_year = C_E_tilde + C_R_tilde
    required_capacity = M / T_target_years
    return total_capacity_per_year >= required_capacity
