# Section 2: Transition & Resilience Analysis

## 2.1 From Ideal State to Probabilistic Reality

In Section 1, we established the baseline architecture assuming ideal operations. However, the problem statement explicitly cites risks such as "tether swaying," "debris impact," and "severe weather." To quantify *to what extent* the solution changes, we transition from a deterministic flow model to a **Stochastic Discrete Event Simulation (DES)** framework.

### 2.1.1 Failure Mode Characterization
We distinguish between two fundamentally different risk typologies:

1.  **Systemic Burst Failure (Space Elevator)**:
    Modeled as a **Two-State Continuous Time Markov Chain (CTMC)**. When a failure occurs (e.g., tether alignment issue), the system enters a `REPAIR` state where throughput drops to zero for a random duration $D_{repair} \sim \mathcal{U}(MTTR_{min}, MTTR_{max})$.
    *   *Impact*: Total capacity blockage.
    *   *Key Parameter*: Availability $A_E = \frac{MTTF}{MTTF + MTTR}$.

2.  **Independent Attrition (Rocket Fleet)**:
    Modeled as **Bernoulli Trials** per launch. A failure (probability $p_R$) results in the loss of a specific payload and triggers a local "Pad Reset" delay ($\tau_{reset}$), but does not halt global operations across $K$ sites.
    *   *Impact*: Marginal capacity degradation.
    *   *Key Parameter*: Effective Success Rate $s_R = 1 - p_R$.

---

## 2.2 Analytical Expectation: The "Alpha Drift"

Before running simulations, we analytically derive the "drift" of the optimal strategy. Let $\tilde{C}_E = A_E \cdot C_E$ and $\tilde{C}_R = (1-p_R) \cdot C_R$ be the effective capacities. The optimal elevator share $\alpha^*$ shifts to minimize the risk-adjusted make-span:

$$
\alpha^*(A_E, p_R) = \frac{\tilde{C}_E}{\tilde{C}_E + \tilde{C}_R}
$$

**Figure 2-1 (The Alpha Drift)** visualizes this migration.
*   **Result**: Under the "Severe" scenario ($A_E=0.70$), the optimal elevator share drops from $\alpha \approx 0.92$ (Ideal) to $\alpha \approx 0.65$.
*   **Implication**: The system *must* structurally over-invest in rocket infrastructure to hedge against elevator downtime. The "extent" of change is a **27% load shift** from the cheap mode to the reliable mode.

---

## 2.3 Feasibility Analysis: The Capacity Gap

We introduce the **Feasibility Certificate** to determine if the deadline $T_{target}=20$ years is physically achievable under risk. The **Capacity Gap ($\Delta C$)** is defined as:

$$
\Delta C = \frac{M}{T_{target}} - (\tilde{C}_E + \tilde{C}_R)
$$

**Figure 2-2 (Feasibility Phase Plot)** maps the system state across Mild, Moderate, and Severe presets.
*   **Observation**: In the **Severe** scenario, $\Delta C > 0$. The baseline system (designed for ideal conditions) falls into the **Infeasible Region**. Even with optimal scheduling, the expected completion time slips to $T \approx 26$ years.
*   **Conclusion**: To maintain the 20-year target, we cannot just "re-optimize"; we must introduce a **Resilience Mechanism**.

---

## 2.4 Resilience Strategy: The Dynamic Surge Policy

To recover from the "Severe" state, we propose a reactive control policy: **The Rocket Surge**.

**Policy Definition**:
$$
r(t) =
\begin{cases}
r_{base}, & \text{if Elevator is UP} \\
\gamma \cdot r_{base}, & \text{if Elevator is DOWN}
\end{cases}
$$
Where $\gamma \ge 1$ is the **Surge Multiplier**, representing the activation of reserve launch pads or overtime shifts during elevator outages.

### 2.4.1 Simulation Results ($N=1000$)
We performed a Monte Carlo sweep of $\gamma \in [1.0, 5.0]$.

*   **Figure 2-3 (Surge Effectiveness)**: Shows the probability of on-time completion $P(T \le 20)$ as a function of $\gamma$.
*   **Critical Threshold**: To achieve $P_{on-time} \ge 95\%$ under severe risks, a multiplier of **$\gamma \approx 3.0$** is required.
*   **Trade-off**: This resilience comes at a cost. The surge strategy increases the Total Project Cost by **$42\%$** (due to the high marginal cost of rocket launches), but it effectively "buys back" the schedule certainty.

**Final Answer to Q2**: The solution changes from a static optimal mix to a dynamic, state-dependent control loop. The extent of this change is quantified by the **Alpha Drift (-27%)** and the **Resilience Cost Premium (+42%)**.
