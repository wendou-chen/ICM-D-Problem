import numpy as np
from typing import Dict, Any, List
from configs.constants import ReliabilityPreset, Rocket, WaterPolicy

def simulate_inventory_trajectory(
    duration_days: int,
    initial_inventory_tons: float,
    daily_demand_tons: float,
    daily_supply_cap_elevator_tons: float,
    rocket_config: Dict[str, Any],
    preset: ReliabilityPreset,
    policy: WaterPolicy,
    phi_e: float = 1.0,
    phi_r: float = 1.0,
    return_trajectory: bool = False,
    step5_mode: bool = False,
    risk_params: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    Simulate water inventory levels.
    Supports standard mode (Q2 logic) and Step 5 Risk mode (Burst logic + detailed tracking).
    """
    # Unpack config
    K = rocket_config['K']
    q = rocket_config['q']
    r_base = rocket_config['r_base']
    
    # State initialization
    inventory = initial_inventory_tons
    history_inv = [inventory]
    
    elevator_down_days = 0
    pad_down_days = np.zeros(K, dtype=int)
    
    stockout_days = 0
    min_inventory = initial_inventory_tons
    
    # Tracking
    total_shipped_E = 0.0
    total_shipped_R = 0.0
    total_attempts_R = 0
    total_failures_R = 0
    elevator_up_days = 0
    
    # Risk Parameters (Default to preset if not Step 5)
    if step5_mode and risk_params:
        p_E_fail = risk_params['p_E_fail_daily']
        rep_min = risk_params['repair_days_min']
        rep_max = risk_params['repair_days_max']
        p_R_fail = risk_params['p_R_fail_per_launch']
    else:
        # Fallback to Q2 preset logic (Exponential)
        lam, mu = preset.lambda_mu
    
    # Simulation Loop
    for _ in range(duration_days):
        
        # --- 1. Determine Needs (Policy A) ---
        target_stock_S = (policy.L_SAFE_DAYS + policy.B_BUFFER_DAYS) * daily_demand_tons
        need = max(0.0, target_stock_S - inventory)
        
        # --- 2. Calculate Available Capacity ---
        
        # Elevator Capacity
        cap_E = 0.0
        
        if elevator_down_days > 0:
            elevator_down_days -= 1
        else:
            # Check for failure
            failed = False
            if step5_mode:
                if np.random.random() < p_E_fail:
                    failed = True
                    downtime = int(np.random.randint(rep_min, rep_max + 1))
            else:
                if np.random.random() < (1.0 - np.exp(-lam)):
                    failed = True
                    downtime = int(np.ceil(np.random.exponential(scale=preset.MTTR_E_DAYS)))
            
            if failed:
                elevator_down_days = downtime
            else:
                cap_E = daily_supply_cap_elevator_tons * phi_e
                elevator_up_days += 1
        
        # Rocket Capacity
        # In Step 5, we model discrete launch attempts for Costing
        # Capacity estimate for planning:
        r_eff = float(r_base) * phi_r
        r_int = int(r_eff)
        r_frac = r_eff - r_int
        r_attempts = r_int + (1 if np.random.random() < r_frac else 0)
        
        # --- 3. Determine Actual Shipments ---
        x_E = min(need, cap_E)
        
        remaining_need = need - x_E
        x_R = 0.0
        
        # Rocket Execution
        # Try to ship 'remaining_need' using available pads
        launches_needed = int(np.ceil(remaining_need / q)) if remaining_need > 0 else 0
        
        if launches_needed > 0:
            for k in range(K):
                if launches_needed == 0: break
                if pad_down_days[k] > 0:
                    pad_down_days[k] -= 1
                    continue
                
                # Check weather if using preset (Step 5 might simplify or keep it)
                if not step5_mode and np.random.random() > preset.A_B:
                    continue
                    
                # Attempt launches
                for _ in range(r_attempts):
                    if launches_needed == 0: break
                    
                    total_attempts_R += 1
                    
                    fail_prob = p_R_fail if step5_mode else preset.P_R
                    
                    if np.random.random() < fail_prob:
                        total_failures_R += 1
                        if not step5_mode:
                            pad_down_days[k] = preset.TAU_RESET_DAYS
                            break # Pad resets in Q2 model
                        # In Step 5, maybe just payload loss? 
                        # Guide says "Binomial", let's assume just loss for simplicity unless reset needed.
                        # Let's keep reset for consistency if not specified.
                        pad_down_days[k] = 5 # Arbitrary short reset for Step 5 or keep Q2 logic
                        break 
                    else:
                        x_R += q
                        launches_needed -= 1
        else:
             for k in range(K):
                if pad_down_days[k] > 0:
                    pad_down_days[k] -= 1

        total_shipped_E += x_E
        total_shipped_R += x_R
        
        # --- 4. Update Inventory ---
        inventory += (x_E + x_R) - daily_demand_tons
        
        if inventory < 0:
            stockout_days += 1
            
        if inventory < min_inventory:
            min_inventory = inventory
            
        history_inv.append(inventory)
        
    result = {
        'min_inventory': min_inventory,
        'stockout_days': stockout_days,
        'final_inventory': inventory,
        'total_shipped_E': total_shipped_E,
        'total_shipped_R': total_shipped_R,
        'total_attempts_R': total_attempts_R,
        'total_failures_R': total_failures_R,
        'elevator_up_days': elevator_up_days
    }
    
    if return_trajectory:
        result['trajectory'] = history_inv
        
    return result
