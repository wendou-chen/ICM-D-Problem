# 脚本与自动化执行中心 (AGENTS.md)

本目录包含了项目的核心执行脚本与数据流水线，负责从原始数据处理到算法求解及可视化的全过程。

## 1. 概览 (OVERVIEW)
本系统采用模块化的流水线设计，确保实验的可重复性与结果的一致性。
**核心流程**: `ETL (数据预处理)` -> `Task Execution (任务执行/算法优化)` -> `Viz (可视化/报告生成)`。

## 2. 脚本分类 (CATEGORIES)
- **ETL (数据提取与转换)**:
  - `data_clean.py`: 原始交通数据清洗与地理信息标准化。
  - `od_sampling.py`: 起讫点 (OD) 需求的随机抽样与策略管理。
- **Solver (求解器/核心算法)**:
  - `run_task2_hybrid_pipeline.py`: Task 2 混合 PSO-GA-SA 优化流水线。
  - `run_resilience_task2.py`: 针对选定方案的拓扑韧性与性能压力测试。
  - `run_task3_mcda.py`: Task 3 多准则决策分析与方案评估。
- **Viz (可视化与导出)**:
  - `viz_task2.py`: 一键生成论文级图表 (PDF/PNG) 并导出 Kepler 可视化数据。
  - `viz_task3_resilience.py`: 生成韧性曲面与敏感度分析图表。
- **Test (测试与验证)**:
  - `acceptance_test.py`: 自动化交付物完整性与 Schema 验收。
  - `verify_latest_fixes.py`: 关键 Bug 修复后的回归验证。

## 3. 执行约定 (CONVENTIONS)
- **确定性 (Determinism)**: 
  - 所有涉及随机过程的脚本必须支持 `--seed` 参数。
  - 实验结果必须在相同种子下严格可复现。
- **Schema 依赖 (Schema dependency)**:
  - 实验产出必须遵循 `experiment_schema.py` 定义的字段与格式。
  - 强制执行 CSV 头部校验，确保多轮实验数据可合并分析。
- **标准格式**:
  - 结构化指标采用 **CSV** 存储；执行轨迹与详细 Log 采用 **JSONL**。

## 4. 常用命令 (COMMON COMMANDS)

### 运行 Task 2 混合优化方案
```bash
python scripts/run_task2_hybrid_pipeline.py --seed 42 --budget 120 --K 100
```

### 启动可视化渲染引擎
```bash
python scripts/viz_task2.py --outdir outputs/task2/viz --run_id auto --dpi 300
```

### 执行全量脚本链健康检查
```bash
python run_chain_healthcheck.py
```

---
*Last Updated: 2026-01-23*
