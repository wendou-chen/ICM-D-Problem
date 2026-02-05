# 2050 Lunar Logistics Network: Modeling Brief
**Date:** 2026-02-02
**Author:** Modeling Team

## 1. Variable & Parameter Dictionary
Key parameters defined in `configs/constants.py` and `configs/env_constants.py`.

| Symbol | Code Variable | Description | Default Value | Unit |
|---|---|---|---|---|
| $M_{total}$ | `TOTAL_MASS_TONS` | Total cargo demand to Moon | 100,000,000 | tons |
| $T_{start}$ | `START_YEAR` | Project start year | 2050 | year |
| $C(y)$ | `rocket_cost_per_launch` | Rocket launch cost at year $y$ | Dynamic | USD |
| $\alpha$ | `decay_rate` | Technology learning rate | 0.05 / 5yrs | - |
| $S_t$ | `S_bc` | Stratospheric Black Carbon Stock | Dynamic | tons |
| $\tau$ | `tau_bc_years` | Soot residence time | 4.0 | years |
| $E_{LCA}$ | `E_LCA_build_ton` | Emissions from Elevator Construction | ~Eq 4.4 | tons CO2 |
| $I_t$ | `inventory` | Water inventory at lunar base | Dynamic | tons |
| $N_{safe}$ | `N_safe_year` | Safe rocket launch limit (Ozone) | 1000 | launches/yr |

## 2. Modeling Logic Summary

### Q1: Infrastructure Selection (The Baseline)
We compare two modes:
1.  **Rocket Only**: High marginal cost, low fixed cost. Subject to learning curve $C(t) = C_0 (1-\alpha)^{\lfloor t/5 \rfloor}$.
2.  **Space Elevator**: Huge fixed cost ($E_{LCA}$), near-zero marginal cost.
**Logic**: Identify the cross-over point where Elevator ROI exceeds Rockets.

### Q2: Reliability & Resilience
Introduced stochastic failures:
*   **Rocket Failure**: Binomial process $B(n, p)$.
*   **Elevator Failure**: Poisson process with MTTR (Mean Time To Repair).
**Logic**: Discrete Event Simulation (DES) to measure throughput variance under "Severe" conditions.

### Q3: Water Resource Management
Supply Chain Dual-Sourcing:
*   **Base Load**: Elevator (Cheap, slow).
*   **Surge Capacity**: Rockets (Fast, expensive).
**Logic**: Inventory Control Policy $(s, S)$ with emergency rocket injections when $I_t < s$.

### Q4: Environmental Impact Assessment
**The Leaky Bucket Model**:
$$S_{t+1} = (1 - \delta) S_t + u_t$$
Where $u_t$ is daily emissions from rocket launches.
**EDI (Environmental Damage Index)**: Weighted sum of Carbon, Soot, and Ozone layer depletion risks.

## 3. Visual Gallery

### 3.1 Q1: The Trade-off
![Figure 1: Cumulative Mass Transported vs. Year](outputs/q1/figs/cum_mass_vs_year.png)
> **Interpretation**: The elevator (step function) allows massive capacity deployment once built, whereas rockets (linear/curve) are limited by launch windows and fleet size.

![Figure 2: Cost-Time Pareto Front](outputs/q1/figs/pareto_cost_time.png)
> **Interpretation**: The Pareto front shows the non-dominated solutions. High investment (Elevator) yields faster completion (lower time).

### 3.2 Q2: System Stability
![Figure 3: Feasibility Region Analysis](outputs/q2/figs/feasibility_region.png)
> **Interpretation**: The shaded region represents valid operating parameters where the system meets demand 95% of the time despite failures.

### 3.3 Q3: Supply Chain Risk
![Figure 4: Reliability Curve](outputs/q3/step3/fig3_reliability_curve.png)
> **Interpretation**: As we increase the safety stock (buffer), the probability of water stockout decreases exponentially.

### 3.4 Q4: Environmental Costs
![Figure 5: Environmental Components Breakdown](outputs/q4_detailed/plots/fig_q4_env_components.png)
> **Interpretation**: Breakdown of the Environmental Damage Index (EDI). Rocket soot (Black Carbon) becomes the dominant long-term factor compared to transient CO2.

![Figure 6: Soot Accumulation (Leaky Bucket)](outputs/q4_detailed/plots/fig_q4_soot_timeseries.png)
> **Interpretation**: Time-series of stratospheric soot. Even with launches spreading out, the long residence time ($\tau=4$ years) causes accumulation (the "filling bucket" effect).
