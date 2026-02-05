import matplotlib.pyplot as plt
import matplotlib.patches as patches
import os
from matplotlib import rcParams

# 设置中文字体 (需要确保系统中安装了支持中文的字体，如 SimHei, Microsoft YaHei 等)
# 如果运行环境没有中文字体，可能会显示乱码。这里尝试设置常见中文字体。
rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS']
rcParams['axes.unicode_minus'] = False 

def draw_overall_framework_cn():
    fig, ax = plt.subplots(figsize=(14, 8))
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 10)
    ax.axis('off')

    # Styles
    box_style = dict(boxstyle='round,pad=0.5', facecolor='#E3F2FD', edgecolor='#1565C0', linewidth=2)
    arrow_style = dict(arrowstyle='->', color='#37474F', linewidth=2)
    text_style = dict(ha='center', va='center', fontsize=10) 
    title_style = dict(ha='center', va='center', fontsize=12, fontweight='bold')

    # --- 第一阶段: 准备工作 ---
    # Data & Assumptions
    rect_prep = patches.FancyBboxPatch((1, 7), 3, 2, **box_style)
    ax.add_patch(rect_prep)
    ax.text(2.5, 8.5, "阶段 I: 准备工作", **title_style)
    ax.text(2.5, 8, "• 问题分析\n• 假设定义\n• 参数初始化\n(M=10^8 吨, T=2050)", **text_style)

    # --- 第二阶段: 核心建模 (Q1-Q4) ---
    # Container for Core
    rect_core = patches.Rectangle((5, 1), 5, 8, linewidth=2, edgecolor='#1565C0', facecolor='none', linestyle='--')
    ax.add_patch(rect_core)
    ax.text(7.5, 9.3, "阶段 II: 核心建模与仿真", **title_style)

    # Q1
    ax.text(7.5, 8, "Q1: 物流基线", **title_style)
    ax.text(7.5, 7.5, "太空电梯 vs. 火箭\n成本效益分析", **text_style)

    # Q2
    ax.text(7.5, 6, "Q2: 韧性分析", **title_style)
    ax.text(7.5, 5.5, "灾难恢复 (离散事件仿真)\n动态冗余策略", **text_style)

    # Q3
    ax.text(7.5, 4, "Q3: 资源供给", **title_style)
    ax.text(7.5, 3.5, "水资源库存 ((s, S) 策略)\n双源采购策略", **text_style)

    # Q4
    ax.text(7.5, 2, "Q4: 环境影响", **title_style)
    ax.text(7.5, 1.5, "漏桶模型\n分阶段全生命周期分析 (LCA)", **text_style)

    # Arrows inside Core
    ax.annotate('', xy=(7.5, 6.5), xytext=(7.5, 7.2), arrowprops=arrow_style)
    ax.annotate('', xy=(7.5, 4.5), xytext=(7.5, 5.2), arrowprops=arrow_style)
    ax.annotate('', xy=(7.5, 2.5), xytext=(7.5, 3.2), arrowprops=arrow_style)

    # --- 第三阶段: 综合评估 ---
    # Evaluation & Policy
    rect_eval = patches.FancyBboxPatch((11, 4), 2.5, 2, **box_style)
    ax.add_patch(rect_eval)
    ax.text(12.25, 5.5, "阶段 III: 综合评估", **title_style)
    ax.text(12.25, 4.8, "• 敏感性分析\n• 政策建议\n• 致 IBM 主管备忘录", **text_style)

    # --- Connections ---
    # Prep to Core
    ax.annotate('', xy=(5, 8), xytext=(4, 8), arrowprops=arrow_style)

    # Core to Eval (Collect all outputs)
    ax.annotate('', xy=(11, 5), xytext=(10, 8), arrowprops=dict(arrowstyle='->', color='#37474F', linewidth=2, connectionstyle="arc3,rad=0.2"))
    ax.annotate('', xy=(11, 5), xytext=(10, 2), arrowprops=dict(arrowstyle='->', color='#37474F', linewidth=2, connectionstyle="arc3,rad=-0.2"))

    os.makedirs('docs/internal', exist_ok=True)
    plt.tight_layout()
    plt.savefig('docs/internal/Overall_Framework_CN.png', dpi=300)
    print("Generated Overall_Framework_CN.png")
    plt.close()

