# D-Library Usage Examples

These examples show how to leverage the D-Algorithm Library for custom analysis.

## Example 1: Custom Baseline Analysis

This script imports the library to run a custom "Scenario C" calculation with your own capacity numbers.

```python
import pandas as pd
from src.q1.feasibility import alpha_star, lower_bound_time_years
from src.q1.capacity import rocket_annual_capacity_tpy

# 1. Define Parameters
M_TOTAL = 100_000_000 # 100M tons
C_ELEVATOR = 500_000  # 500k tons/year (Custom Elevator)

# Define a custom rocket fleet
K_SITES = 15
MAX_LAUNCHES_DAY = 3
PAYLOAD = 200 # tons

# 2. Calculate Rocket Capacity
c_rocket = rocket_annual_capacity_tpy(K_SITES, MAX_LAUNCHES_DAY, PAYLOAD)
print(f"Rocket Fleet Capacity: {c_rocket/1e6:.2f}M tpy")

# 3. Solve for Optimal Process
optimal_alpha = alpha_star(C_ELEVATOR, c_rocket)
min_time = lower_bound_time_years(M_TOTAL, C_ELEVATOR, c_rocket)

print(f"--- Results ---")
print(f"Optimal Split: {optimal_alpha:.1%} Elevator / {1-optimal_alpha:.1%} Rocket")
print(f"Completion Time: {min_time:.2f} Years")
```

## Example 2: Sensitivity Scan

How does completion time change if we add more rocket launch sites?

```python
import numpy as np
import matplotlib.pyplot as plt
from src.q1.capacity import rocket_annual_capacity_tpy, elevator_total_capacity_tpy
from src.q1.feasibility import lower_bound_time_years
from configs.constants import Elevator

# Base Config
M = 1e8 # 100M tons
C_E = elevator_total_capacity_tpy(Elevator.NUM_HARBOURS, Elevator.CAPACITY_PER_HARBOUR_TPY)

# Scan Sites K from 5 to 50
k_values = range(5, 51, 5)
times = []

for k in k_values:
    # Assume r=2, q=150
    c_r = rocket_annual_capacity_tpy(k, 2, 150)
    
    # Calculate time
    t = lower_bound_time_years(M, C_E, c_r)
    times.append(t)

# Plot
plt.plot(k_values, times, marker='o')
plt.xlabel('Number of Launch Sites (K)')
plt.ylabel('Completion Time (Years)')
plt.title('Impact of Infrastructure Expansion')
plt.grid(True)
plt.savefig('optimization_scan.png')
print("Plot saved to optimization_scan.png")
```

## Example 3: Running the Full Q1 Pipeline

If you just want to run the standard analysis:

```bash
python scripts/run_q1.py
```

Check `outputs/q1/q1_baseline.csv` for the results.
