# 新题套壳作战手册 (New Problem Runbook)

**生成时间**: 2026-01-19
**基于流程图**: `流程图/D题流程图-2026-01-18-updated.mmd`

---

## 📖 使用说明

本手册指导你如何将当前工程套用到新的ICM/MCM题目。手册分为三部分：

1. **Step-by-Step Runbook**：按流程图步骤，详细说明每一步的操作
2. **全自动模式**：接入API Key后的自动化执行方案
3. **手动模式**：无API Key的离线执行方案

---

## 第一部分：Step-by-Step Runbook（对照流程图）

### 阶段 0: 自动化编排核心 (Step0–Step9+)

#### Step0: 环境变量设置

**目的**: 配置API Key（如果使用全自动模式）

**操作**:
```powershell
# Windows PowerShell（仅当前会话）
$env:DEEPSEEK_API_KEY = "your_key_here"
$env:OPENROUTER_API_KEY = "your_key_here"

# 或使用 .env 文件（推荐，不要入库）
# 在项目根目录创建 .env 文件
DEEPSEEK_API_KEY=your_key_here
OPENROUTER_API_KEY=your_key_here
```

**输入**: API Key（从DeepSeek/OpenRouter获取）  
**输出**: 环境变量（仅当前终端会话可见）  
**新题需要改**: 无（API Key与题目无关）

---

#### Step1: Schema定义

**目的**: 统一I/O，确保写作/审计友好

**文件**: `schema.py`

**操作**: 无需手动执行（已定义好）

**输入**: 无  
**输出**: Pydantic模型（ExperimentPlan, RunResult等）  
**新题需要改**: 
- 如果新题的指标与当前不同，需要修改`RunResult`中的`metrics`字段定义
- 如果新题的实验配置不同，需要修改`ExperimentPlan`的`runs`结构

**优先级**: ⭐⭐⭐（如果指标结构完全一致，可不动）

---

#### Step2: Runner统一执行器

**目的**: 统一执行命令+收集artifacts+tail日志（Windows编码errors=replace防崩）

**文件**: `runner.py`

**操作**: 无需手动执行（被其他脚本调用）

**输入**: 命令列表  
**输出**: 执行结果 + 日志  
**新题需要改**: 无（通用执行器）

---

#### Step3: 工具实现与Schema

**目的**: 实现LLM可调用的工具列表

**文件**: `tools_impl.py`, `tool_schemas.py`, `tools.json`

**操作**: 无需手动执行（被agent_exec.py调用）

**输入**: 工具参数（通过tools.json定义）  
**输出**: RunResult  
**新题需要改**: 
- 如果新题需要新的工具函数，在`tools_impl.py`中添加
- 在`tool_schemas.py`和`tools.json`中注册新工具
- 如果新题的脚本入口不同，修改`tools_impl.py`中的脚本调用路径

**优先级**: ⭐⭐⭐⭐（工具函数需要适配新题的脚本）

---

#### Step4: 生成实验计划

**目的**: 生成ExperimentPlan JSON（支持--prior注入硬约束）

**文件**: `plan_speciale.py`

**操作**:
```powershell
# 全自动（有API Key）
python plan_speciale.py --output plans/plan.json

# 带先验约束
python plan_speciale.py --prior docs/human_prior_task2.md --output plans/plan_with_prior.json

# 离线stub（无API Key）
python plan_speciale.py --offline --output plans/plan.json
```

**输入**: 
- `docs/human_prior_task2.md`（可选--prior）
- API Key（如果在线模式）

**输出**: `plans/plan.json`  
**产物位置**: `plans/`  
**新题需要改**: 
- **必须修改**: `docs/human_prior_task2.md`（描述新题的算法主线和约束）
- 如果新题的工具列表不同，修改`plan_speciale.py`中的工具列表
- 修改`plans/plan_templates.json`（如果有模板）

**优先级**: ⭐⭐⭐⭐⭐（必须为新题定制先验知识）

---

#### Step5: 执行实验计划

**目的**: 按plan顺序执行runs（强制顺序&参数覆盖，防模型乱序）

**文件**: `execute_plan.py`

**操作**:
```powershell
# 干运行（检查plan）
python execute_plan.py --plan plans/plan.json --dry-run

# 完整运行
python execute_plan.py --plan plans/plan.json --full

# 只运行前k个runs
python execute_plan.py --plan plans/plan.json --full-first-k 3
```

**输入**: `plans/plan.json`  
**输出**: `outputs/experiment_log*.jsonl`  
**产物位置**: `outputs/`  
**新题需要改**: 
- 确保`plans/plan.json`中的工具参数正确
- 如果新题的脚本参数不同，修改plan.json中的args

**优先级**: ⭐⭐⭐⭐（plan.json需要适配新题）

---

#### Step6: 生成论文章节

