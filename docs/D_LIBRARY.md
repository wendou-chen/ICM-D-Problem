# D-Algorithm Library Documentation

## 1. Overview

The **D-Algorithm Library** is a specialized Python toolkit originally built for **MCM 2026 Problem D (Space Transportation)**. It solves the "Space Elevator vs. Rocket" logistics problem by modeling capacity, cost, risk, and time trade-offs.

The library is designed to be **modular** and **stateless** where possible, relying on configuration classes (`configs/constants.py`) for physical parameters.

## 2. Architecture

The library is split into four distinct question-modules (`q1` to `q4`), corresponding to the phases of the original problem.

### `src/q1`: Baseline & Feasibility
Focuses on deterministic, static analysis.
- **Goal**: Determine the "Best", "Worst", and "Hybrid" scenarios for transporting 100M tons of cargo.
- **Key Files**:
    - `baseline.py`: Generates the master comparison table (A vs B vs C).
    - `feasibility.py`: Contains analytical derivatives, such as $\alpha^*$ (optimal load split).
    - `robustness_interval.py`: Implements interval arithmetic for uncertainty analysis (e.g., what if capacity varies by $\pm10\%$?).

### `src/q2`: Reliability & Optimization
Focuses on probabilistic analysis and risk management.
- **Goal**: Analyze system performance under failure modes (Poisson process / Binomial).
- **Key Concepts**:
    - **Alpha Drift**: How the optimal split changes when reliability drops.
    - **Feasibility Region**: Visualizing $C_E$ vs $C_R$ space.
    - **Gamma Scan**: Impact of emergency surge capacity.

### `src/q3`: Inventory Simulation (Implied)
Focuses on dynamic supply chain management.
- **Goal**: Managing water/resource stocks.
- **Key Concepts**:
    - Order-up-to policies.
    - Buffer stock optimization.

### `src/q4`: Environmental Impact
Focuses on Life Cycle Assessment (LCA).
- **Goal**: Quantify emissions and black carbon impact.

## 3. Mathematical Foundations

### The Hybrid Model (Scenario C)

The library implements a parallel processing model where mass $M$ is split between Elevator ($M_E = \alpha M$) and Rocket ($M_R = (1-\alpha)M$).

The completion time $T$ is governed by the bottleneck channel:
$$ T(\alpha) = \max \left( \frac{\alpha M}{C_E}, \frac{(1-\alpha)M}{C_R} \right) $$

To minimize $T$, we solve for $\alpha^*$ such that both channels finish simultaneously:
$$ \frac{\alpha M}{C_E} = \frac{(1-\alpha)M}{C_R} \implies \alpha^* = \frac{C_E}{C_E + C_R} $$

This logic is encapsulated in `src.q1.feasibility.alpha_star`.

### Interval Robustness

Instead of single-point estimates, the library uses interval arithmetic:
$$ [T_{min}, T_{max}] = \left[ \frac{M}{C_{\max}}, \frac{M}{C_{\min}} \right] $$
See `src.q1.robustness_interval`.

## 4. Configuration System

All physical constants are centralized in `configs/constants.py` using frozen dataclasses.

- **`Problem`**: Global scale ($M$, Start Year).
- **`Elevator`**: Capacity and availability specs.
- **`Rocket`**: Launch rates, payload ranges, daily limits.
- **`Cost`**: Price floors, decay rates (learning curve), and Beta factors (Apex transfer).

> **Tip**: exact simulation behavior can be tuned by modifying `configs/constants.py` without changing algorithmic code.
