# Modeling Notes: MCM 2026 Problem B - Question 1

## Overview
Question 1 asks for a baseline comparison of three transportation scenarios (Elevator only, Rocket only, Hybrid) to move $M=100$ million metric tons to the Moon, starting in 2050.

## Assumptions & Interpretations

### 1. Elevator Capacity (Scenario A)
- **Problem Statement**: "Galactic Harbor will provide... 179,000 metric tons every year" and there are 3 Harbors.
- **Interpretation**: The 179k capacity is *per harbor*.
- **Total Capacity $C_E$**: $3 \times 179,000 = 537,000$ tons/year.
- **Apex Transfer**: Material reaching Apex (GEO) needs transfer to Moon. We assume this transfer capability matches the elevator uplift rate in the "perfect condition" baseline.

### 2. Rocket Capacity (Scenario B)
- **Problem Statement**: 
  - Payload 100-150 tons ($q$).
  - 10 Launch sites ($K$).
- **Launch Frequency ($r$)**: Not explicitly fixed. We assume reasonable bounds for 2050 technology:
  - Low estimate: 1 launch/day/site ($r=1$).
  - High estimate: 2 launches/day/site ($r=2$).
- **Total Capacity $C_R$**: $K \times r \times 365 \times q$.

### 3. Hybrid Strategy (Scenario C)
- **Goal**: Minimize time $T$.
- **Method**: Parallel operation.
- **Optimal Split ($\alpha^*$)**:
  - Let $\alpha$ be fraction of mass on Elevator.
  - $T_E(\alpha) = \frac{\alpha M}{C_E}$
  - $T_R(\alpha) = \frac{(1-\alpha)M}{C_R}$
  - Optimal $T$ is when $T_E = T_R$.
  - $\implies \alpha^* = \frac{C_E}{C_E + C_R}$.
  - $T_{min} = \frac{M}{C_E + C_R}$.

### 4. Cost Modeling
- **Status**: Symbolic / Interval in Q1.
- **Reasoning**: Specific dollar values for 2050 are highly uncertain. We establish the *structure* of the cost function now.

## Results Summary
See `outputs/q1/q1_baseline.csv` for calculated values.
See `outputs/q1/figs/` for visualizations.
