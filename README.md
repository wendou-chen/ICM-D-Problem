# MCM 2026 Problem B Archive

![Status](https://img.shields.io/badge/Status-Active-brightgreen)
![Problem](https://img.shields.io/badge/MCM-2026_Problem_B-blue)
![Python](https://img.shields.io/badge/Python-3.9%2B-blue)

This repository serves as the development and archival codebase for **MCM 2026 Problem B** (Creating a Moon Colony Using a Space Elevator System).

## 📂 Repository Structure

### 🚀 **Active: MCM 2026 Problem B**

The primary codebase for the 2026 Problem B submission includes:

**Core Algorithm Library:**
- `src/q1/` - Baseline Trade-off & Cost Analysis
- `src/q2/` - Reliability & Optimization Models  
- `src/q3/` - Inventory Control & Water Supply Simulation
- `src/q4/` - Environmental Impact Assessment (LCA)
- `src/utils/` - Shared Plotting & Statistics Utilities

**Execution Scripts:**
- `scripts/run_q1.py` - Run Question 1 analysis
- `scripts/run_q2.py` - Run Question 2 optimization
- `scripts/run_q3.py` - Run Question 3 simulation
- `scripts/run_q4.py` - Run Question 4 environmental assessment

**Configuration:**
- `configs/constants.py` - Physical/Economic Constants
- `configs/sources.yaml` - Data Sources Configuration

**Documentation:**
- `docs/` - API references, examples, and architecture guides
- `problems/` - Problem-specific documentation (问题1-4)

---

### 🏛️ **Legacy: ICM D Problem Archive**

**⚠️ Note:** The `mcm_d_heuristics_v3_3_1/` directory contains an **archived algorithm library from a previous ICM Problem D** submission (not related to the current MCM Problem B work).

**Legacy Directory:**
- `mcm_d_heuristics_v3_3_1/` - ICM D Problem heuristic optimization framework
  - Genetic Algorithms, PSO, Simulated Annealing
  - Network flow and scheduling algorithms
  - Data cleaning scripts (legacy)

**This legacy code is retained for reference only and should not be used for the current MCM Problem B submission.**

---

## 🚀 Quick Start (Problem B)

### 1. Installation

```bash
git clone <repository-url>
cd D题归档工程_26
pip install -r requirements.txt
```

### 2. Running Problem B Analysis

Execute the Question 1-4 analysis pipelines:

```bash
# Run Question 1: Baseline Trade-offs & Cost Analysis
python scripts/run_q1.py

# Run Question 2: Reliability & Optimization
python scripts/run_q2.py

# Run Question 3: Water Supply & Inventory Control
python scripts/run_q3.py

# Run Question 4: Environmental Impact Assessment
python scripts/run_q4.py
```

*Results will be generated in `outputs/q1/`, `outputs/q2/`, etc.*

---

## 📊 Outputs

All scripts write to `outputs/` by default:
- `outputs/q1/` - Baseline analysis results
- `outputs/q2/` - Optimization results
- `outputs/q3/` - Simulation results  
- `outputs/q4/` - Environmental assessment results

---

## 🔧 Configuration

- **Constants**: Physical parameters (Mass, Cost, Reliability) are defined in `configs/constants.py`
- **Data Sources**: Configure data paths in `configs/sources.yaml`

---

## 📜 Citation

If you use this codebase in your research, please cite:

```text
@misc{mcm2026_problem_b,
  author = {Team 26},
  title = {MCM 2026 Problem B: Moon Colony Space Elevator System},
  year = {2026},
  note = {MCM Competition Submission Codebase}
}
```

---

## 📄 License

[MIT License](LICENSE)

---

## ⚠️ Important Note

**Do not confuse:**
- **Current Work** = MCM 2026 Problem B (root `src/`, `scripts/`, `configs/`)
- **Legacy Archive** = ICM D Problem (`mcm_d_heuristics_v3_3_1/` folder only)
