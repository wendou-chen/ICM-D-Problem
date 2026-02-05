# D-Library API Reference

This document outlines the public interface for the D-Algorithm Library.

## `src.q1` (Question 1: Baseline)

### `src.q1.baseline`

#### `build_q1_baseline_table() -> pd.DataFrame`
Generates a Pandas DataFrame containing analysis for Scenarios A (Elevator), B (Rocket), and C (Hybrid). 
- **Returns**: DataFrame with columns: `scenario`, `K_sites`, `r_daily`, `payload_ton`, `annual_capacity_tpy`, `time_years`, `cost_low_usd`, `cost_high_usd`.
- **Side Effects**: Reads constants from `configs.constants`.

### `src.q1.robustness_interval`

#### `interval_time_A(total_mass_ton: float, C_elevator_tpy: float, delta: float) -> Tuple[float, float]`
Calculates the min/max completion time for Scenario A given a $\pm \delta$ uncertainty in elevator capacity.
- **delta**: Percentage variation (e.g., 0.1 for 10%).
- **Returns**: `(t_min_years, t_max_years)`

#### `interval_time_B(total_mass_ton, K_range, r_set, q_range) -> Dict[str, float]`
Calculates bounds for Scenario B based on parameter ranges.
- **K_range**: `(k_min, k_max)` tuple of sites.
- **r_set**: Tuple of possible launch rates.
- **q_range**: `(q_min, q_max)` payload range.
- **Returns**: Dictionary with `best_time_years`, `worst_time_years`, `cap_min_tpy`, `cap_max_tpy`.

#### `interval_time_C_lower_bound(...) -> Dict[str, float]`
Calculates bounds for Scenario C (Hybrid). Assumes Elevator is constant (or mean), varies Rocket parameters.

### `src.q1.feasibility`

#### `alpha_star(C_E: float, C_R: float) -> float`
Calculates the optimal share fraction $\alpha^*$ for the Elevator to minimize total time.
$$ \alpha^* = \frac{C_E}{C_E + C_R} $$

#### `lower_bound_time_years(total_mass, C_E, C_R) -> float`
Calculates the theoretical minimum time using the optimal split.
$$ T = \frac{M}{C_E + C_R} $$

### `src.q1.capacity`

#### `elevator_total_capacity_tpy(num_harbours: int, cap_per_harbour: float) -> float`
Sum capacity for N harbors.

#### `rocket_annual_capacity_tpy(k_sites, r_daily, q_payload) -> float`
$$ C_R = K \times r \times 365 \times q $$

---

## `src.q2` (Question 2: Optimization)

### `src.q2.plots`

#### `plot_feasibility_region(..., output_path: str)`
Visualizes the 2D feasibility space ($C_E, C_R$) with isolines for completion time.
- **system_points**: List of dictionaries marking specific system configurations.

#### `plot_alpha_drift(results, param_name, output_path)`
Plots how $\alpha^*$ changes as a parameter (e.g., reliability) varies.

---

## `configs`

### `configs.constants`
Contains frozen data classes:
- `Problem`
- `Rocket`
- `Elevator`
- `Cost`

Import these to access standard simulation parameters.
