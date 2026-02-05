# Burst Failure Simulation

**Extracted:** 2026-02-01
**Context:** Discrete Event Simulation (DES) or time-step simulations where component failures result in multi-step downtime (e.g., repair windows).

## Problem
Standard probabilistic failure models (e.g., `random() < p_fail`) often simulate instantaneous failures that resolve in the next time step. This fails to capture "Burst Failures" where a system goes offline for a significant duration (Mean Time To Repair - MTTR), which has a much more severe impact on buffers and inventory than frequent short failures.

## Solution
Implement a state-machine approach within the time-step loop:
1.  Track a `remaining_downtime` counter.
2.  If `remaining_downtime > 0`: The system is down; decrement counter; output 0 capacity.
3.  If `remaining_downtime == 0`:
    *   Check for *new* failure using daily probability `p_fail`.
    *   If failed: Sample `repair_duration` from a distribution (e.g., Uniform or Exponential) and set `remaining_downtime`.
    *   If not failed: The system is operational.

**Calibration**: Ensure the input `p_fail` is calibrated to the target Availability ($A$) and Mean Repair Time ($D$).
Formula: $p_{\text{fail}} \approx \frac{1-A}{A \cdot D}$ (for small $p$).

## Example
```python
# State variable
down_days_remaining = 0

for t in range(simulation_horizon):
    if down_days_remaining > 0:
        # System is in repair state
        down_days_remaining -= 1
        capacity_today = 0
    else:
        # System is operational, check for NEW failure
        if random.random() < p_daily_failure:
            # Failure occurred! Sample repair time.
            # Example: Uniform[5, 25] days
            repair_time = random.randint(5, 25)
            down_days_remaining = repair_time
            capacity_today = 0
        else:
            # Successful operation
            capacity_today = nominal_capacity
```

## When to Use
- Logistics simulations involving machinery with significant repair times (Elevators, Ships, Factories).
- Reliability engineering where "Availability" is a composite of MTTF and MTTR.
- Inventory buffer sizing (buffers must survive the *duration* of the burst, not just the *frequency*).
