import matplotlib.pyplot as plt
import matplotlib.patches as patches
import os

def draw_overall_framework():
    fig, ax = plt.subplots(figsize=(14, 8))
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 10)
    ax.axis('off')

    # Styles
    box_style = dict(boxstyle='round,pad=0.5', facecolor='#E3F2FD', edgecolor='#1565C0', linewidth=2)
    arrow_style = dict(arrowstyle='->', color='#37474F', linewidth=2)
    text_style = dict(ha='center', va='center', fontsize=10, fontname='DejaVu Sans') # Changed font for compatibility
    title_style = dict(ha='center', va='center', fontsize=12, fontweight='bold', fontname='DejaVu Sans')

    # --- Phase 1: Preparation ---
    # Data & Assumptions
    rect_prep = patches.FancyBboxPatch((1, 7), 3, 2, **box_style)
    ax.add_patch(rect_prep)
    ax.text(2.5, 8.5, "Phase I: Preparation", **title_style)
    ax.text(2.5, 8, "• Problem Analysis\n• Assumption Definition\n• Parameter Initialization\n(M=10^8 tons, T=2050)", **text_style)

    # --- Phase 2: Core Modeling (Q1-Q4) ---
    # Container for Core
    rect_core = patches.Rectangle((5, 1), 5, 8, linewidth=2, edgecolor='#1565C0', facecolor='none', linestyle='--')
    ax.add_patch(rect_core)
    ax.text(7.5, 9.3, "Phase II: Core Modeling & Simulation", **title_style)

    # Q1
    ax.text(7.5, 8, "Q1: Logistics Baseline", **title_style)
    ax.text(7.5, 7.5, "Space Elevator vs. Rocket\nCost-Benefit Analysis", **text_style)

    # Q2
    ax.text(7.5, 6, "Q2: Resilience Analysis", **title_style)
    ax.text(7.5, 5.5, "Disaster Recovery (DES)\nDynamic Redundancy", **text_style)

    # Q3
    ax.text(7.5, 4, "Q3: Resource Supply", **title_style)
    ax.text(7.5, 3.5, "Water Inventory ((s, S) Policy)\nDual-Sourcing Strategy", **text_style)

    # Q4
    ax.text(7.5, 2, "Q4: Environment Impact", **title_style)
    ax.text(7.5, 1.5, "Leaky Bucket Model\nPhased LCA Analysis", **text_style)

    # Arrows inside Core
    ax.annotate('', xy=(7.5, 6.5), xytext=(7.5, 7.2), arrowprops=arrow_style)
    ax.annotate('', xy=(7.5, 4.5), xytext=(7.5, 5.2), arrowprops=arrow_style)
    ax.annotate('', xy=(7.5, 2.5), xytext=(7.5, 3.2), arrowprops=arrow_style)

    # --- Phase 3: Synthesis ---
    # Evaluation & Policy
    rect_eval = patches.FancyBboxPatch((11, 4), 2.5, 2, **box_style)
    ax.add_patch(rect_eval)
    ax.text(12.25, 5.5, "Phase III: Synthesis", **title_style)
    ax.text(12.25, 4.8, "• Sensitivity Analysis\n• Policy Recommendations\n• Memo to IBM Director", **text_style)

    # --- Connections ---
    # Prep to Core
    ax.annotate('', xy=(5, 8), xytext=(4, 8), arrowprops=arrow_style)

    # Core to Eval (Collect all outputs)
    ax.annotate('', xy=(11, 5), xytext=(10, 8), arrowprops=dict(arrowstyle='->', color='#37474F', linewidth=2, connectionstyle="arc3,rad=0.2"))
    ax.annotate('', xy=(11, 5), xytext=(10, 2), arrowprops=dict(arrowstyle='->', color='#37474F', linewidth=2, connectionstyle="arc3,rad=-0.2"))

    os.makedirs('docs/internal', exist_ok=True)
    plt.tight_layout()
    plt.savefig('docs/internal/Overall_Framework.png', dpi=300)
    print("Generated Overall_Framework.png")
    plt.close()

def draw_methodology_framework():
    fig, ax = plt.subplots(figsize=(12, 10))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 10)
    ax.axis('off')

    # Styles
    module_box = dict(boxstyle='round,pad=0.3', facecolor='#BBDEFB', edgecolor='#1976D2')
    method_box = dict(boxstyle='round,pad=0.3', facecolor='#FFF9C4', edgecolor='#FBC02D')
    text_black = dict(color='black', ha='center', va='center', fontname='DejaVu Sans')

    # --- Q1 Module ---
    ax.add_patch(patches.FancyBboxPatch((1, 8), 3, 1, **module_box))
    ax.text(2.5, 8.5, "Q1: Logistics", fontweight='bold', **text_black)
    # Methods
    ax.add_patch(patches.FancyBboxPatch((5, 8), 3, 1, **method_box))
    ax.text(6.5, 8.5, "Linear Programming\nCost Learning Curve", **text_black)

    # --- Q2 Module ---
    ax.add_patch(patches.FancyBboxPatch((1, 6), 3, 1, **module_box))
    ax.text(2.5, 6.5, "Q2: Resilience", fontweight='bold', **text_black)
    # Methods
    ax.add_patch(patches.FancyBboxPatch((5, 6), 3, 1, **method_box))
    ax.text(6.5, 6.5, "Discrete Event Sim (DES)\nMarkov Chain", **text_black)

    # --- Q3 Module ---
    ax.add_patch(patches.FancyBboxPatch((1, 4), 3, 1, **module_box))
    ax.text(2.5, 4.5, "Q3: Resources", fontweight='bold', **text_black)
    # Methods
    ax.add_patch(patches.FancyBboxPatch((5, 4), 3, 1, **method_box))
    ax.text(6.5, 4.5, "Inventory Theory (s,S)\nMonte Carlo Sim", **text_black)

    # --- Q4 Module ---
    ax.add_patch(patches.FancyBboxPatch((1, 2), 3, 1, **module_box))
    ax.text(2.5, 2.5, "Q4: Environment", fontweight='bold', **text_black)
    # Methods
    ax.add_patch(patches.FancyBboxPatch((5, 2), 3, 1, **method_box))
    ax.text(6.5, 2.5, "LCA Assessment\nLeaky Bucket Model", **text_black)

    # --- Outputs ---
    ax.add_patch(patches.FancyBboxPatch((9, 1.5), 2.5, 8, boxstyle='round,pad=0.2', facecolor='#E0E0E0', edgecolor='gray'))
    ax.text(10.25, 9, "Integrated Output", fontweight='bold', **text_black)
    ax.text(10.25, 7, "• Optimal Transport Mix\n• Minimized Cost", **text_black)
    ax.text(10.25, 5, "• Robustness Metric\n• 95% Reliability", **text_black)
    ax.text(10.25, 3, "• Environmental Damage\nIndex (EDI)", **text_black)

    # Arrows
    for y in [8.5, 6.5, 4.5, 2.5]:
        ax.arrow(4.1, y, 0.8, 0, head_width=0.1, head_length=0.1, fc='k', ec='k')
        ax.arrow(8.1, y, 0.8, 0, head_width=0.1, head_length=0.1, fc='k', ec='k')

    plt.tight_layout()
    plt.savefig('docs/internal/Methodology_Framework.png', dpi=300)
    print("Generated Methodology_Framework.png")
    plt.close()

if __name__ == "__main__":
    draw_overall_framework()
    draw_methodology_framework()