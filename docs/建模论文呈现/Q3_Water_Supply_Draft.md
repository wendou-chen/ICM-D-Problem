# Section 3: Water Supply Chain Strategy

## 3.1 Demand Modeling & Inventory Dynamics

Securing a stable water supply for the 100,000-person settlement represents a unique logistical challenge: unlike structural cargo, water demand is continuous, life-critical, and non-deferrable.

### 3.1.1 Net Demand Calculation
The daily net water requirement ($d_{net}$) is a function of the population ($P$), per capita usage ($w$), and the recycling efficiency ($\eta$) of the Environmental Control and Life Support System (ECLSS).
$$
d_{net} = \frac{P \cdot w \cdot (1 - \eta)}{1000} \quad [\text{tons/day}]
$$
Assuming ISS-standard recycling ($\eta=0.98$) and typical usage ($w=175$ L/day), the baseline net import requirement is approximately **350 tons/day**.

### 3.1.2 Dual-Mode Inventory Policy
We propose a **Risk-Aware Order-Up-To Policy** $(s, S)$ to manage the inventory $W_t$ on the Moon.
$$
W_{t+1} = W_t + x_{E,t} + x_{R,t} - d_{net}
$$
The target stock level $S$ is calibrated to buffer against the specific failure modes of the transport architecture:
$$
S = (L_{transit} + B_{safety}) \cdot d_{net}
$$
*   **Transit Stock ($L \cdot d$)**: Covers demand during the 7-day elevator transit.
*   **Safety Buffer ($B \cdot d$)**: A strategic reserve (e.g., 15 days) to withstand "Burst Failures" of the elevator system.

---

## 3.2 Stochastic Risk Assessment

We developed a **Discrete Event Simulation (DES)** engine to stress-test this policy over a 365-day horizon. The simulation introduces random disruptions:
1.  **Elevator Downtime**: Modeled as a Markov process with Mean Time Between Failures (MTBF).
2.  **Rocket Launch Failure**: Modeled as Bernoulli trials with probability $p_{fail}$.

### 3.2.1 The "Reliability Premium"
**Figure 3-1** (Spaghetti Plot of Inventory Traces) reveals that under a "Severe" risk scenario, a pure elevator strategy leads to frequent stockouts. To guarantee 95% service reliability ($P_{stockout} < 0.05$), the system must activate the **Emergency Rocket Fleet**.

This creates a structural asymmetry:
*   **Mass Volume**: The Space Elevator carries $>95\%$ of the water.
*   **Total Cost**: The Rocket Fleet, accounting for $<5\%$ of the volume, drives $>60\%$ of the annual logistics budget.
We term this cost disparity the **Reliability Premium**—the marginal cost of insuring against elevator failure.

---

## 3.3 Strategic Extension: In-Situ Resource Utilization (ISRU)

To mitigate the high costs of Earth-based transport, we modeled the integration of lunar ice extraction. Let $\gamma \in [0, 1]$ be the **ISRU Coverage Ratio**, representing the fraction of demand met by local production ($u_{local} = \gamma \cdot d_{net}$).

The effective shipping demand becomes:
$$
d_{ship} = \max(0, d_{net} - u_{local})
$$

**Figure 3-2** (ISRU Sensitivity Sweep) demonstrates a critical threshold effect:
1.  **Monotone Risk Reduction**: As $\gamma$ increases, the dependency on the long Earth-Moon supply chain decreases linearly.
2.  **Budgetary Collapse**: When $\gamma \to 1$, the annual logistics cost drops precipitously, as the expensive "Emergency Rockets" are no longer needed to cover supply gaps.

**Recommendation**: The "Reliability Premium" calculated in Section 3.2 serves as the **Breakeven Capital Expenditure (CAPEX)** for ISRU infrastructure. If the annualized cost of lunar ice mining is lower than this premium, ISRU is economically strictly dominant.
