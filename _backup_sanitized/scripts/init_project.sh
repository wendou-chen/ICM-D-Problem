#!/usr/bin/env bash
set -euo pipefail

PROJECT_NAME="${1:-ICM-D}"
ROOT_DIR="$(pwd)"

echo "[init] Initializing project in: ${ROOT_DIR}"
echo "[init] Project name label: ${PROJECT_NAME}"

# -------------------------------
# 1) Create directories
# -------------------------------
DIRS=(
  "configs"
  "data/raw"
  "data/interim"
  "data/processed"
  "src/utils"
  "examples"
  "outputs/baseline"
  "outputs/solutions"
  "outputs/metrics"
  "outputs/robust"
  "outputs/exports"
  "outputs/figures_python"
  "artist/kepler"
  "artist/gephi"
  "artist/arcgis_qgis"
  "artist/exports_from_artist"
  "paper/sections"
  "paper/tables"
  "paper/assets"
  "qa"
  "logs"
  "scripts"
)

for d in "${DIRS[@]}"; do
  mkdir -p "${d}"
done

# -------------------------------
# 2) Create .gitignore (safe defaults)
# -------------------------------
if [[ ! -f ".gitignore" ]]; then
cat > .gitignore <<'EOF'
# Python
__pycache__/
*.pyc
*.pyo
*.pyd
*.egg-info/
.venv/
venv/
.env
.ipynb_checkpoints/

# OS
.DS_Store
Thumbs.db

