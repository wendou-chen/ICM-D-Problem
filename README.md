# MCM 2026 Problem D Solution

![Status](https://img.shields.io/badge/Status-Active-brightgreen)
![Python](https://img.shields.io/badge/Python-3.9%2B-blue)

This repository contains the complete engineering solution, mathematical models, and simulation scripts for the **MCM 2026 Problem D**. The project is designed to analyze space transportation logistics, comparing Space Elevators and Rocket systems under various scenarios (A, B, C).

## 📂 Project Structure

The project is organized into modular components to separate core logic from execution scripts and data.

```text
D题归档工程_26/
├── src/                    # Core simulation logic & models
│   ├── q1/                 # Question 1: Baseline & Trade-off models
│   ├── q2/                 # Question 2: Optimization & Probability
│   ├── q3/                 # Question 3: Simulation & Sensitivity
│   └── q4/                 # Question 4: Environmental Impact (LCA)
├── scripts/                # Execution scripts for pipelines
│   ├── run_q1.py           # Execute Q1 analysis
│   ├── run_q2.py           # Execute Q2 analysis
│   └── ...
├── configs/                # Configuration & Constants (Yaml/Py)
│   ├── constants.py        # Global constants (Parameters)
│   └── risk_params.yaml    # Risk analysis parameters
├── outputs/                # Generated Artifacts
│   ├── q1/                 # Q1 Tables & Figures
│   └── ...
├── .agent/                 # Agentic workflow configs (Antigravity/Opencode)
├── requirements.txt        # Python dependencies
└── runner.py               # Unified command execution utility
```

## 🚀 Getting Started

### Prerequisites

- Python 3.9 or higher
- Git

### Installation

1.  **Clone the repository:**
    ```bash
    git clone git@github.com:wendou-chen/ICM-D-.git
    cd ICM-D-
    ```

2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

    *Note: The `ai-watermark/` directory is ignored by git to keep the repository light. Ensure all necessary packages are installed via pip.*

## 🛠️ Usage

The project uses standalone scripts for each specific problem part. All scripts should be run from the project root directory.

### Running Question 1 Analysis
Generates baseline tables, interval robustness data, and cost-time trade-off plots.
```bash
python scripts/run_q1.py
```
*Outputs:* `outputs/q1/q1_baseline.csv`, `outputs/q1/figs/*.png`

### Running Question 2 Analysis
Executes the optimization models and probabilistic simulations.
```bash
python scripts/run_q2.py
```

### Running Detailed Simulations (Q3/Q4)
For comprehensive scenario simulation and environmental impact analysis:
```bash
python scripts/run_q3_step5.py
python scripts/run_q4_detailed_sim.py
```

## 🧠 Key Features

-   **Modular Architecture:** Separation of physical concerns (Elevator vs Rocket) and economic concerns (Cost models).
-   **Robustness Analysis:** Built-in interval arithmetic and sensitivity scanning (Alpha scan).
-   **Automated Visualization:** Publication-ready plots generated automatically using Matplotlib/Seaborn.
-   **Agentic Integration:** Designed to work with AI Agents for automated reporting and code refinement (see `.opencode` directory).

## 🤝 Contribution

1.  Fork the Project
2.  Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3.  Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4.  Push to the Branch (`git push origin feature/AmazingFeature`)
5.  Open a Pull Request

## 📄 License

[MIT License](LICENSE)