def draw_methodology_framework_cn():
    fig, ax = plt.subplots(figsize=(12, 10))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 10)
    ax.axis('off')

    # Styles
    module_box = dict(boxstyle='round,pad=0.3', facecolor='#BBDEFB', edgecolor='#1976D2')
    method_box = dict(boxstyle='round,pad=0.3', facecolor='#FFF9C4', edgecolor='#FBC02D')
    text_black = dict(color='black', ha='center', va='center')
    title_font = dict(fontweight='bold')

    # --- Q1 Module ---
    ax.add_patch(patches.FancyBboxPatch((1, 8), 3, 1, **module_box))
    ax.text(2.5, 8.5, "Q1: 物流规划", **text_black, **title_font)
    # Methods
    ax.add_patch(patches.FancyBboxPatch((5, 8), 3, 1, **method_box))
    ax.text(6.5, 8.5, "线性规划\n成本学习曲线", **text_black)

    # --- Q2 Module ---
    ax.add_patch(patches.FancyBboxPatch((1, 6), 3, 1, **module_box))
    ax.text(2.5, 6.5, "Q2: 韧性评估", **text_black, **title_font)
    # Methods
    ax.add_patch(patches.FancyBboxPatch((5, 6), 3, 1, **method_box))
    ax.text(6.5, 6.5, "离散事件仿真 (DES)\n马尔可夫链", **text_black)

    # --- Q3 Module ---
    ax.add_patch(patches.FancyBboxPatch((1, 4), 3, 1, **module_box))
    ax.text(2.5, 4.5, "Q3: 资源管理", **text_black, **title_font)
    # Methods
    ax.add_patch(patches.FancyBboxPatch((5, 4), 3, 1, **method_box))
    ax.text(6.5, 4.5, "库存理论 ((s,S) 策略)\n蒙特卡洛模拟", **text_black)

    # --- Q4 Module ---
    ax.add_patch(patches.FancyBboxPatch((1, 2), 3, 1, **module_box))
    ax.text(2.5, 2.5, "Q4: 环境影响", **text_black, **title_font)
    # Methods
    ax.add_patch(patches.FancyBboxPatch((5, 2), 3, 1, **method_box))
    ax.text(6.5, 2.5, "生命周期评价 (LCA)\n漏桶模型", **text_black)

    # --- Outputs ---
    ax.add_patch(patches.FancyBboxPatch((9, 1.5), 2.5, 8, boxstyle='round,pad=0.2', facecolor='#E0E0E0', edgecolor='gray'))
    ax.text(10.25, 9, "综合输出", **text_black, **title_font)
    ax.text(10.25, 7, "• 最优运输组合\n• 成本最小化", **text_black)
    ax.text(10.25, 5, "• 鲁棒性指标\n• 95% 可靠度", **text_black)
    ax.text(10.25, 3, "• 环境破坏指数\n(EDI)", **text_black)

    # Arrows
    for y in [8.5, 6.5, 4.5, 2.5]:
        ax.arrow(4.1, y, 0.8, 0, head_width=0.1, head_length=0.1, fc='k', ec='k')
        ax.arrow(8.1, y, 0.8, 0, head_width=0.1, head_length=0.1, fc='k', ec='k')

    plt.tight_layout()
    plt.savefig('docs/internal/Methodology_Framework_CN.png', dpi=300)
    print("Generated Methodology_Framework_CN.png")
    plt.close()

if __name__ == "__main__":
    draw_overall_framework_cn()
    draw_methodology_framework_cn()
