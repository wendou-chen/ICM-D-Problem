# 2 Assumptions and Justifications

1. **Assumption I**: The project timeline commences in 2050, and the total mass demand of 100 million tons ($M_{total}$) accounts for all necessary structural components, neglecting initial in-situ resource utilization (ISRU) savings.
   **Justification**: Assuming a 2050 start provides a realistic timeframe for the maturation of critical precursor technologies like commercial fusion and graphene manufacturing. Treating the demand as fixed and conservative ensures that our feasibility analysis accounts for the worst-case logistical load, providing a robust upper bound for infrastructure requirements.

2.  **Assumption II**: The Two-Stage Transport TopologyWe assume the Space Elevator (Galactic Harbour) operates as a synchronized two-stage system: cargo is first lifted to the Apex Anchor via tether, then transferred to the Moon via tugs. The tether's lift rate $C_E$ is the binding constraint of the entire link.
    **Justification**: Feasibility Simplification. While the physical mechanics of climbing are continuous, the system's throughput is dictated by the slowest segment. Assuming the tether is the bottleneck allows us to model the elevator as a flow channel with capacity $C_E$, decoupling it from the complex orbital mechanics of the Apex transfer tugs.

3.  **Assumption III**: Rocket launch costs follow a technological learning curve (Wright’s Law) decaying at 5% every 5 years, while Space Elevator operational capacity remains linear once built.
    **Justification**: Historical aerospace data supports the use of learning curves to model cost reductions over time. Assuming linear capacity for the elevator simplifies the steady-state analysis, allowing us to focus on the long-term trade-offs between the high-frequency but costly rocket launches and the high-volume, low-marginal-cost elevator system.

4.  **Assumption IV**: Mechanical failures in the transportation system follow a Poisson process with exponential inter-arrival times, and repair times are exponentially distributed.
    **Justification**: The "Memoryless Property" of the Poisson process is a standard reliability engineering assumption for complex systems where failure risk does not strictly depend on age. Exponential repair times capture the "long tail" risk of rare, catastrophic failures that disrupt the supply chain significantly more than routine maintenance, which is critical for our resilience analysis.

5.  **Assumption V**Green Energy DecarbonizationWe assume the carbon intensity of the Space Elevator's operation is a function of the Earth's grid mix $\chi$ (Green Penetration Rate), which can improve over time.
    **Justification**:LCA Boundary Definition. The Elevator itself emits nothing locally. Its environmental footprint is entirely indirect (Scope 2 emissions). Linking it to the grid mix $\chi$ allows us to model the sensitivity of environmental impact to energy policy.

6.  **Assumption VI**: Stratospheric Black Carbon accumulation follows a "Leaky Bucket" dynamic model with a residence time of approximately 4 years, and global mixing is instantaneous.
    **Justification**: Physical accumulation is the primary driver of long-term environmental damage. The "Leaky Bucket" model captures the cumulative debt of pollutants that injection rates exceeding natural deposition create. Instantaneous mixing simplifies the atmospheric physics to a tractable global variable ($S_{BC}$), sufficient for estimating the order of magnitude of radiative forcing risks without running a full climate simulation.
