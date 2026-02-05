import numpy as np
from typing import Dict, Any, Tuple
from configs.constants import ReliabilityPreset, Problem, Elevator, Rocket

def simulate_once(
    policy: str,
    M: float,
    preset: ReliabilityPreset,
    elevator_capacity_nominal_tpy: float,
    rocket_config: Dict[str, Any],
    gamma: float = 1.0
) -> float:
    """
    Run one simulation of the delivery process.

    Args:
        policy: 'fixed_alpha_star' or 'dynamic_backup'
        M: Total mass target (tons)
        preset: ReliabilityPreset parameters
        elevator_capacity_nominal_tpy: Nominal annual capacity of elevator system
        rocket_config: {
            'K': int,       # Number of sites
            'q': float,     # Payload per launch
            'r_base': int,  # Base daily rate
            'r_max': int    # Max daily rate (for backup)
        }
        gamma: Surge multiplier for dynamic_backup (default 1.0)

    Returns:
        Completion time in years.
    """

    # Unpack config
    K = rocket_config['K']
    q = rocket_config['q']
    r_base = rocket_config['r_base']
    r_max = rocket_config.get('r_max', r_base) # Default to r_base if not specified

    # Elevator parameters
    lam, mu = preset.lambda_mu
    daily_cap_elevator = elevator_capacity_nominal_tpy / 365.0

    # State initialization
    mass_delivered = 0.0
    day = 0

    elevator_down_days = 0
    pad_down_days = np.zeros(K, dtype=int)

    while mass_delivered < M:
        day += 1

        # --- Elevator Step ---
        elevator_delivered = 0.0

        if elevator_down_days > 0:
            elevator_down_days -= 1
        else:
            # Check for failure
            # Prob of failure today approx 1 - exp(-lambda * 1)
            if np.random.random() < (1.0 - np.exp(-lam)):
                # Failed! Determine downtime.
                downtime = int(np.ceil(np.random.exponential(scale=preset.MTTR_E_DAYS)))
                elevator_down_days = downtime
            else:
                # Operational
                elevator_delivered = daily_cap_elevator

        # --- Rocket Step ---
        rocket_delivered = 0.0

        # Determine r for today (float)
        r_today = float(r_base)
        if policy == 'dynamic_backup':
            if elevator_down_days > 0:
                # Apply gamma surge, capped by r_max
                # r_today = min(r_max, gamma * r_base)
                # But physically r_max is the limit.
                # Interpreting prompt: r_surge = min(r_max, gamma * r_base) or similar.
                # The prompt says: r_surge = min(r_max, gamma, r_base) ? No, gamma is multiplier.
                # Prompt: r_surge = min(r_max, gamma, r_base) -> this looks like a typo in prompt or specific logic.
                # Prompt text: r_surge = min(r_max, gamma * r_base) (implied).
                # Actually prompt says: r_surge = min(r_max, gamma, r_base) -- wait, gamma is multiplier?
                # "設平时每基地日发射次数 r_base，电梯停机时提升到：r_surge = min(r_max, gamma * r_base)"
                # Let's assume gamma is the multiplier on r_base.
                r_surge = min(float(r_max), gamma * r_base)
                r_today = r_surge

        # Handle fractional attempts
        r_int = int(r_today)
        r_frac = r_today - r_int
        r_attempts = r_int
        if r_frac > 0 and np.random.random() < r_frac:
            r_attempts += 1

        # Iterate over pads
        for k in range(K):
            if pad_down_days[k] > 0:
                pad_down_days[k] -= 1
                continue

            # Check base availability (weather)
            if np.random.random() > preset.A_B:
                # Weather bad, no launch, but doesn't break pad
                continue

            # Attempt launches
            # Sequential attempts up to r_attempts
            for _ in range(r_attempts):
                if np.random.random() < preset.P_R:
                    # Failure!
                    pad_down_days[k] = preset.TAU_RESET_DAYS
                    break # Stop using this pad today and for reset period
                else:
                    # Success
                    rocket_delivered += q

        # --- Update Total ---
        mass_delivered += elevator_delivered + rocket_delivered

        # Safety break for infinite loops (e.g. if everything broken forever)
        if day > 1000 * 365: # 1000 years - increased limit to avoid clipping tail risks
            return 1000.0

    return day / 365.0
