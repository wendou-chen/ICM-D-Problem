# AGENTS.md - 2026 MCM/ICM Problem D 核心指南

## 1. OVERVIEW (概览)
本仓库用于 **2026 MCM/ICM Problem D** 数学建模任务的工程模板。项目采用 AI 驱动和手动运行两种运行方式的编排模式，结合启发式优化算法与 LaTeX 自动化流水线，确保建模过程的高度严谨性与可复现性。

**注意**: 这是一个干净的模板工程，已清除 2025 年题目特定的数据和产物。

## 2. STRUCTURE (目录结构)
```
D题归档工程_26/
├── mcm_d_heuristics_v3_3_1/   # 核心算法库（PSO, GA, SA, ALNS, VNS等）
├── scripts/                    # 脚本入口（数据清洗、实验执行）
├── paper/                      # 论文链路（LaTeX编译）
├── data/                       # 数据层（raw + processed，待填充）
│   ├── raw/                    # 原始数据（放入新题数据）
│   └── processed/              # 处理后数据（运行清洗脚本生成）
├── outputs/                    # 实验结果（运行后生成）
├── handoff/                    # 打包交付工具
├── docs/                       # 文档（方法说明/先验知识）
├── plans/                      # 实验计划JSON
├── problems/                   # 问题定义（需新建 OptimizationProblem 子类）
├── src/                        # 数据加载器/导出器
└── 自动化编排核心脚本（根目录）
```

## 3. QUICK START (快速开始)

### Step 1: 环境初始化
```bash
# 创建虚拟环境
python -m venv .venv
.venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

### Step 2: 放入新题数据
将 2026 年题目的原始数据文件放入 `data/raw/` 目录

### Step 3: 核心开发流程
1. **修改 `scripts/data_clean.py`** — 适配新题数据格式
2. **新建 `problems/<新题名>.py`** — 实现 OptimizationProblem 子类
3. **创建 `docs/human_prior_task2.md`** — 编写算法主线和约束先验
4. **编写 Task 脚本** — 在 `scripts/` 下创建 `run_task*.py`
5. **运行实验** — `python execute_plan.py --full`
6. **编译论文** — `powershell paper/build_submission.ps1`

## 4. CORE COMPONENTS (核心组件)

### 算法库 (`mcm_d_heuristics_v3_3_1/`)
| 文件 | 作用 |
|------|------|
| `problem.py` | OptimizationProblem 抽象基类 |
| `hybrid.py` | 混合算法编排器（PSO→GA→SA recipes） |
| `ga.py` | 遗传算法 |
| `pso.py` | 粒子群优化 |
| `sa.py` | 模拟退火 |
| `flow.py` | 网络流问题建模 |
| `network_algo.py` | 图算法（最短路径、连通性） |
| `viz.py` | 可视化工具 |

### 自动化编排（根目录）
| 文件 | 作用 |
|------|------|
| `execute_plan.py` | 实验计划执行引擎 |
| `runner.py` | 统一命令执行器 |
| `agent_exec.py` | AI 工具调用闭环 |
| `schema.py` | Pydantic 数据合同 |
| `writer.py` | 论文章节生成器 |

## 5. CRITICAL CONSTRAINTS (重要约束)
- **严禁幻觉 (No Hallucinations)**: 所有代码变更必须经过验证
- **快速失败 (Fail-Fast)**: 审计逻辑作为质量闸门
- **零泄露 (No Secrets)**: 严禁提交 API Keys、个人凭证
- **确定性 (Deterministic)**: 必须显式设置随机种子（默认为 42）

## 6. NEW PROBLEM CHECKLIST (新题待办清单)

### 必须完成 ⭐⭐⭐⭐⭐
- [ ] 放入新题原始数据到 `data/raw/`
- [ ] 修改 `scripts/data_clean.py` 适配新数据格式
- [ ] 新建 `problems/<问题名>.py` 实现 OptimizationProblem
- [ ] 创建 `docs/human_prior_task2.md` 编写算法先验

### 需要修改 ⭐⭐⭐⭐
- [ ] 修改 `src/data_loader.py` 数据加载逻辑
- [ ] 编写 `scripts/run_task*.py` 各 Task 脚本
- [ ] 更新 `paper/main_submission.tex` 题目信息

### 可选调整 ⭐⭐⭐
- [ ] 修改 `schema.py` 中的 metrics 字段
- [ ] 更新 `tools_impl.py` 工具函数
- [ ] 调整 `writer.py` 章节生成逻辑

## 7. COMMANDS (常用命令)
```powershell
# 数据清洗
python scripts/data_clean.py --raw_dir data/raw --out_dir data/processed

# 执行实验计划
python execute_plan.py --plan plans/plan.json --full

# 运行验收测试
python run_all_acceptance.py

# 论文编译
powershell paper/build_submission.ps1
```

## 8. REFERENCES (参考文档)
- `docs/new_problem_runbook.md` — 新题套壳作战手册（详细步骤）
- `docs/problem_contract.md` — OptimizationProblem 接口合同
- `docs/repo_map.md` — 工程结构地图

---

**Template Version**: 2026-01  
**Based on**: 2025 ICM-D 工程框架  
**Last Updated**: 2026-01-23
