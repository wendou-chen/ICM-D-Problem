# MCM 2026 Problem B: Lunar Infrastructure Transportation Optimization

## Overview

This repository contains the computational models, optimization algorithms, and analysis code for the 2026 Mathematical Contest in Modeling (MCM) Problem B: *Efficient Transportation Strategies for Lunar Infrastructure Development*.

The project models multi-modal space logistics (Space Elevator vs. Rockets vs. Hybrid approaches) to deliver 100 million metric tons of building materials to the Moon, starting from 2050.

## Project Structure

```
.
├── configs/                    # Configuration files
│   ├── constants.py            # Physical and system constants
│   ├── env_constants.py        # Environmental parameters
│   └── risk_params.yaml        # Monte Carlo simulation parameters
├── docs/                       # Documentation and reports
│   ├── 最终论文/               # Final paper and figures
│   ├── internal/               # Internal modeling briefs
│   └── 2026_MCM_Problem_B.pdf  # Original problem statement
├── flowchart/                  # Process flow diagrams
│   ├── Q1/                     # Question 1 flowcharts
│   ├── Q2/                     # Question 2 flowcharts
│   └── Init/                   # Initialization diagrams
├── mcm_d_heuristics_v3_3_1/    # Optimization algorithm library
│   ├── ga.py                   # Genetic Algorithm
│   ├── pso.py                  # Particle Swarm Optimization
│   ├── sa.py                   # Simulated Annealing
│   ├── nsga2.py                # Multi-objective NSGA-II
│   └── examples/               # Algorithm demos
├── paper/                      # LaTeX paper source
│   ├── sections/               # Paper sections
│   ├── tables/                 # LaTeX tables
│   └── references.bib          # Bibliography
├── problems/                   # Problem-specific modeling notes
│   └── 问题4/                  # Q4 modeling steps
├── reports/                    # Generated reports
├── scripts/                    # Utility scripts
├── src/                        # Core source code
│   └── q1-q4 modules           # Question-specific implementations
├── tests/                      # Unit tests
├── handoff/                    # Packaging scripts for team handoff
└── data/                       # Data directory (see data/README.md)
```

## Quick Start

### Prerequisites

- Python 3.11+ (tested with 3.14)
- pip package manager

### Installation

1. Clone this repository:
   ```bash
   git clone <repository-url>
   cd D题归档工程_26
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Set up environment variables:
   ```bash
   cp .env.example .env
   # Edit .env with your API keys (optional, for LLM features)
   ```

### Key Dependencies

- `numpy`, `pandas`, `scipy` - Numerical computing
- `matplotlib`, `seaborn` - Visualization
- `networkx` - Graph algorithms
- `scikit-learn` - Machine learning utilities
- `pydantic` - Data validation
- `openai` - LLM integration (optional)

## Running the Pipelines

### Q1: Baseline Model (Perfect Conditions)

```bash
python scripts/run_q1.py
```

Outputs:
- `outputs/q1_baseline.csv` - Scenario A/B/C cost-time comparisons
- `outputs/fig_q1_*.png` - Pareto frontiers and sensitivity plots

### Q2: Imperfect Conditions (Stochastic Model)

```bash
python scripts/run_q2.py
```

Outputs:
- `outputs/q2_risk_summary.csv` - Risk metrics under failure scenarios
- `outputs/fig_q2_*.png` - Monte Carlo simulation results

### Q3: Water Sustainability (One-Year Guarantee)

```bash
python scripts/run_q3.py
```

Outputs:
- `outputs/q3_water_summary.csv` - Inventory policies and costs
- `outputs/fig_q3_*.png` - Inventory dynamics and stockout risk

### Q4: Environmental Impact Assessment

```bash
python scripts/run_q4.py
```

Outputs:
- `outputs/q4_env_summary.csv` - Environmental metrics (EDI, CO2, soot)
- `outputs/fig_q4_*.png` - Environmental impact visualizations

## Reproducibility

### Fixed Random Seeds

All Monte Carlo simulations use fixed seeds for reproducibility:
- Default seed: 42
- Configure in `configs/risk_params.yaml`

### Key Parameters

| Parameter | Value | Source |
|-----------|-------|--------|
| Total Material (M) | 1×10⁸ metric tons | Problem Statement |
| Start Year | 2050 | Problem Statement |
| Elevator Capacity | 537,000 tons/year | 3 Harbours × 179,000 |
| Rocket Payload | 100-150 tons | Problem Estimate |
| Simulation Horizon | Variable | Model-dependent |

### Running Full Acceptance Tests

```bash
python run_all_acceptance.py
```

## Generating Figures for Paper

All publication-quality figures can be regenerated:

```bash
python scripts/generate_all_figures.py
```

Figures are saved to `docs/最终论文/figs全-2.0/`.

## Citation

If you use this code in your research, please cite:

```bibtex
@misc{mcm2026problemb,
  title={MCM 2026 Problem B: Lunar Infrastructure Transportation Optimization},
  author={Team},
  year={2026},
  howpublished={Mathematical Contest in Modeling}
}
```

## License

This project is for educational purposes as part of MCM 2026.

## Contributing

This is an archived competition submission. For questions, please open an issue.

---

**Note**: This is a sanitized version. Original API keys and personal identifiers have been removed. See `.env.example` for required environment variables.
