# 2050年月球物流网络：建模内参 (Modeling Brief)

**日期:** 2026-02-02
**作者:** AI Modeling Team (Antigravity)

## 1. 核心变量与参数字典
主要参数定义在 `configs/constants.py` 和 `configs/env_constants.py` 中。

| 符号 | 代码变量名 | 物理含义 | 默认值 | 单位 |
|---|---|---|---|---|
| $M_{total}$ | `TOTAL_MASS_TONS` | 月球基地总物资需求 | 100,000,000 | tons |
| $T_{start}$ | `START_YEAR` | 项目启动年份 | 2050 | year |
| $C(y)$ | `rocket_cost_per_launch` | $y$ 年的火箭发射成本 | 动态衰减 | USD |
| $\alpha$ | `decay_rate` | 技术学习率 (Learning Rate) | 0.05 / 5yrs | - |
| $S_t$ | `S_bc` | 平流层黑碳 (Soot) 库存量 | 动态计算 | tons |
| $\tau$ | `tau_bc_years` | 黑碳在大气中的驻留时间 | 4.0 | years |
| $E_{LCA}$ | `E_LCA_build_ton` | 太空电梯建设产生的碳排放 | ~Eq 4.4 | tons CO2 |
| $I_t$ | `inventory` | 月球基地水资源库存 | 动态计算 | tons |
| $N_{safe}$ | `N_safe_year` | 臭氧层安全发射阈值 | 1000 | launches/yr |

---

## 2. 建模逻辑详解

### Q1: 基础设施选型 (Infrastructure Selection)
**问题阐述**: 在纯火箭运输与太空电梯之间做权衡。
**模型架构**:
*   **火箭模式**: 低固定成本，高边际成本。受学习曲线影响：$C(t) = C_0 (1-\alpha)^{\lfloor t/5 \rfloor}$。
*   **电梯模式**: 极高固定成本 ($E_{LCA}$)，极低边际成本。
**工程实现**: `src/q1/cost_model.py` 实现了基于时间步进的成本累积算法。
**关键结论**: 存在一个盈亏平衡点 (Break-even Point)，但在极大规模运输 ($10^8$ 吨) 需求下，太空电梯在长周期内具有绝对优势。

### Q2: 系统韧性与可靠性 (Reliability & Resilience)
**问题阐述**: 面对天气、机械故障等随机干扰，系统能否稳定运行？
**模型架构**: **离散事件仿真 (Discrete Event Simulation, DES)**
*   **火箭故障**: 服从二项分布 $B(n, p)$。
*   **电梯故障**: 服从泊松过程，修复时间 $MTTR$ 服从指数分布。
**工程实现**: `src/q2/simulator.py`。
**关键结论**: 单一链路极其脆弱。通过引入冗余发射台和动态备份策略，我们将由于故障导致的停运风险控制在 5% 以内。

### Q3: 水资源供应链管理 (Water Resource Management)
**问题阐述**: 水是生命之源，如何确保断供概率趋近于零？
**模型架构**: **双源采购策略 (Dual-Sourcing Strategy)**
*   **基础负荷**: 由太空电梯承担 (低成本，大容量)。
*   **应急激增**: 由火箭承担 (高成本，响应快)。
*   **库存控制**: 采用 $(s, S)$ 策略。当库存 $I_t < s$ (安全库存) 时，触发火箭紧急补给。
**工程实现**: `src/q3/simulation.py` 中的 `simulate_inventory_trajectory` 函数。

### Q4: 环境影响评估 (Environmental Impact Assessment)
**问题阐述**: 长期高频发射对地球大气的影响。
**模型架构**: **漏桶模型 (The Leaky Bucket Model)**
$$S_{t+1} = (1 - \delta) S_t + u_t$$
*   $S_t$: 平流层积累的污染物 (黑碳)。
*   $u_t$: 每日发射产生的排放。
*   $\delta$: 自然沉降率 ($\delta \approx 1/(\tau \times 365)$)。
**指标体系 (EDI)**:
构建环境破坏指数 (Environmental Damage Index)，加权综合了：
1.  温室效应 (CO2)
2.  辐射强迫 (Black Carbon)
3.  臭氧层损耗风险 (Ozone Depletion Risk)
**工程实现**: `src/q4/env_ledger.py`。

---

## 3. 可视化证据 (Visual Evidence)

### 3.1 成本-时间帕累托前沿
![图1: 成本与时间的权衡](outputs/q1/figs/pareto_cost_time.png)
> **解读**: 图中展示了不同方案的非支配解。太空电梯方案虽然初期投入大，但在总耗时和长期总成本上均处于帕累托前沿的优势区域。

### 3.2 供应链韧性曲线
![图2: 可靠性曲线](outputs/q3/step3/fig3_reliability_curve.png)
> **解读**: 随着安全库存 (Buffer) 的增加，缺水风险呈指数级下降。我们建议设定 30 天的安全库存以平衡成本与风险。

### 3.3 环境污染物累积
![图3: 平流层黑碳时序图](outputs/q4_detailed/plots/fig_q4_soot_timeseries.png)
> **解读**: 即使发射频率恒定，由于污染物的长驻留时间 ($\tau=4$年)，平流层内的黑碳存量会呈现"充水效应"并最终达到动态平衡高位。这是火箭方案不可忽视的长期环境代价。
