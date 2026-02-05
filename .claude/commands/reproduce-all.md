# Reproduce Full Pipeline (Q1-Q4)

Execute the complete modeling and simulation pipeline for MCM 2026 Problem B.

## Q1: Baseline Construction & Analysis
Establishes the baseline space elevator model and cost analysis.
```bash
python scripts/run_q1.py
```

## Q2: Weather & Resilience
Simulates non-perfect conditions (weather) and optimizes for system resilience.
```bash
python scripts/run_q2.py
```

## Q3: Water Supply & ISRU Strategy
Executes the multi-step water supply and In-Situ Resource Utilization (ISRU) planning.
```bash
python scripts/run_q3_step1.py
python scripts/run_q3_step3.py
python scripts/run_q3_step4.py
python scripts/run_q3_step5.py
```

## Q4: Environmental Impact Assessment
Runs environmental parameter sweeps and detailed emissions simulations.
```bash
python scripts/run_q4_env_sweep.py
python scripts/run_q4_detailed_sim.py
```

## Visualization (Optional)
Generate final plots for the paper.
```bash
python scripts/viz_q4_results.py
python scripts/viz_q4_detailed.py
```
