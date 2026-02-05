# Minimal Intrusion Environmental Ledger

## Context
When extending engineering simulations (e.g., traffic, logistics, space missions) to include environmental impact analysis (LCA, emissions), a common anti-pattern is injecting "pollution counters" directly into the core physics classes. This couples the "accounting" logic with the "physics" logic, increasing complexity and risk of regression in the verified simulation core.

## Pattern Description
The **Minimal Intrusion Environmental Ledger** creates a sidecar observer (the "Ledger") that passively accepts state updates from the main simulation loop or reconstructs them from logs. It maintains its own internal state (e.g., pollutant decay, cumulative stock) completely separate from the operational logic.

## Implementation Structure

### 1. The Ledger Class
This class acts as a sink for operational data and a source for environmental metrics.

```python
class EnvLedger:
    def __init__(self, config):
        self.emissions_log = []
        self.pollutant_stock = 0.0  # Dynamic stock (e.g., stratospheric soot)
        self.decay_rate = config.get('decay_rate', 0.01) # e.g., daily decay

    def record_step(self, t, operational_vars):
        """
        Ingest operational state for time t without modifying it.
        operational_vars: dict of physics states (e.g., fuel_burnt, distance)
        """
        # 1. Flow Calculation: Map physics to immediate emissions
        daily_emission = operational_vars['fuel_kg'] * EMISSION_FACTOR

        # 2. Stock Update: Leaky Bucket Model
        # S_{t+1} = (1 - delta) * S_t + u_t
        self.pollutant_stock = (1 - self.decay_rate) * self.pollutant_stock + daily_emission

        # 3. Log
        self.emissions_log.append({
            't': t,
            'flow': daily_emission,
            'stock': self.pollutant_stock,
            'event': operational_vars.get('event_type')
        })

    def finalize(self):
        """Compute aggregated metrics after simulation ends."""
        import pandas as pd
        df = pd.DataFrame(self.emissions_log)
        return {
            'total_emissions': df['flow'].sum(),
            'peak_stock': df['stock'].max(),
            'average_stock': df['stock'].mean()
        }
```

### 2. Integration Point
The simulation loop remains clean. The ledger is just a subscriber.

```python
# Main Simulation Loop
ledger = EnvLedger(config)
sim_state = SimulationState()

for t in range(MAX_TIME):
    # Core Physics (Unchanged)
    ops_data = sim_state.step()

    # Non-Intrusive Accounting
    ledger.record_step(t, ops_data)

metrics = ledger.finalize()
```

## Benefits
1.  **Safety**: Zero risk of breaking the core physics engine (since the ledger cannot modify `sim_state`).
2.  **Flexibility**: You can change emission factors or decay models (e.g., update the "Leaky Bucket" parameters) without re-validating the trajectory code.
3.  **Visualization**: Naturally supports the "Flow vs. Stock" visualization by tracking both instantaneous emissions and cumulative burden.

## When to Use
-   Adding LCA/Sustainability metrics to existing, complex simulations.
-   Modeling pollutants with residence times (CO2, soot, orbital debris) where `Total = Sum(Daily)` is incorrect.
-   Comparing scenarios where operational efficiency trades off against construction costs (e.g., building a space elevator vs. flying rockets).