**目的**: plan+log → paper/sections/*.tex（offline必可用；可选LLM润色）

**文件**: `writer.py`

**操作**:
```powershell
python writer.py --plan plans/plan.json --log outputs/experiment_log.jsonl --output paper/sections/
```

**输入**: `plans/plan.json`, `outputs/experiment_log*.jsonl`  
**输出**: `paper/sections/{methods,results,robustness,limitations,ai_tools_report}.tex`  
**产物位置**: `paper/sections/`  
**新题需要改**: 
- 如果新题的结构不同，修改`writer.py`中的章节生成逻辑
- 如果新题的指标不同，修改`writer.py`中的指标提取逻辑

**优先级**: ⭐⭐⭐（通常需要手动调整LaTeX）

---

#### Step7-8: 论文编译

**目的**: 编译LaTeX生成PDF

**文件**: `paper/build.ps1`, `paper/build_submission.ps1`

**操作**:
```powershell
# 编译提交版（≤25页）
.\paper\build_submission.ps1

# 编译完整版
.\paper\build.ps1
```

**输入**: `paper/main_submission.tex`, `paper/sections/*.tex`  
**输出**: `paper/main_submission.pdf`, `paper/ai_appendix.pdf`  
**产物位置**: `paper/`  
**新题需要改**: 
- 修改`paper/main_submission.tex`中的题目信息
- 根据需要修改`paper/sections/*.tex`的内容（通常由writer.py生成后手动调整）

**优先级**: ⭐⭐⭐⭐（必须修改题目信息）

---

#### Step9+: 打包交付

**目的**: 按工具/任务切片打包（给写作手/绘图手）

**文件**: `handoff/pack_task_artifacts.py`, `handoff/package_teamshare.ps1`

**操作**:
```powershell
# 打包各任务
python handoff/pack_task_artifacts.py

# 一键总包
.\handoff\package_teamshare.ps1
```

**输入**: `outputs/`, `paper/*.pdf`  
**输出**: `handoff/all_teamshare.zip`  
**产物位置**: `handoff/`  
**新题需要改**: 
- 如果新题的任务结构不同，修改`handoff/pack_task_artifacts.py`中的打包逻辑

**优先级**: ⭐⭐（如果任务结构一致，可不动）

---

### 阶段 1: 数据清洗与构图 (ETL & Graph Build)

#### Step1: 数据审计

**目的**: 验证原始数据质量

**脚本**: `scripts/data_validate.py`

**命令**:
```powershell
python scripts/data_validate.py --raw_dir data/raw
```

**输入**: `data/raw/*`  
**输出**: 验证报告  
**产物位置**: 控制台输出  
**新题需要改**: 
- 如果新题的数据格式不同，修改`scripts/data_validate.py`中的验证逻辑

**优先级**: ⭐⭐⭐⭐（必须适配新题数据格式）

---

#### Step2: 数据清洗

**目的**: raw → processed 清洗

**脚本**: `scripts/data_clean.py`

**命令**:
```powershell
python scripts/data_clean.py --raw_dir data/raw --out_dir data/processed
```

**输入**: `data/raw/*`  
**输出**: `data/processed/{nodes,edges,bus_stops}_clean.csv`, `cleaning_log.md`  
**产物位置**: `data/processed/`  
**新题需要改**: 
- **必须修改**: `scripts/data_clean.py`（适配新题的CSV列名、清洗规则）
- **必须修改**: 新题的数据字段映射逻辑

**优先级**: ⭐⭐⭐⭐⭐（必须为新题定制清洗逻辑）

---

#### Step3: 构建广义成本矩阵

**目的**: 计算边的广义成本（时间/距离/费用）

**脚本**: `scripts/build_generalized_cost.py`

**命令**:
```powershell
python scripts/build_generalized_cost.py --edges data/processed/edges_clean.csv
```

**输入**: `data/processed/edges_clean.csv`  
**输出**: 成本矩阵（写入edges或单独文件）  
**产物位置**: `data/processed/`  
**新题需要改**: 
- 如果新题的成本计算方式不同，修改`scripts/build_generalized_cost.py`
- 修改成本公式（当前可能是时间+距离，新题可能是其他）

**优先级**: ⭐⭐⭐⭐（必须适配新题成本定义）

---

#### Step4: 构建多层网络图

**目的**: 构建多层网络图 & 导出绘图资产

**脚本**: `src/data_loader.py`

**命令**:
```powershell
python src/data_loader.py
```

**输入**: `data/processed/{nodes,edges,bus_stops}_clean.csv`  
**输出**: 
- `data/processed/graph.pkl` - **核心图对象**（算法唯一输入）
- `data/processed/graph_{nodes,edges,edges_kepler}.csv`
- `data/processed/boundary.geojson`
- `data/processed/base_map.csv`

**产物位置**: `data/processed/`  
**新题需要改**: 
- **必须修改**: `src/data_loader.py`（适配新题的图结构）
- 如果新题是多层网络，修改层的定义
- 如果新题需要不同的节点/边属性，修改图构建逻辑

**优先级**: ⭐⭐⭐⭐⭐（必须为新题定制图构建逻辑）

---

### 阶段 1.5: Baseline + 关键设施 + Stakeholder 映射

#### Step5: Baseline分析

**目的**: OD抽样连通性/代价 sanity + 瓶颈识别

**脚本**: `scripts/baseline_analysis.py`

**命令**:
```powershell
python scripts/baseline_analysis.py --graph data/processed/graph.pkl --od_samples 5000
```

**输入**: `data/processed/graph.pkl`  
**输出**: `outputs/baseline/baseline_metrics.csv`, `bottlenecks_top10_nodes.csv`, `baseline_report.md`  
**产物位置**: `outputs/baseline/`  
**新题需要改**: 
- 如果新题的基线定义不同，修改`scripts/baseline_analysis.py`
- 修改OD抽样策略（如果新题不需要OD，改为其他抽样方式）

**优先级**: ⭐⭐⭐⭐（必须适配新题基线定义）

---

#### Step6: 关键设施识别

**目的**: 识别关键设施（Key Bridge & US-40，确定性方法）

**脚本**: `scripts/identify_critical_infrastructure.py`

**命令**:
```powershell
python scripts/identify_critical_infrastructure.py --edges data/processed/edges_clean.csv --boundary data/processed/boundary.geojson
```

**输入**: `data/processed/edges_clean.csv`, `data/processed/boundary.geojson`  
**输出**: `outputs/task1/{key_bridge_edges,us40_edges}.csv`, `critical_locations_map.png`, `critical_infra_report.md`  
**产物位置**: `outputs/task1/`  
**新题需要改**: 
- **必须修改**: `scripts/identify_critical_infrastructure.py`（新题的关键设施识别规则完全不同）
- 修改正则表达式匹配规则（当前是Key Bridge/US-40，新题可能是其他）
- 修改空间聚类参数（如果新题需要）

**优先级**: ⭐⭐⭐⭐⭐（必须为新题定制关键设施识别逻辑）

---

#### Step7: Stakeholder映射

**目的**: OD→stakeholder（规则级联+KDTree）

**脚本**: `scripts/stakeholder_mapping.py`

**命令**:
```powershell
python scripts/stakeholder_mapping.py --graph_nodes data/processed/graph_nodes.csv --bus_stops data/processed/bus_stops_clean.csv --boundary data/processed/boundary.geojson
```

**输入**: `data/processed/{graph_nodes.csv,bus_stops_clean.csv}`, `data/processed/boundary.geojson`  
**输出**: `outputs/stakeholders/{od_stakeholder_labels,stakeholder_summary}.csv`, `docs/stakeholder_mapping.md`  
**产物位置**: `outputs/stakeholders/`, `docs/`  
**新题需要改**: 
- **必须修改**: `scripts/stakeholder_mapping.py`（新题的stakeholder分类规则完全不同）
- 修改stakeholder分类规则（当前是Transit-dependent等，新题可能是其他）
- 修改公交站距离阈值（如果新题不需要公交站，改为其他判定方式）

**优先级**: ⭐⭐⭐⭐⭐（必须为新题定制stakeholder映射逻辑）

---

### 阶段 2: Task 1 — Key Bridge 情景

#### Step8: Key Bridge情景评估

**目的**: 删边/改权重 → 情景评估（口径对齐Task2）

**脚本**: `scripts/run_task1_keybridge_scenarios.py`

**命令**:
```powershell
python scripts/run_task1_keybridge_scenarios.py --graph data/processed/graph.pkl --key_edges outputs/task1/key_bridge_edges.csv --stakeholder_labels outputs/stakeholders/od_stakeholder_labels.csv
```

**输入**: 
- `data/processed/graph.pkl`
- `outputs/task1/key_bridge_edges.csv`
- `outputs/stakeholders/od_stakeholder_labels.csv`

**输出**: `outputs/task1/{metrics_by_stakeholder,metrics_overall,delta_metrics_by_stakeholder}.csv`  
**产物位置**: `outputs/task1/`  
**新题需要改**: 
- **必须修改**: `scripts/run_task1_keybridge_scenarios.py`（新题的Task1情景可能完全不同）
- 修改情景定义（当前是baseline/collapse/rebuild，新题可能是其他）
- 修改评估指标（如果新题的指标不同）

**优先级**: ⭐⭐⭐⭐⭐（必须为新题定制Task1逻辑）

---

### 阶段 3: Task 2 — 公交线路优化

#### Step9: 候选线路生成（如需要）

**目的**: 生成候选公交线路集合（优化变量）

**操作**: 
- 如果已有候选线路文件，跳过
- 否则，在`scripts/run_hybrid_pso_ga_task2.py`中会自动生成mock candidates

**输入**: 无（或手动准备JSON文件）  
**输出**: `data/processed/candidates_task2.json`  
**产物位置**: `data/processed/`  
**新题需要改**: 
- **必须修改**: 候选生成逻辑（如果新题的优化变量不是公交线路）
- 修改JSON格式（如果新题的变量结构不同）

**优先级**: ⭐⭐⭐⭐⭐（必须为新题定制候选生成逻辑）

---

#### Step10A: Task2 消融与超参扫描

**目的**: 批量跑 PSO-only/GA-only/Hybrid 的网格 + 多随机种子

**脚本**: `scripts/run_algorithm_ablation.py`

**命令（Smoke）**:
```powershell
python scripts/run_algorithm_ablation.py --mode all --dry-run
```

**命令（Full）**:
```powershell
python scripts/run_algorithm_ablation.py --mode all --seed_base 42 --n_repeats 5
```

**输入**: 
- `data/processed/graph.pkl`
- `data/processed/candidates_task2.json`

**输出**:
- `outputs/task2/ablation_results.csv`
- `outputs/task2/ablation_logs/*.json`

**产物位置**: `outputs/task2/`  
**新题需要改**:
- 若新题算法/参数网格不同，修改 `scripts/run_algorithm_ablation.py` 中的 grid
- 若问题构建逻辑不同，修改 `scripts/task2_problem_factory.py`

**优先级**: ????（论文对比实验必需）

---

#### Step10B: Task2 对比分析与作图

**目的**: 读取消融结果，生成论文级对比表 + 图 + 建议

**脚本**: `scripts/analyze_ablation_results.py`

**命令**:
```powershell
python scripts/analyze_ablation_results.py --feasible_only
```

**输入**:
- `outputs/task2/ablation_results.csv`
- `outputs/task2/ablation_logs/*.json`

**输出**:
- `outputs/task2/ablation_summary.md`
- `outputs/task2/viz/*.png`

**产物位置**: `outputs/task2/`  
**写作接入**: 当前 writer 未自动消费，需要手动拷贝 `ablation_summary.md` 中的 LaTeX snippet  
**新题需要改**:
- 若指标不同，调整 `scripts/analyze_ablation_results.py` 的列解析与图表

**优先级**: ????（论文对比与可视化必需）

---

#### Step10C: Hybrid PSO→GA优化

**目的**: Hybrid PSO→GA选择线路（主入口）

**脚本**: `scripts/run_hybrid_pso_ga_task2.py`

**命令**:
```powershell
python scripts/run_hybrid_pso_ga_task2.py --graph data/processed/graph.pkl --candidates data/processed/candidates_task2.json --stakeholder_labels outputs/stakeholders/od_stakeholder_labels.csv --output_dir outputs/task2
```

**输入**: 
- `data/processed/graph.pkl`
- `data/processed/candidates_task2.json`
- `outputs/stakeholders/od_stakeholder_labels.csv`

**输出**: 
- `outputs/task2/metrics.csv`
- `outputs/task2/best_solution.json`
- `outputs/task2/convergence_history.csv`
- `outputs/task2/metrics_by_stakeholder.csv`
- `outputs/task2/hybrid_log.json`

**产物位置**: `outputs/task2/`  
**新题需要改**: 
- **必须修改**: `problems/bus_route_design_problem.py`（实现新题的OptimizationProblem子类）
- **必须修改**: `scripts/run_hybrid_pso_ga_task2.py`（适配新题的问题类）
- 修改目标函数（如果新题的目标不同）
- 修改约束条件（如果新题的约束不同）
- 修改解码器（如果新题的解码方式不同）

**优先级**: ⭐⭐⭐⭐⭐（必须为新题定制问题定义和优化脚本）

---

#### Step11: Task2增量计算

**目的**: Task2相对collapse baseline的Δ

**脚本**: `scripts/compute_delta_metrics_task2.py`

**命令**:
```powershell
python scripts/compute_delta_metrics_task2.py --baseline outputs/task1/metrics_by_stakeholder.csv --task2 outputs/task2/metrics_by_stakeholder.csv --output outputs/task2/delta_metrics_by_stakeholder.csv
```

**输入**: `outputs/task1/metrics_by_stakeholder.csv`, `outputs/task2/metrics_by_stakeholder.csv`  
**输出**: `outputs/task2/delta_metrics_by_stakeholder.csv`  
**产物位置**: `outputs/task2/`  
**新题需要改**: 
- 如果新题的增量计算方式不同，修改`scripts/compute_delta_metrics_task2.py`

**优先级**: ⭐⭐⭐（通常不需要大改）

---

#### Step12: Task2鲁棒性测试

**目的**: 随机/定向移除鲁棒性

**脚本**: `scripts/run_resilience_task2.py`

**命令**:
```powershell
python scripts/run_resilience_task2.py --solution outputs/task2/best_solution.json --graph data/processed/graph.pkl
```

**输入**: `outputs/task2/best_solution.json`, `data/processed/graph.pkl`  
**输出**: `outputs/task2/{resilience_table.csv,resilience_curve.csv}`  
**产物位置**: `outputs/task2/`  
**新题需要改**: 
- 如果新题的鲁棒性测试方式不同，修改`scripts/run_resilience_task2.py`
- 修改攻击策略（随机/定向）的定义

**优先级**: ⭐⭐⭐⭐（必须适配新题的鲁棒性定义）

---

#### Step13: Task2可视化

**目的**: 一键出图+Kepler+打包

**脚本**: `scripts/viz_task2.py`

**命令**:
```powershell
python scripts/viz_task2.py --output_dir outputs/task2
```

**输入**: `outputs/task2/*.csv`, `outputs/task2/best_solution.json`  
**输出**: `outputs/task2/viz/figures/*.png`, `solution_flows.csv`, `plot_pack_*.zip`  
**产物位置**: `outputs/task2/viz/`  
**新题需要改**: 
- 如果新题的可视化需求不同，修改`scripts/viz_task2.py`
- 修改图表类型（如果新题需要不同的图）

**优先级**: ⭐⭐⭐（通常需要调整图例和标签）

---

### 阶段 4: Task 3 — MCDA推荐

#### Step14: MCDA项目对比

**目的**: 项目对比（task2_bus_project vs us40_walk_improve）

**脚本**: `scripts/run_task3_mcda.py`

**命令**:
```powershell
python scripts/run_task3_mcda.py --task2_solution outputs/task2/best_solution.json --us40_edges outputs/task1/us40_edges.csv
```

**输入**: `outputs/task2/best_solution.json`, `outputs/task1/us40_edges.csv`  
**输出**: `outputs/task3/{alternatives.csv,project_metrics_by_stakeholder.csv,mcda_scores.csv}`  
**产物位置**: `outputs/task3/`  
**新题需要改**: 
- **必须修改**: `scripts/run_task3_mcda.py`（新题的Task3项目可能完全不同）
- 修改项目定义（当前是两个项目，新题可能是其他）
- 修改MCDA权重和指标（如果新题的决策准则不同）

**优先级**: ⭐⭐⭐⭐⭐（必须为新题定制Task3逻辑）

---

#### Step15: Task3决策鲁棒性

**目的**: α/β/US40参数扰动 → 决策稳定性

**脚本**: `scripts/run_resilience_task3_mcda_sensitivity.py`

**命令**:
```powershell
python scripts/run_resilience_task3_mcda_sensitivity.py --mcda_scores outputs/task3/mcda_scores.csv
```

**输入**: `outputs/task3/mcda_scores.csv`  
**输出**: `outputs/task3/resilience/{experiment_matrix.csv,robustness_table.csv,robustness_curve.csv}`  
**产物位置**: `outputs/task3/resilience/`  
**新题需要改**: 
- **必须修改**: `scripts/run_resilience_task3_mcda_sensitivity.py`（新题的敏感性参数不同）
- 修改参数扰动范围（α/β/US40，新题可能是其他参数）

**优先级**: ⭐⭐⭐⭐⭐（必须适配新题的敏感性参数）

---

#### Step16: Task3可视化

**目的**: 稳定率曲线+margin曲线+US40热力图

**脚本**: `scripts/viz_task3_resilience.py`

**命令**:
```powershell
python scripts/viz_task3_resilience.py --output_dir outputs/task3/resilience
```

**输入**: `outputs/task3/resilience/*.csv`  
**输出**: `outputs/task3/resilience/viz/figures/*.png`, `plot_pack_task3_resilience.zip`  
**产物位置**: `outputs/task3/resilience/viz/`  
**新题需要改**: 
- 如果新题的可视化需求不同，修改`scripts/viz_task3_resilience.py`

**优先级**: ⭐⭐⭐（通常需要调整图例）

---

### 阶段 5: 复现审计 + 论文交付

#### Step17: 一键复现Task2

**目的**: clean→loader→task2→resilience→viz→audit

**脚本**: `scripts/reproduce_task2.ps1`

**命令**:
```powershell
powershell -ExecutionPolicy Bypass -File scripts\reproduce_task2.ps1
```

**输入**: 原始数据  
**输出**: Task2完整产物  
**产物位置**: `outputs/task2/`  
**新题需要改**: 
- 如果新题的复现流程不同，修改`scripts/reproduce_task2.ps1`

**优先级**: ⭐⭐⭐（通常不需要大改）

---

#### Step18: 项目审计

**目的**: Stage A–G PASS

**脚本**: `scripts/project_audit.py`

**命令**:
```powershell
python scripts/project_audit.py --strict
```

**输入**: 所有输出文件  
**输出**: 审计报告  
**产物位置**: `outputs/audit/`  
**新题需要改**: 
- 如果新题的审计标准不同，修改`scripts/project_audit.py`

**优先级**: ⭐⭐⭐⭐（必须适配新题的审计标准）

---

## 第二部分：全自动模式（接入API Key）

### 环境准备

1. **设置API Key**（不要入库）:
```powershell
# 方式1: 当前会话环境变量
$env:DEEPSEEK_API_KEY = "your_key_here"
$env:OPENROUTER_API_KEY = "your_key_here"

# 方式2: .env 文件（推荐）
# 在项目根目录创建 .env
DEEPSEEK_API_KEY=your_key_here
OPENROUTER_API_KEY=your_key_here
```

2. **安装依赖**:
```powershell
pip install -r requirements.txt
```

### 完整命令链

```powershell
# 1. 生成实验计划（带先验约束）
python plan_speciale.py --prior docs/human_prior_task2.md --output plans/plan.json

# 2. 执行计划（完整运行）
python execute_plan.py --plan plans/plan.json --full

# 2.1 消融与分析（如 plan 已包含 run_task2_ablation / analyze_task2_ablation 则自动运行）
# 若未包含，可手动在 plan.json 的 runs 中加入对应 tool_name

# 3. 生成论文章节
python writer.py --plan plans/plan.json --log outputs/experiment_log.jsonl --output paper/sections/

# 4. 编译论文
.\paper\build_submission.ps1

# 5. 打包交付
.\handoff\package_teamshare.ps1
```

### 无Key时的Fallback

如果无API Key，以下步骤会自动fallback为offline stub：

1. **plan_speciale.py**: 使用`--offline`参数，生成stub计划
2. **agent_exec.py**: 如果API调用失败，会fallback为本地执行
3. **writer.py**: offline模式必可用（不使用LLM）

**Fallback提示**: 脚本会输出`[OFFLINE MODE]`或`[STUB]`标记，表明正在使用离线模式。

---

## 第三部分：手动模式（无Key，离线执行）

### 最小可跑模式（Smoke Test）

```powershell
# 1. 数据清洗（快速验证）
python scripts/data_clean.py --raw_dir data/raw --out_dir data/processed

# 2. 构建图（快速验证）
python src/data_loader.py

# 3. Task2 Smoke Test（小规模）
python scripts/run_hybrid_pso_ga_task2.py --graph data/processed/graph.pkl --candidates data/processed/candidates_task2.json --K 10 --pso_iter 5 --ga_gen 5 --output_dir outputs/task2_smoke

# 4. Task2 Ablation Smoke
python scripts/run_algorithm_ablation.py --mode all --dry-run

# 5. Ablation Analysis
python scripts/analyze_ablation_results.py --feasible_only
```

### 正式全跑模式（Full）

```powershell
# === 阶段1: 数据准备 ===
python scripts/data_validate.py --raw_dir data/raw
python scripts/data_clean.py --raw_dir data/raw --out_dir data/processed
python scripts/build_generalized_cost.py --edges data/processed/edges_clean.csv
python src/data_loader.py

# === 阶段1.5: Baseline + 关键设施 ===
python scripts/baseline_analysis.py --graph data/processed/graph.pkl --od_samples 5000
python scripts/identify_critical_infrastructure.py --edges data/processed/edges_clean.csv --boundary data/processed/boundary.geojson
python scripts/stakeholder_mapping.py --graph_nodes data/processed/graph_nodes.csv --bus_stops data/processed/bus_stops_clean.csv --boundary data/processed/boundary.geojson

# === 阶段2: Task1 ===
python scripts/run_task1_keybridge_scenarios.py --graph data/processed/graph.pkl --key_edges outputs/task1/key_bridge_edges.csv --stakeholder_labels outputs/stakeholders/od_stakeholder_labels.csv

# === 阶段3: Task2 ===
python scripts/run_hybrid_pso_ga_task2.py --graph data/processed/graph.pkl --candidates data/processed/candidates_task2.json --stakeholder_labels outputs/stakeholders/od_stakeholder_labels.csv --output_dir outputs/task2
python scripts/run_algorithm_ablation.py --mode all --seed_base 42 --n_repeats 5
python scripts/analyze_ablation_results.py --feasible_only
python scripts/compute_delta_metrics_task2.py --baseline outputs/task1/metrics_by_stakeholder.csv --task2 outputs/task2/metrics_by_stakeholder.csv --output outputs/task2/delta_metrics_by_stakeholder.csv
python scripts/run_resilience_task2.py --solution outputs/task2/best_solution.json --graph data/processed/graph.pkl
python scripts/viz_task2.py --output_dir outputs/task2

# === 阶段4: Task3 ===
python scripts/run_task3_mcda.py --task2_solution outputs/task2/best_solution.json --us40_edges outputs/task1/us40_edges.csv
python scripts/run_resilience_task3_mcda_sensitivity.py --mcda_scores outputs/task3/mcda_scores.csv
python scripts/viz_task3_resilience.py --output_dir outputs/task3/resilience

# === 阶段5: 论文编译（可选） ===
.\paper\build_submission.ps1

# === 打包交付 ===
python handoff/pack_task_artifacts.py
.\handoff\package_teamshare.ps1
```

### 独立脚本入口清单

所有可独立运行的脚本（按执行顺序）：

1. `scripts/data_validate.py` - 数据审计
2. `scripts/data_clean.py` - 数据清洗
3. `scripts/build_generalized_cost.py` - 成本矩阵
4. `src/data_loader.py` - 构建图
5. `scripts/baseline_analysis.py` - Baseline分析
6. `scripts/identify_critical_infrastructure.py` - 关键设施
7. `scripts/stakeholder_mapping.py` - Stakeholder映射
8. `scripts/run_task1_keybridge_scenarios.py` - Task1
9. `scripts/run_hybrid_pso_ga_task2.py` - Task2优化
10. `scripts/run_algorithm_ablation.py` - Task2消融与超参扫描
11. `scripts/analyze_ablation_results.py` - Task2消融分析与作图
12. `scripts/compute_delta_metrics_task2.py` - Task2增量
13. `scripts/run_resilience_task2.py` - Task2鲁棒性
14. `scripts/viz_task2.py` - Task2可视化
15. `scripts/run_task3_mcda.py` - Task3 MCDA
16. `scripts/run_resilience_task3_mcda_sensitivity.py` - Task3敏感性
17. `scripts/viz_task3_resilience.py` - Task3可视化
18. `scripts/project_audit.py` - 项目审计
19. `scripts/reproduce_task2.ps1` - 一键复现Task2

---

## 第四部分：新题套壳最少修改清单（Top 10）

### ⭐⭐⭐⭐⭐ 最高优先级（必须修改）

1. **数据加载器** (`src/data_loader.py`)
   - 适配新题的CSV列名和结构
   - 修改图构建逻辑（节点/边/属性）
   - 修改多层网络定义（如果新题不需要多层，简化为单层）

2. **数据清洗脚本** (`scripts/data_clean.py`)
   - 适配新题的原始数据格式
   - 修改清洗规则（去重、缺失值处理、异常值过滤）
   - 修改字段映射和重命名

3. **问题定义** (`problems/bus_route_design_problem.py` 或新建)
   - 创建新题的OptimizationProblem子类
   - 实现`decode()`方法（如何从genome解码为解）
   - 实现`evaluate_solution()`方法（如何评估解的成本）
   - 实现`constraints()`方法（约束检查）

4. **Task2优化脚本** (`scripts/run_hybrid_pso_ga_task2.py`)
   - 修改问题类实例化
   - 修改候选生成逻辑（如果新题的优化变量不同）
   - 修改目标函数参数（budget、penalty等）

5. **先验知识文档** (`docs/human_prior_task2.md`)
   - 描述新题的算法主线（如PSO→GA）
   - 定义硬约束和参数范围
   - 说明问题的特殊性

### ⭐⭐⭐⭐ 高优先级（通常需要修改）

6. **关键设施识别** (`scripts/identify_critical_infrastructure.py`)
   - 修改识别规则（正则表达式、空间聚类）
   - 如果新题没有"关键设施"概念，改为其他识别逻辑

7. **Stakeholder映射** (`scripts/stakeholder_mapping.py`)
   - 修改stakeholder分类规则
   - 修改判定条件（当前是公交站距离，新题可能是其他）

8. **Task1情景脚本** (`scripts/run_task1_keybridge_scenarios.py`)
   - 修改情景定义（baseline/collapse/rebuild）
   - 修改评估指标（如果新题的指标不同）

9. **Task3 MCDA脚本** (`scripts/run_task3_mcda.py`)
   - 修改项目定义（当前是两个项目）
   - 修改MCDA权重和指标

10. **实验计划模板** (`plans/plan_templates.json` 或 `plan_speciale.py`)
    - 修改工具列表（如果新题需要新的工具）
    - 修改run配置（参数、预期产物）

### ⭐⭐⭐ 中优先级（可能需要调整）

11. **成本计算** (`scripts/build_generalized_cost.py`)
    - 如果新题的成本定义不同

12. **鲁棒性测试** (`scripts/run_resilience_task2.py`, `scripts/run_resilience_task3_mcda_sensitivity.py`)
    - 如果新题的鲁棒性定义不同

13. **可视化脚本** (`scripts/viz_task2.py`, `scripts/viz_task3_resilience.py`)
    - 调整图例和标签

14. **论文主文件** (`paper/main_submission.tex`)
    - 修改题目信息
    - 调整章节结构（如果新题的结构不同）

---

## 第五部分：常见踩坑排查（Top 10）

### 1. 图对象缺失或格式错误

**症状**: `FileNotFoundError: graph.pkl not found` 或 `AttributeError: graph has no attribute 'xxx'`

**排查**:
- 检查`data/processed/graph.pkl`是否存在
- 运行`scripts/inspect_graph_attrs.py`检查图属性
- 确认`src/data_loader.py`执行成功

**解决**: 重新运行`src/data_loader.py`，检查CSV列名是否匹配

---

### 2. CSV列名不匹配

**症状**: `KeyError: 'xxx'` 或 `ColumnNotFoundError`

**排查**:
- 检查`data/processed/*_clean.csv`的列名
- 对比脚本中期望的列名（grep搜索脚本中的列名引用）

**解决**: 修改`scripts/data_clean.py`的列名映射，或修改脚本中的列名引用

---

### 3. 优化算法不收敛

**症状**: 收敛曲线波动大，或始终不下降

**排查**:
- 检查目标函数是否合理（数值范围）
- 检查解码器是否正确（`problem.decode()`）
- 检查约束是否过严

**解决**: 
- 调整目标函数缩放因子
- 检查解码器逻辑
- 放宽约束条件

---

### 4. 不可达OD对过多

**症状**: `reachable_ratio < 0.8`，触发Guard失败

**排查**:
- 检查图是否连通
- 检查OD对采样是否合理
- 检查成本矩阵是否有异常值

**解决**:
- 检查图构建逻辑（确保图连通）
- 调整OD采样策略
- 检查成本计算逻辑（是否有无穷大值）

---

### 5. 候选生成失败

**症状**: `candidates_task2.json not found` 或格式错误

**排查**:
- 检查候选生成函数是否执行
- 检查JSON格式是否正确

**解决**: 
- 手动运行候选生成逻辑
- 检查JSON文件格式

---

### 6. 鲁棒性测试卡住

**症状**: `run_resilience_task2.py`运行时间过长

**排查**:
- 检查`ratios`参数范围（是否过大）
- 检查`n_trials`参数（是否过多）

**解决**:
- 使用smoke test参数（`--ratios 0,0.1 --n_trials 2`）
- 逐步增加参数规模

---

### 7. 消融组合爆炸（运行时间过长）

**症状**: `run_algorithm_ablation.py` 运行过久或组合数超预期  

**排查**:
- 检查 grid 是否过大（PSO/GA/Hybrid 叠加）
- 检查 `--n_repeats` 是否过高

**解决**:
- 使用 `--max_runs` 或 `--sample_runs`
- 先 `--dry-run` 验证流程

---

### 8. params_json 展平失败或 log_path 缺失

**症状**: `analyze_ablation_results.py` 画不出收敛曲线或字段缺失  

**排查**:
- 检查 `ablation_results.csv` 的 `params_json` 是否是合法 JSON
- 检查 `log_path` 指向的 JSON 是否存在

**解决**:
- 重新跑 `run_algorithm_ablation.py`（必要时 `--force`）
- 确保 `outputs/task2/ablation_logs/` 未被清理

---

### 9. 可视化脚本报错

**症状**: `matplotlib`或`geopandas`相关错误

**排查**:
- 检查数据文件是否存在
- 检查坐标系统是否匹配（WGS84 vs 投影坐标系）

**解决**:
- 安装缺失依赖（`pip install geopandas matplotlib`）
- 检查CSV中的坐标列（lon/lat格式）

---

### 10. LaTeX编译失败

**症状**: `pdflatex`报错或缺失引用

**排查**:
- 检查`paper/sections/*.tex`是否存在
- 检查`references.bib`格式
- 检查图片路径是否正确

**解决**:
- 运行`paper/build.ps1`查看详细错误
- 检查LaTeX语法（特殊字符转义）
- 确保所有引用的图片文件存在

---

### 11. 实验计划执行失败

**症状**: `execute_plan.py`报错`tool not found`或`artifact not found`

**排查**:
- 检查`plans/plan.json`中的工具名称是否与`tools.json`匹配
- 检查预期产物路径是否正确

**解决**:
- 使用`--dry-run`检查plan
- 修改plan.json中的工具名称或参数

---

### 12. API Key失效或无响应

**症状**: `plan_speciale.py`或`agent_exec.py`报API错误

**排查**:
- 检查环境变量是否设置（`echo $env:DEEPSEEK_API_KEY`）
- 检查网络连接
- 检查API额度是否用尽

**解决**:
- 使用`--offline`参数fallback到stub模式
- 检查`.env`文件格式
- 更新API Key

---

## 附录：流程图节点映射表

| 流程图节点 | 实际脚本/模块 | 优先级 |
|-----------|--------------|--------|
| Step0 环境变量 | `.env`文件或`$env:DEEPSEEK_API_KEY` | ⭐⭐⭐ |
| Step1 Schema | `schema.py` | ⭐⭐⭐ |
| Step2 Runner | `runner.py` | ⭐ |
| Step3 工具实现 | `tools_impl.py`, `tool_schemas.py` | ⭐⭐⭐⭐ |
| Step4 计划生成 | `plan_speciale.py` | ⭐⭐⭐⭐⭐ |
| Step5 计划执行 | `execute_plan.py` | ⭐⭐⭐⭐ |
| Step6 论文写作 | `writer.py` | ⭐⭐⭐ |
| Step7-8 论文编译 | `paper/build_submission.ps1` | ⭐⭐⭐⭐ |
| Step9+ 打包交付 | `handoff/package_teamshare.ps1` | ⭐⭐ |
| 数据审计 | `scripts/data_validate.py` | ⭐⭐⭐⭐ |
| 数据清洗 | `scripts/data_clean.py` | ⭐⭐⭐⭐⭐ |
| 成本矩阵 | `scripts/build_generalized_cost.py` | ⭐⭐⭐⭐ |
| 构建图 | `src/data_loader.py` | ⭐⭐⭐⭐⭐ |
| Baseline分析 | `scripts/baseline_analysis.py` | ⭐⭐⭐⭐ |
| 关键设施识别 | `scripts/identify_critical_infrastructure.py` | ⭐⭐⭐⭐⭐ |
| Stakeholder映射 | `scripts/stakeholder_mapping.py` | ⭐⭐⭐⭐⭐ |
| Task1情景 | `scripts/run_task1_keybridge_scenarios.py` | ⭐⭐⭐⭐⭐ |
| Task2优化 | `scripts/run_hybrid_pso_ga_task2.py` | ⭐⭐⭐⭐⭐ |
| Task2消融批跑 | `scripts/run_algorithm_ablation.py` | ???? |
| Task2消融分析 | `scripts/analyze_ablation_results.py` | ???? |
| Task2增量 | `scripts/compute_delta_metrics_task2.py` | ⭐⭐⭐ |
| Task2鲁棒性 | `scripts/run_resilience_task2.py` | ⭐⭐⭐⭐ |
| Task2可视化 | `scripts/viz_task2.py` | ⭐⭐⭐ |
| Task3 MCDA | `scripts/run_task3_mcda.py` | ⭐⭐⭐⭐⭐ |
| Task3敏感性 | `scripts/run_resilience_task3_mcda_sensitivity.py` | ⭐⭐⭐⭐⭐ |
| Task3可视化 | `scripts/viz_task3_resilience.py` | ⭐⭐⭐ |
| 项目审计 | `scripts/project_audit.py` | ⭐⭐⭐⭐ |

---

**文档结束**



