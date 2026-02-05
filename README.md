# MCM 2026 Project (Problem B + D Library)

![Status](https://img.shields.io/badge/Status-Archived-orange)
![Python](https://img.shields.io/badge/Python-3.9%2B-blue)
![License](https://img.shields.io/badge/License-MIT-green)

This repository serves as the archival codebase for the **MCM 2026 Problem B** submission. It is built upon a robust, standalone **Algorithm Library** originally developed for **Problem D (Space Logistics)**. 

While the repository contains pipelines specific to Problem B (WNBA Data Analysis), the core value lies in the reusable **Space Transportation Simulation Library** (`src/q1` - `src/q4`), which models complex trade-offs between Space Elevators and Rocket systems.

## 📂 Repository Map

```text
D题归档工程_26/
├── src/                        # 🧠 CORE ALGORITHM LIB (Problem D)
│   ├── q1/                     #   - Baseline Trade-off & Intervals
│   ├── q2/                     #   - Optimization & Probability Models
│   ├── q3/                     #   - Simulation & Inventory Control
│   ├── q4/                     #   - Environmental LCA Models
│   └── utils/                  #   - Shared Plotting & Stats Utils
│
├── scripts/                    # 🚀 ENTRY POINTS
│   ├── run_pipeline.py         #   - [Problem B] WNBA Data Pipeline
│   ├── run_q1.py               #   - [Problem D] Baseline Analysis
│   ├── run_q2.py               #   - [Problem D] Optimization Run
│   └── ...
│
├── configs/                    # ⚙️ CONFIGURATION
│   ├── constants.py            #   - Physical/Economic Constants (D Lib)
│   └── sources.yaml            #   - Data Sources Config (B Pipeline)
│
├── docs/                       # 📚 DOCUMENTATION
│   ├── D_LIBRARY.md            #   - Detailed D-Lib Architecture Guide
│   ├── API.md                  #   - API Reference
│   ├── EXAMPLES.md             #   - Runnable Usage Examples
│   └── repo_map.md             #   - Legacy Project Map
│
└── outputs/                    # 📊 ARTIFACTS
    └── q1/                     #   - Simulation results
```

---

## 🚀 Quick Start

### 1. Installation

Clone the repository and install dependencies. Note that we exclude large datasets and virtual environments.

```bash
git clone git@github.com:wendou-chen/ICM-D-.git
cd ICM-D-
pip install -r requirements.txt
```

### 2. Running Problem B Pipeline (WNBA Analysis)

To reproduce the Problem B data processing workflow:

```bash
python scripts/run_pipeline.py --seasons 2024
```

### 3. Running D-Algorithm Library (Space Logistics)

To execute the Space Transportation simulation suite:

```bash
# Run Question 1: Baseline Trade-offs & Cost Analysis
python scripts/run_q1.py

# Run Question 2: Reliability & Optimization
python scripts/run_q2.py
```

*Results will be generated in `outputs/q1/` and `outputs/q2/`.*

---

## 🌌 D-Problem Algorithm Library

The **D-Library** is a modular Python framework designed to solve logistics and transportation problems involving **mixed-integer constraints**, **stochastic failures**, and **non-linear cost functions**.

### Core Capabilities

| Module | Responsibility | Key Concepts |
| :--- | :--- | :--- |
| **q1** | **Static Analysis** | `build_q1_baseline_table`, `alpha_star` (Optimal Split), Cost/Time Intervals |
| **q2** | **Optimization** | Boxplot Analysis, Feasibility Regions, Gamma Scan (Risk) |
| **q3** | **Simulation** | Inventory Control policies, Discrete Event Simulation (implied) |
| **q4** | **Impact** | Life Cycle Assessment (LCA) models, Environmental Metrics |

### Reusing the Library

You can import the library modules directly into your own scripts.

**Example: Calculating Optimal Space Elevator Share**

```python
from configs.constants import Elevator, Rocket
from src.q1.capacity import elevator_total_capacity_tpy, rocket_annual_capacity_tpy
from src.q1.feasibility import alpha_star

# 1. Define System Capacities
cap_elev = elevator_total_capacity_tpy(num_harbours=3, cap_per_harbour=179000)
cap_rock = rocket_annual_capacity_tpy(k_sites=10, r_daily=2, q_payload=150)

# 2. Calculate Optimal Share (Alpha)
# alpha = fraction of mass sent via Elevator to balance completion time
alpha = alpha_star(C_E=cap_elev, C_R=cap_rock)

print(f"Optimal Elevator Share: {alpha:.2%}")
```

👉 **For more details, see:**
- [**D_LIBRARY.md**](docs/D_LIBRARY.md) - Architecture & Math deep dive.
- [**API.md**](docs/API.md) - Function signatures and parameters.
- [**EXAMPLES.md**](docs/EXAMPLES.md) - End-to-end recipes.

---

## 🔧 Data & Configuration

- **Constants**: Physical parameters (Mass, Cost ranges, Reliability) are defined in `configs/constants.py`. Edit this file to adjust the simulation universe.
- **Outputs**: All scripts write to `outputs/` by default. Ensure this directory exists or is writable.

## 📜 Citation

If you use this codebase or library in your research, please cite the MCM 2026 Team Submission.

```text
@misc{mcm2026_problem_b_d,
  author = {Team 26},
  title = {Space Logistics & WNBA Analysis Framework},
  year = {2026},
  note = {MCM/ICM Submission Codebase}
}
```

## 📄 License

[MIT License](LICENSE)
