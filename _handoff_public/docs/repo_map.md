# 工程结构地图 (Repo Map)

**生成时间**: 2026-01-XX  
**仓库路径**: `D:\aMCM_profile\D题归档项目工程\`

---

## 📋 目录结构概览

```
D题归档项目工程/
├── 📦 mcm_d_heuristics_v3_3_1/     # 核心算法库（源码模块）
├── 🎯 scripts/                      # 脚本入口（执行层）
├── 📄 paper/                        # 论文链路（LaTeX编译）
├── 📊 data/                         # 数据层（原始+处理后）
├── 📈 outputs/                      # 计划/日志（实验结果）
├── 📦 handoff/                      # 打包交付（团队协作包）
├── 📝 docs/                         # 文档（方法说明/先验知识）
├── 🗺️ plans/                        # 实验计划JSON
├── 🔧 problems/                     # 问题定义（OptimizationProblem子类）
├── 🏗️ src/                          # 数据加载器/导出器
└── 🔄 自动化编排核心脚本（根目录）
```

---

## 🔧 核心模块分类

### 1. 📦 源码库模块 (`mcm_d_heuristics_v3_3_1/`)

**作用**: 算法核心库，包含所有启发式算法实现和问题接口定义。

#### 核心接口文件
- `problem.py` - **OptimizationProblem 接口定义**（所有问题的抽象基类）
- `hybrid.py` - **混合算法编排器**（PSO→GA→SA recipes、ALNS、VNS等）
- `problem_templates.py` - 问题模板（可复用的问题定义）

#### 算法实现
- `ga.py` - 遗传算法（GAConfig, run_ga）
- `pso.py` - 粒子群优化（PSOConfig, run_pso）
- `sa.py` - 模拟退火（SAConfig, NeighborOp, run_sa）
- `hybrid.py` - 混合算法recipes（recipe_pso_ga_sa, recipe_alns等）

#### 网络/图算法
- `network_algo.py` - 网络算法（最短路径、连通性）
- `flow.py` - 网络流问题建模（路径流、最小成本流）
- `graph_io.py` - 图数据IO
- `schedule.py` - 排程问题（SSGS解码器）

#### 工具与可视化
- `opt_algo.py` - 优化算法工具函数
- `viz.py` - 可视化工具
- `budget.py` - 预算约束处理
- `baselines.py` - 基线算法
- `operators.py` - 邻域算子/破坏修复算子

#### 示例
- `examples/` - 各种算法的演示脚本

**输入**: 问题定义（OptimizationProblem子类）、配置（Config类）  
**输出**: HybridResult（最佳解、成本、收敛历史、日志）  
**产物位置**: 通常被scripts层调用，不直接产生文件

---

### 2. 🎯 脚本入口 (`scripts/`)

**作用**: 执行层脚本，每个脚本对应流程图中的一个节点。

#### 数据清洗与构图 (ETL & Graph Build)
- `data_validate.py` - **数据审计**  
  输入: `data/raw/*`  
  输出: 验证报告  
  产物: 数据质量报告

- `data_clean.py` - **数据清洗**（raw → processed）  
  输入: `data/raw/*`  
  输出: `data/processed/{nodes,edges,bus_stops}_clean.csv`, `cleaning_log.md`  
  产物位置: `data/processed/`

- `build_generalized_cost.py` - **构建广义成本矩阵**  
  输入: `data/processed/edges_clean.csv`  
  输出: 成本矩阵  
  产物位置: `data/processed/`

- `src/data_loader.py` - **构建多层网络图 & 导出绘图资产**  
  输入: `data/processed/{nodes,edges,bus_stops}_clean.csv`  
  输出: `graph.pkl`, `graph_nodes.csv`, `graph_edges.csv`, `graph_edges_kepler.csv`, `boundary.geojson`, `base_map.csv`  
  产物位置: `data/processed/`

#### Baseline + 关键设施 + Stakeholder
- `baseline_analysis.py` - **Baseline分析**（OD抽样连通性/代价 + 瓶颈识别）  
  输入: `data/processed/graph.pkl`  
  输出: `outputs/baseline/baseline_metrics.csv`, `bottlenecks_top10_nodes.csv`, `baseline_report.md`  
  产物位置: `outputs/baseline/`

- `identify_critical_infrastructure.py` - **关键设施识别**（Key Bridge & US-40）  
  输入: `data/processed/edges_clean.csv`, `data/processed/boundary.geojson`  
  输出: `outputs/task1/{key_bridge_edges,us40_edges}.csv`, `critical_locations_map.png`, `critical_infra_report.md`  
  产物位置: `outputs/task1/`

- `stakeholder_mapping.py` - **Stakeholder映射**（OD→stakeholder）  
  输入: `data/processed/{graph_nodes.csv,bus_stops_clean.csv}`, `data/processed/boundary.geojson`  
  输出: `outputs/stakeholders/{od_stakeholder_labels,stakeholder_summary}.csv`, `docs/stakeholder_mapping.md`  
  产物位置: `outputs/stakeholders/`, `docs/`

#### Task 1 - Key Bridge 情景
- `run_task1_keybridge_scenarios.py` - **Key Bridge情景评估**  
  输入: `data/processed/graph.pkl`, `outputs/task1/key_bridge_edges.csv`, `outputs/stakeholders/od_stakeholder_labels.csv`  
  输出: `outputs/task1/{metrics_by_stakeholder,metrics_overall,delta_metrics_by_stakeholder}.csv`  
  产物位置: `outputs/task1/`

#### Task 2 - 公交线路优化
- `run_hybrid_pso_ga_task2.py` - **Hybrid PSO→GA优化**（主入口）  
  输入: `data/processed/graph.pkl`, `data/processed/candidates_task2.json`, `outputs/stakeholders/od_stakeholder_labels.csv`  
  输出: `outputs/task2/{metrics.csv,best_solution.json,convergence_history.csv,metrics_by_stakeholder.csv,hybrid_log.json}`  
  产物位置: `outputs/task2/`

- `run_task2_hybrid_pipeline.py` - **Hybrid PSO→GA→SA Pipeline**（可选，更完整）  
  输入: 同上  
  输出: 同上 + SA阶段结果  
  产物位置: `outputs/task2/`

- `experiment_schema.py` - **实验Schema**（指标定义 & fail-fast）  
  作用: 定义CSV Schema、生成run_id、验证输出格式

- `compute_delta_metrics_task2.py` - **Task2相对baseline的Δ计算**  
  输入: `outputs/task1/metrics_by_stakeholder.csv`, `outputs/task2/metrics_by_stakeholder.csv`  
  输出: `outputs/task2/delta_metrics_by_stakeholder.csv`  
  产物位置: `outputs/task2/`

- `run_resilience_task2.py` - **Task2鲁棒性测试**（随机/定向移除）  
  输入: `outputs/task2/best_solution.json`, `data/processed/graph.pkl`  
  输出: `outputs/task2/{resilience_table.csv,resilience_curve.csv}`  
  产物位置: `outputs/task2/`

- `viz_task2.py` - **Task2可视化**（一键出图+Kepler+打包）  
  输入: `outputs/task2/*.csv`, `outputs/task2/best_solution.json`  
  输出: `outputs/task2/viz/figures/*.png`, `solution_flows.csv`, `plot_pack_*.zip`  
  产物位置: `outputs/task2/viz/`

#### Task 3 - MCDA推荐
- `run_task3_mcda.py` - **MCDA项目对比**  
  输入: `outputs/task2/best_solution.json`, `outputs/task1/us40_edges.csv`  
  输出: `outputs/task3/{alternatives.csv,project_metrics_by_stakeholder.csv,mcda_scores.csv}`  
  产物位置: `outputs/task3/`

- `run_resilience_task3_mcda_sensitivity.py` - **Task3决策鲁棒性**（α/β/US40参数扰动）  
  输入: `outputs/task3/mcda_scores.csv`  
  输出: `outputs/task3/resilience/{experiment_matrix.csv,robustness_table.csv,robustness_curve.csv}`  
  产物位置: `outputs/task3/resilience/`

- `viz_task3_resilience.py` - **Task3可视化**  
  输入: `outputs/task3/resilience/*.csv`  
  输出: `outputs/task3/resilience/viz/figures/*.png`, `plot_pack_task3_resilience.zip`  
  产物位置: `outputs/task3/resilience/viz/`

#### 复现与审计
- `reproduce_task2.ps1` - **一键复现Task2全链路**（ETL→Task2→Resilience→Viz→Audit）  
  输入: 原始数据  
  输出: Task2完整产物  
  产物位置: `outputs/task2/`

- `project_audit.py` - **项目审计**（Stage A–G PASS）  
  输入: 所有输出文件  
  输出: 审计报告  
  产物位置: `outputs/audit/`

- `acceptance_test.py` - **验收测试**  
  作用: 验证各阶段产物是否符合Schema

#### 辅助脚本
- `od_sampling.py` - OD对抽样工具  
- `generate_data_dictionary.py` - 生成数据字典  
- `make_tables.py` - 生成表格  
- 其他调试/验证脚本

---

### 3. 🔄 自动化编排核心（根目录）

**作用**: 流程图"阶段0"的自动化编排核心，从计划生成到论文交付。

#### Step0-3: 基础设施
- `schema.py` - **统一I/O Schema**（Artifact / RunResult / StepConfig / ExperimentPlan）  
  作用: 定义数据结构，确保写作/审计友好

- `runner.py` - **统一执行命令**（run_cmd: 执行+收集artifacts+tail日志）  
  作用: Windows编码errors=replace防崩，统一命令执行接口

- `tools_impl.py` - **工具实现**（run_etl/build_graph/run_baseline/run_task2/sensitivity/attack_nodes）  
  输入: 工具参数（通过tools.json定义）  
  输出: RunResult  
  产物位置: 调用scripts层脚本，产物在各outputs/目录

- `tool_schemas.py` + `tools.json` - **DeepSeek-Chat tool-calls schema**  
  作用: 定义LLM可调用的工具列表和参数

- `agent_exec.py` - **DeepSeek-Chat tool-loop执行器**（自检ping）  
  作用: 执行LLM工具调用循环

#### Step4-5: 计划生成与执行
- `plan_speciale.py` - **生成ExperimentPlan JSON**  
  输入: `docs/human_prior_task2.md`（可选--prior）  
  输出: `plans/plan.json`  
  产物位置: `plans/`  
  支持: 在线（OpenRouter API）和离线（stub计划）

- `execute_plan.py` - **按plan顺序执行runs**  
  输入: `plans/plan.json`  
  输出: `outputs/experiment_log*.jsonl`  
  产物位置: `outputs/`  
  参数: `--dry-run` / `--full` / `--full-first-k`

#### Step6: 论文写作
- `writer.py` - **plan+log → paper/sections/*.tex**  
  输入: `plans/plan.json`, `outputs/experiment_log*.jsonl`  
  输出: `paper/sections/{methods,results,robustness,limitations,ai_tools_report}.tex`  
  产物位置: `paper/sections/`  
  说明: offline必可用；可选LLM润色（不改数字/路径）

#### Step7-8: 论文编译
- `paper/build.ps1` / `paper/build_submission.ps1` - **LaTeX编译脚本**  
  输入: `paper/main.tex` / `paper/main_submission.tex`  
  输出: `paper/main.pdf` / `paper/main_submission.pdf`, `paper/ai_appendix.pdf`  
  产物位置: `paper/`

#### Step9+: 打包交付
- `handoff/pack_task_artifacts.py` - **按工具/任务切片打包**  
  输入: 各outputs/目录  
  输出: `handoff/{task1,task2,task3}_artifacts.zip`  
  产物位置: `handoff/`

- `handoff/package_teamshare.ps1` - **一键总包**  
  输入: PDF + 中文总览 + plan/log/schema + task zips  
  输出: `handoff/all_teamshare.zip`  
  产物位置: `handoff/`

---

### 4. 📄 论文链路 (`paper/`)

**作用**: LaTeX源文件与编译产物。

#### 主文件
- `main.tex` - 完整版论文主文件
- `main_submission.tex` - 提交版论文（≤25页）
- `main_submission_cn.tex` - 中文总览版
- `ai_appendix.tex` - AI工具使用报告

#### 章节文件
- `sections/` - 各章节LaTeX源文件（methods, results, robustness等）

#### 表格
- `tables/` - LaTeX表格源文件

#### 参考文献
- `references.bib` - BibTeX参考文献

#### 编译脚本
- `build.ps1` - 编译完整版
- `build_submission.ps1` - 编译提交版

**输入**: `sections/*.tex`（由writer.py生成）  
**输出**: `*.pdf`  
**产物位置**: `paper/`

---

### 5. 📊 数据层 (`data/`)

**作用**: 原始数据与处理后数据。

#### 原始数据
- `raw/` - 原始CSV文件（Bus_Stops.csv, edges_all.csv, nodes_all.csv等）

#### 处理后数据
- `processed/` - 清洗后的CSV + 图文件
  - `{nodes,edges,bus_stops}_clean.csv` - 清洗后的节点/边/站点数据
  - `graph.pkl` - **核心图对象**（算法唯一输入）
  - `graph_{nodes,edges,edges_kepler}.csv` - 图导出CSV
  - `boundary.geojson` - 边界GeoJSON
  - `base_map.csv` - 底图数据
  - `candidates_task2.json` - Task2候选线路集合
  - `cleaning_log.md` - 清洗日志

**输入**: 原始CSV  
**输出**: 处理后CSV + graph.pkl  
**产物位置**: `data/processed/`

---

### 6. 📈 输出层 (`outputs/`)

**作用**: 实验结果、日志、可视化产物。

#### 目录结构
- `baseline/` - Baseline分析结果
- `task1/` - Task1情景评估结果
- `task2/` - Task2优化结果 + 鲁棒性 + 可视化
- `task3/` - Task3 MCDA结果 + 敏感性分析 + 可视化
- `stakeholders/` - Stakeholder映射结果
- `experiment_log*.jsonl` - 实验日志（RunResult序列）
- `audit/` - 审计报告
- `memo/` - 政策备忘录（待写）

**输入**: 各scripts输出  
**输出**: CSV/JSON/PNG/PDF等  
**产物位置**: 各子目录

---

### 7. 📦 打包交付 (`handoff/`)

**作用**: 团队协作包（给写作手/绘图手）。

#### 文件
- `task{1,2,3}_artifacts.zip` - 各任务切片包
- `all_teamshare.zip` - 一键总包（PDF+中文+数据+图）
- `README_HANDOFF.md` - 交付说明

**输入**: outputs/ + paper/  
**输出**: ZIP文件  
**产物位置: `handoff/`

---

### 8. 📝 文档 (`docs/`)

**作用**: 方法说明、先验知识、问题契约。

#### 文件
- `human_prior_task2.md` - **人类先验**（算法主线，如PSO→GA）
- `stakeholder_mapping.md` - Stakeholder方法说明
- `problem_contract.md` - 问题契约定义

**作用**: 供plan_speciale.py读取（--prior注入硬约束）

---

### 9. 🗺️ 计划层 (`plans/`)

**作用**: 实验计划JSON。

#### 文件
- `plan.json` - 当前实验计划
- `plan_with_prior.json` - 带先验约束的计划
- `plan_templates.json` - 计划模板

**输入**: plan_speciale.py生成  
**输出**: execute_plan.py消费  
**产物位置: `plans/`

---

### 10. 🔧 问题定义 (`problems/`)

**作用**: 自定义OptimizationProblem子类。

#### 文件
- `bus_route_design_problem.py` - **BusRouteDesignProblem**（Task2问题定义）

**输入**: graph.pkl, candidates, OD对  
**输出**: 被scripts层调用  
**作用**: 实现OptimizationProblem接口，定义解码/评估/约束

---

### 11. 🏗️ 数据加载器 (`src/`)

**作用**: 数据加载与导出工具。

#### 文件
- `data_loader.py` - 数据加载器（构建图）
- `exporters.py` - 数据导出器
- `utils/` - 工具函数

**输入**: CSV文件  
**输出**: graph.pkl等  
**产物位置: `data/processed/`

---

## 🔑 关键入口脚本清单

### 数据准备阶段
1. `scripts/data_validate.py` - 数据审计
2. `scripts/data_clean.py` - 数据清洗
3. `src/data_loader.py` - 构建图

### Baseline + 关键设施
4. `scripts/baseline_analysis.py` - Baseline分析
5. `scripts/identify_critical_infrastructure.py` - 关键设施识别
6. `scripts/stakeholder_mapping.py` - Stakeholder映射

### Task执行
7. `scripts/run_task1_keybridge_scenarios.py` - Task1
8. `scripts/run_hybrid_pso_ga_task2.py` - Task2优化
9. `scripts/compute_delta_metrics_task2.py` - Task2增量计算
10. `scripts/run_resilience_task2.py` - Task2鲁棒性
11. `scripts/viz_task2.py` - Task2可视化
12. `scripts/run_task3_mcda.py` - Task3 MCDA
13. `scripts/run_resilience_task3_mcda_sensitivity.py` - Task3敏感性
14. `scripts/viz_task3_resilience.py` - Task3可视化

### 自动化编排
15. `plan_speciale.py` - 生成计划
16. `execute_plan.py` - 执行计划
17. `writer.py` - 生成论文章节
18. `paper/build_submission.ps1` - 编译论文
19. `handoff/package_teamshare.ps1` - 打包交付

### 一键复现
20. `scripts/reproduce_task2.ps1` - 一键复现Task2

---

## 📊 数据流图

```
原始数据 (data/raw/)
  ↓ [data_clean.py]
清洗数据 (data/processed/*_clean.csv)
  ↓ [data_loader.py]
图对象 (data/processed/graph.pkl)
  ↓ [baseline_analysis.py]
Baseline结果 (outputs/baseline/)
  ↓ [run_hybrid_pso_ga_task2.py]
Task2结果 (outputs/task2/)
  ↓ [run_resilience_task2.py]
鲁棒性结果 (outputs/task2/)
  ↓ [viz_task2.py]
可视化产物 (outputs/task2/viz/)
  ↓ [pack_task_artifacts.py]
交付包 (handoff/)
```

---

## 🎯 模块依赖关系

1. **scripts层** 依赖 **mcm_d_heuristics_v3_3_1库**（算法实现）
2. **scripts层** 依赖 **problems/**（问题定义）
3. **execute_plan.py** 调用 **tools_impl.py**，后者调用 **scripts层**
4. **writer.py** 读取 **outputs/** 和 **plans/**，生成 **paper/sections/**
5. **handoff脚本** 打包 **outputs/** 和 **paper/**

---

**文档结束**
