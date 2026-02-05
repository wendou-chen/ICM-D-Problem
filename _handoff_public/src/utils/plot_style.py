import matplotlib.pyplot as plt
import seaborn as sns

def apply_style():
    """
    Applies a consistent plotting style across the project (Q1-Q4).
    Enforces Times New Roman font and a clean academic style.
    """
    # Reset to defaults first to avoid conflicts
    plt.style.use('default')

    # Seaborn (if used)
    try:
        sns.set_style("whitegrid", {
            "font.family": "serif",
            "font.serif": ["Times New Roman"]
        })
        sns.set_context("paper") # Suitable for academic papers
    except ImportError:
        pass # Soft fail if seaborn not installed

    # Global Settings (Applied LAST to override defaults/seaborn)
    plt.rcParams.update({
        "font.family": "serif",
        "font.serif": ["Times New Roman"],
        "mathtext.fontset": "stix",  # Matches Times New Roman for math
        "axes.unicode_minus": False, # Fix minus sign

        # Enforce visible borders (Spines) - UPDATED
        "axes.edgecolor": "#E0E5EB",   # Color: #E0E5EB
        "axes.linewidth": 0.5,         # Width: 0.5pt
        "axes.spines.top": False,      # Hide Top
        "axes.spines.right": False,    # Hide Right
        "axes.spines.bottom": True,    # Show Bottom (X)
        "axes.spines.left": True,      # Show Left (Y)

        # Grid settings
        "axes.grid": False,            # Disable Grid (per user request)
        "grid.color": "#E0E5EB",       # Keep grid light (if enabled manually)
        "grid.linewidth": 0.5,         # Match grid width
        "grid.alpha": 1.0,             # Solid grid lines

        # Ensure ticks are visible
        "xtick.bottom": False,         # Hide bottom ticks
        "ytick.left": False,           # Hide left ticks
        "xtick.color": "black",
        "ytick.color": "black",
    })