# Data (raw can be large; keep source notes instead)
data/raw/*
!data/raw/notes_source.md

# Outputs (optional: you may want to keep selected outputs)
outputs/*
!outputs/README.md

# Paper build artifacts
paper/*.aux
paper/*.log
paper/*.out
paper/*.toc
paper/*.bbl
paper/*.blg
paper/*.synctex.gz

# Editor
.vscode/
.idea/
EOF
  echo "[init] Created .gitignore"
else
  echo "[init] .gitignore already exists, skipped"
fi

# -------------------------------
# 3) Minimal README.md
# -------------------------------
if [[ ! -f "README.md" ]]; then
cat > README.md <<EOF
# ${PROJECT_NAME}

## Quick Start
1. Put official datasets into \`data/raw/\` (do not modify raw files).
2. Run ETL to generate \`data/processed/\` assets.
3. Run solvers to generate \`outputs/\`.
4. Run visualization to generate \`outputs/figures_python/\` and copy final figures into \`paper/assets/\`.
5. Build paper in \`paper/\`.

## Convention
- Raw data: \`data/raw/\` (read-only)
- Processed data: \`data/processed/\` (single source of truth)
- Solver outputs: \`outputs/\`
- Artist outputs: \`artist/exports_from_artist/\`
- Paper-ready assets: \`paper/assets/\`

## One-command (recommended)
\`\`\`bash
bash run_all.sh
\`\`\`
EOF
  echo "[init] Created README.md"
else
  echo "[init] README.md already exists, skipped"
fi

# -------------------------------
# 4) outputs/README.md (so outputs folder is tracked if you ignore it)
# -------------------------------
if [[ ! -f "outputs/README.md" ]]; then
cat > outputs/README.md <<'EOF'
This folder stores ALL generated outputs.
Suggested structure:
- baseline/: baseline strategy results
- solutions/: per-run solution objects + params snapshot
- metrics/: metrics.csv runtime.csv ablation.csv
- robust/: resilience_table.csv perturbation_table.csv critical_nodes.csv
- exports/: deliverables for artist (Kepler/Gephi)
- figures_python/: python-generated figures (before final paper copy)
EOF
  echo "[init] Created outputs/README.md"
fi

# -------------------------------
# 5) configs/base.yaml (minimal config skeleton)
# -------------------------------
if [[ ! -f "configs/base.yaml" ]]; then
cat > configs/base.yaml <<'EOF'
project:
  name: "ICM-D"
  seed: 42

paths:
  raw_dir: "data/raw"
  processed_dir: "data/processed"
  outputs_dir: "outputs"
  exports_dir: "outputs/exports"
  figures_dir: "outputs/figures_python"

etl:
  crs_target: "EPSG:4326"
  drop_duplicates: true

solver:
  max_iters: 200
  pop_size: 100
  time_limit_sec: 0   # 0 means no limit

robustness:
  perturb_ratio: 0.10
  attack_steps: 11
  monte_carlo_runs: 30

viz:
  dpi: 300
EOF
  echo "[init] Created configs/base.yaml"
fi

# -------------------------------
# 6) run_all.sh (pipeline skeleton)
# -------------------------------
if [[ ! -f "run_all.sh" ]]; then
cat > run_all.sh <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

echo "[run_all] 1) Data validation + ETL"
python -m src.data_validate || true
python -m src.data_loader

echo "[run_all] 2) Baseline"
python examples/demo_baseline.py || true

echo "[run_all] 3) Solvers"
python examples/demo_flow_path_ga.py || true
python examples/demo_flow_minmax_congestion.py || true
python examples/demo_schedule_ssgs_ga.py || true
python examples/demo_tsp_ga_pso_sa.py || true

echo "[run_all] 4) Robustness"
python examples/demo_sensitivity_robustness.py || true

echo "[run_all] 5) Visualization"
python -m src.viz || true

echo "[run_all] Done."
EOF
  chmod +x run_all.sh
  echo "[init] Created run_all.sh"
fi

# -------------------------------
# 7) Create placeholder python modules (safe stubs)
# -------------------------------
touch src/__init__.py
touch src/utils/__init__.py

# Create stubs only if missing (won't overwrite your existing code)
create_stub() {
  local filepath="$1"
  local content="$2"
  if [[ ! -f "${filepath}" ]]; then
    mkdir -p "$(dirname "${filepath}")"
    cat > "${filepath}" <<< "${content}"
    echo "[init] Stub created: ${filepath}"
  fi
}

create_stub "src/utils/seeds.py" \
'def set_seed(seed: int = 42) -> None:
    import random
    random.seed(seed)
    try:
        import numpy as np
        np.random.seed(seed)
    except Exception:
        pass
'

create_stub "src/utils/io.py" \
'import json, pickle
from pathlib import Path
from typing import Any, Dict

def save_json(obj: Dict[str, Any], path: str) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)

def load_json(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_pkl(obj: Any, path: str) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as f:
        pickle.dump(obj, f)

def load_pkl(path: str) -> Any:
    with open(path, "rb") as f:
        return pickle.load(f)
'

create_stub "src/data_validate.py" \
'def main() -> None:
    # TODO: implement missing/duplicate/outlier/crs checks
    print("data_validate: stub (implement checks here).")

if __name__ == "__main__":
    main()
'

create_stub "src/data_loader.py" \
'def main() -> None:
    # TODO: load raw csv/shapefile, clean, transform CRS, build graph.pkl
    print("data_loader: stub (implement ETL here).")

if __name__ == "__main__":
    main()
'

create_stub "examples/demo_baseline.py" \
'def main() -> None:
    print("demo_baseline: stub (implement baselines here).")

if __name__ == "__main__":
    main()
'

# -------------------------------
# 8) Create paper templates
# -------------------------------
if [[ ! -f "paper/figure_inventory.md" ]]; then
cat > paper/figure_inventory.md <<'EOF'
# Figure Inventory (图表清单)

> 规则：论文中每张图必须在此登记，保证可追溯（图编号—文件—来源数据—生成脚本—负责人）。
> 建议写作时按 “先占位、后填充” 的方式维护。

## Legend
- **Fig ID**: 图编号（Fig. 1, Fig. 2, ...）
- **Asset file**: 论文引用的最终文件路径（paper/assets/...）
- **Generated by**: 生成脚本（src/viz.py / artist 工程等）
- **Input data**: 输入数据（data/processed 或 outputs/）
- **Owner**: 负责人（你 / 绘图手 / 写作手）
- **Status**: TODO / DRAFT / FINAL
- **Caption**: 最终图注（可直接粘进论文）

---

## Figures

| Fig ID | Asset file (paper/assets) | Generated by | Input data | Owner | Status | Caption (final) |
|---|---|---|---|---|---|---|
| Fig. 1 | assets/fig_region_basemap.png | artist/kepler/* | data/processed/base_map.csv + boundary.geojson | 绘图手 | TODO | 研究区域与基础地理底图。 |
| Fig. 2 | assets/conv_curve.png | src/viz.py:plot_convergence | outputs/metrics/metrics.csv | 你 | TODO | 算法收敛曲线，展示迭代过程中的目标值下降趋势。 |
| Fig. 3 | assets/heat_network.png | src/viz.py:draw_network_flow | outputs/exports/solution_flows.csv + data/processed/edges.csv | 你 | TODO | 流量/拥塞在网络上的空间分布（颜色为利用率、线宽为流量）。 |
| Fig. 4 | assets/fig_3d_flow.png | artist/kepler/* or artist/gephi/* | outputs/exports/solution_flows.csv | 绘图手 | TODO | 3D 弧线流向可视化，突出主要通道与瓶颈。 |
| Fig. 5 | assets/resilience_curve.png | src/viz.py:plot_resilience_curve | outputs/robust/resilience_table.csv | 你 | TODO | 蓄意攻击/随机攻击下的韧性曲线（攻击比例 vs 性能保持率）。 |
| Fig. 6 | assets/centrality_ccdf.png | src/viz.py:plot_value_distribution(kind=ccdf) | outputs/robust/critical_nodes.csv | 你 | TODO | 节点重要性（如介数中心性）的 CCDF 分布，展示长尾特征。 |

---

## Tables (optional but recommended)

| Table ID | File (paper/tables) | Source csv | Owner | Status | Notes |
|---|---|---|---|---|---|
| Tab. 1 | tables/table_metrics.tex | outputs/metrics/metrics.csv | 写作手 | TODO | 主模型 vs baseline 指标对比 |
| Tab. 2 | tables/table_ablation.tex | outputs/metrics/ablation.csv | 写作手 | TODO | 消融实验：算子开关影响 |
| Tab. 3 | tables/table_robust.tex | outputs/robust/perturbation_table.csv | 写作手 | TODO | 参数±10%敏感度表 |
EOF
  echo "[init] Created paper/figure_inventory.md"
fi

# Section stubs (won't overwrite)
create_stub "paper/sections/intro.md"        "# Introduction\n\nTODO\n"
create_stub "paper/sections/data.md"         "# Data\n\nTODO\n"
create_stub "paper/sections/model.md"        "# Model\n\nTODO\n"
create_stub "paper/sections/algorithm.md"    "# Algorithm\n\nTODO\n"
create_stub "paper/sections/results.md"      "# Results\n\nTODO\n"
create_stub "paper/sections/sensitivity.md"  "# Sensitivity & Robustness\n\nTODO\n"
create_stub "paper/sections/conclusion.md"   "# Conclusion\n\nTODO\n"

# -------------------------------
# 9) QA templates
# -------------------------------
create_stub "qa/repro_checklist.md" \
'# Repro Checklist

- [ ] Fresh environment created from requirements/environment file
- [ ] Raw data placed under data/raw/
- [ ] ETL runs and produces data/processed/graph.pkl etc.
- [ ] Solvers run and produce outputs/metrics/*.csv
- [ ] Robustness runs and produces outputs/robust/*.csv
- [ ] Visualization runs and produces outputs/figures_python/*.png
- [ ] paper/assets contains final figures referenced by paper
'

echo "[init] ✅ Project skeleton ready."
echo "[init] Next: put official data into data/raw/ and implement src/data_loader.py + src/data_validate.py."
