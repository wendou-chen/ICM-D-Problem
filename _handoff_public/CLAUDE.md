# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Environment & Setup

- **Dependencies**: `pip install -r requirements.txt` (Requires Python 3.7+)
- **Key Packages**: `numpy`, `matplotlib`, `networkx`, `pandas`, `geopandas`, `scikit-learn`
- **Environment Variables**:
  - `DEEPSEEK_API_KEY` / `OPENROUTER_API_KEY` (for automated planning/writing features)
  - `PYTHONPATH`: May need to include project root if not running as modules.

## Common Commands

### Verification & Basics
- **Run basic algorithm test**: `python -m mcm_d_heuristics_v3_3_1.examples.test_x2`
- **Validate data**: `python scripts/data_validate.py --raw_dir data/raw`
- **Project Audit**: `python scripts/project_audit.py --strict`

### Data Pipeline (Stage 1)
- **Clean data**: `python scripts/data_clean.py --raw_dir data/raw --out_dir data/processed`
- **Build graph**: `python src/data_loader.py` (Generates `data/processed/graph.pkl`)
- **Baseline analysis**: `python scripts/baseline_analysis.py --graph data/processed/graph.pkl`

### Task Execution
- **Task 1 (Key Bridge)**: `python scripts/run_task1_keybridge_scenarios.py --graph data/processed/graph.pkl ...`
- **Task 2 (Optimization)**:
  - Run hybrid optimization: `python scripts/run_hybrid_pso_ga_task2.py --graph data/processed/graph.pkl ...`
  - Ablation study: `python scripts/run_algorithm_ablation.py --mode all`
  - Resilience test: `python scripts/run_resilience_task2.py ...`
- **Task 3 (MCDA)**: `python scripts/run_task3_mcda.py ...`

### Automation & Reporting
- **Generate Experiment Plan**: `python plan_speciale.py --output plans/plan.json` (Add `--offline` if no API key)
- **Execute Plan**: `python execute_plan.py --plan plans/plan.json --full`
- **Generate Paper Sections**: `python writer.py --plan plans/plan.json --log outputs/experiment_log.jsonl`
- **Compile Paper**: `powershell -File paper/build_submission.ps1`

## Code Architecture

This project is a framework for solving MCM/ICM problems (specifically Network/Optimization) using heuristic algorithms.

### 1. Core Algorithm Library (`mcm_d_heuristics_v3_3_1/`)
- **Design Pattern**: Separates the "Algorithm" (generic) from the "Problem" (specific).
- **Key Files**:
  - `problem.py`: Abstract base class `OptimizationProblem` (defines objective, constraints, decoder).
  - `ga.py`, `pso.py`, `sa.py`: Generic implementations of Genetic Algorithm, Particle Swarm, Simulated Annealing.
  - `hybrid.py`: Orchestrator for hybrid approaches (e.g., PSO -> GA).
- **Usage**: Do not modify these files for specific problems. Subclass `OptimizationProblem` instead.

### 2. Problem Definitions (`problems/`)
- Contains concrete implementations of `OptimizationProblem` for specific tasks (e.g., `bus_route_design_problem.py`).
- This is where objective functions, decoders, and specific constraints live.

### 3. Execution Scripts (`scripts/`)
- **ETL**: `data_clean.py`, `data_validate.py`.
- **Analysis**: `baseline_analysis.py`, `identify_critical_infrastructure.py`.
- **Optimization Runners**: `run_hybrid_pso_ga_task2.py`, `run_task3_mcda.py`.
- **Visualization**: `viz_task2.py`, `viz_task3_resilience.py`.

### 4. Automation Framework (Root)
- **Orchestrator**: `plan_speciale.py` (Planner) -> `execute_plan.py` (Executor) -> `writer.py` (Reporter).
- **Schema**: `schema.py` defines standard I/O for experiments.
- **Tools**: `tools_impl.py` wraps scripts into callable tools for the LLM agent.

## Data Flow
1. **Raw Data** (`data/raw`) → `data_clean.py` → **CSV/Clean** (`data/processed`).
2. **CSV/Clean** → `src/data_loader.py` → **Graph Object** (`data/processed/graph.pkl`).
3. **Graph Object** → **Optimization Scripts** → **Results** (`outputs/`).
4. **Results** → **Writer/Viz** → **Paper/Artifacts**.

## Development Guidelines
- **Importing**: Use module-style execution (`python -m ...`) or ensure `PYTHONPATH` is set to avoid relative import errors with the `mcm_d_heuristics` package.
- **New Problems**: To adapt for a new problem, create a new subclass in `problems/`, adjust `src/data_loader.py` for new data structures, and update `scripts/` runners.
- **Paths**: Scripts generally accept absolute paths or paths relative to the project root.
