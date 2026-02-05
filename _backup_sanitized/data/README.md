# Data Directory

This directory contains input data and generated outputs for the MCM 2026 Problem B models.

## Directory Structure

```
data/
├── raw/                # Raw input data (gitignored)
├── processed/          # Cleaned/transformed data
├── outputs/            # Model outputs (CSV, etc.)
└── sample/             # Sample data for testing
```

## Data Sources

### Problem Parameters (Built-in)

The following parameters are embedded in the code (from problem statement):

| Parameter | Value | Location |
|-----------|-------|----------|
| Total Material Requirement | 1×10⁸ metric tons | `configs/constants.py` |
| Space Elevator Capacity | 537,000 tons/year | `configs/constants.py` |
| Start Year | 2050 | `configs/constants.py` |

### Monte Carlo Parameters

Simulation parameters are defined in `configs/risk_params.yaml`:
- Number of simulations: 1000
- Random seed: 42
- Horizon: 365 days (for Q3)

## Regenerating Data

All outputs can be regenerated from scratch:

```bash
# Generate all Q1-Q4 outputs
python run_all_acceptance.py

# Or run individual questions
python scripts/run_q1.py
python scripts/run_q2.py
python scripts/run_q3.py
python scripts/run_q4.py
```

## Sample Data

A minimal sample dataset is provided for testing:

```
data/sample/
├── sample_launch_schedule.csv
└── sample_inventory_state.csv
```

## Data Privacy

- No personal data is used in this project
- All data is synthetically generated based on problem parameters
- No external API data is stored

## Output File Formats

| File Pattern | Description |
|--------------|-------------|
| `q1_*.csv` | Q1 baseline model outputs |
| `q2_*.csv` | Q2 risk analysis outputs |
| `q3_*.csv` | Q3 water inventory outputs |
| `q4_*.csv` | Q4 environmental impact outputs |

---

*Note: Large output files (>1MB) are gitignored. Regenerate them using the scripts above.*
