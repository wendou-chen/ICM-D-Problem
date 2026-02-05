# 2050 Lunar Logistics Network: Modeling Brief

**Date:** 2026-02-02
**Author:** AI Modeling Team (Antigravity)

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

---

## 2. Modeling Logic Summary

### Q1: Infrastructure Selection
**Problem**: Trade-off between Rockets and Space Elevator.
**Model**:
*   **Rockets**: Low fixed cost, high marginal cost. Subject to learning curve $C(t) = C_0 (1-\alpha)^{\lfloor t/5 \rfloor}$.
*   **Elevator**: Huge fixed cost ($E_{LCA}$), near-zero marginal cost.
**Implementation**: `src/q1/cost_model.py`.
**Key Finding**: Space Elevator dominates in the long run for massive cargo ($10^8$ tons) despite high initial CapEx.

### Q2: System Reliability & Resilience
**Problem**: System stability under stochastic failures.
**Model**: **Discrete Event Simulation (DES)**
*   **Rocket Failure**: Binomial process $B(n, p)$.
*   **Elevator Failure**: Poisson process with MTTR (Mean Time To Repair).
**Implementation**: `src/q2/simulator.py`.
**Key Finding**: Redundancy is critical. A dynamic backup policy reduces downtime risk to <5%.

### Q3: Water Resource Management
**Problem**: Zero-tolerance for water supply failure.
**Model**: **Dual-Sourcing Strategy**
*   **Base Load**: Elevator (Cheap, High Volume).
*   **Surge**: Rockets (Fast, Expensive).
*   **Policy**: $(s, S)$ Inventory Control. Trigger rockets when $I_t < s$.
**Implementation**: `src/q3/simulation.py`.

### Q4: Environmental Impact Assessment
**Problem**: Cumulative impact of high-frequency launches.
**Model**: **The Leaky Bucket Model**
$$S_{t+1} = (1 - \delta) S_t + u_t$$
*   $S_t$: Stratospheric Black Carbon Stock.
*   $u_t$: Daily emissions.
*   $\delta$: Natural decay rate ($\delta \approx 1/(\tau \times 365)$).
**Metric (EDI)**: Weighted sum of Carbon, Soot, and Ozone risks.
**Implementation**: `src/q4/env_ledger.py`.

---

## 3. Visual Gallery

### 3.1 Cost-Time Pareto Front
![Figure 1: Cost vs. Time Trade-off](outputs/q1/figs/pareto_cost_time.png)
> **Interpretation**: The Pareto front shows non-dominated solutions. The Elevator strategy minimizes total time and long-term cost.

### 3.2 Reliability Curve
![Figure 2: Reliability vs. Buffer Size](outputs/q3/step3/fig3_reliability_curve.png)
> **Interpretation**: Stockout probability decreases exponentially with safety stock size. We recommend a 30-day buffer.

### 3.3 Environmental Accumulation
![Figure 3: Stratospheric Soot Time-series](outputs/q4_detailed/plots/fig_q4_soot_timeseries.png)
> **Interpretation**: Due to the long residence time ($\tau=4$ years), soot accumulates in the stratosphere ("Leaky Bucket" effect), posing a significant long-term climate risk for the Rocket-heavy scenario.
