import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import networkx as nx
import numpy as np
import seaborn as sns
from typing import List, Dict, Tuple, Optional, Sequence, Any

# 设置 O 奖级绘图风格
plt.style.use("seaborn-v0_8-whitegrid")
plt.rcParams["font.family"] = "sans-serif"  # 避免中文乱码需配合字体设置，这里默认英文环境
plt.rcParams["axes.unicode_minus"] = False


class Visualizer:
    """
    ICM D 题通用可视化工具箱。
    集成：收敛曲线、网络拓扑、甘特图、路径轨迹。
    """

    @staticmethod
    def plot_convergence(
        histories: Dict[str, List[float]],
        title: str = "Algorithm Convergence Comparison",
        ylabel: str = "Cost / Fitness",
        save_path: Optional[str] = None,
    ):
        """
        [1. 收敛曲线] 绘制算法迭代过程。支持同时对比多个算法。
        :param histories: 字典 {'PSO': [100, 90, ...], 'GA': [110, 85, ...]}
        """
        plt.figure(figsize=(10, 6))

        colors = sns.color_palette("husl", len(histories))
        for idx, (algo_name, history) in enumerate(histories.items()):
            plt.plot(history, label=algo_name, color=colors[idx], linewidth=2, alpha=0.8)
            min_val = min(history)
            min_iter = history.index(min_val)
            plt.scatter(min_iter, min_val, color=colors[idx], s=50, zorder=5)

        plt.title(title, fontsize=14, fontweight="bold")
        plt.xlabel("Iteration", fontsize=12)
        plt.ylabel(ylabel, fontsize=12)
        plt.legend(frameon=True)
        plt.grid(True, linestyle="--", alpha=0.6)

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches="tight")
        plt.show()

    @staticmethod
    def plot_network_analysis(
        G: nx.Graph,
        pos: Dict = None,
        node_values: Dict[int, float] = None,
        highlight_edges: List[Tuple[int, int]] = None,
        title: str = "Network Topology Analysis",
        cmap: str = "coolwarm",
    ):
        """
        [2 & 3. 拓扑热力图] 绘制网络，根据中心性改变节点颜色/大小，高亮关键路径。
        :param G: NetworkX 图对象
        :param pos: 节点位置 (如 {0: (x,y)}), 若无则自动生成
        :param node_values: 节点权重字典 (如 Centrality), 决定颜色和大小
        :param highlight_edges: 需要高亮的边列表 (如 MST 或 最短路)
        """
        plt.figure(figsize=(12, 8))
        if pos is None:
            pos = nx.spring_layout(G, seed=42)

        nx.draw_networkx_edges(G, pos, alpha=0.2, edge_color="gray")

        if highlight_edges:
            nx.draw_networkx_edges(G, pos, edgelist=highlight_edges, width=2.5, edge_color="orange", alpha=0.9)

        if node_values:
            vals = np.array([node_values.get(n, 0) for n in G.nodes()])
            node_sizes = 300 + (vals - vals.min()) / (vals.max() - vals.min() + 1e-9) * 1000

            nodes = nx.draw_networkx_nodes(
                G, pos, node_size=node_sizes, node_color=vals, cmap=cmap, alpha=0.9, edgecolors="white"
            )
            plt.colorbar(nodes, label="Node Centrality / Importance")
        else:
            nx.draw_networkx_nodes(G, pos, node_size=500, node_color="#3498db")

        nx.draw_networkx_labels(G, pos, font_size=10, font_color="black", font_weight="bold")

        plt.title(title, fontsize=15)
        plt.axis("off")
        plt.show()

    @staticmethod
    def plot_gantt_chart(
        tasks: List[Dict],
        title: str = "Job Shop Schedule",
        save_path: Optional[str] = None,
    ):
        """
        [4. 甘特图] 针对调度问题。
        :param tasks: 任务列表，格式: [{'Machine': 'M1', 'Start': 0, 'Duration': 5, 'Job': 'J1'}, ...]
        """
        plt.figure(figsize=(12, 6))

        machines = sorted(list(set(t["Machine"] for t in tasks)))
        job_ids = sorted(list(set(t["Job"] for t in tasks)))

        colors = plt.cm.tab10(np.linspace(0, 1, len(job_ids)))
        color_map = {job: color for job, color in zip(job_ids, colors)}

        yticks = []
        yticklabels = []

        for i, machine in enumerate(machines):
            yticks.append(i * 10)
            yticklabels.append(machine)

            machine_tasks = [t for t in tasks if t["Machine"] == machine]
            for t in machine_tasks:
                plt.barh(
                    i * 10,
                    t["Duration"],
                    left=t["Start"],
                    height=6,
                    align="center",
                    color=color_map[t["Job"]],
                    edgecolor="black",
                    alpha=0.8,
                )
                plt.text(
                    t["Start"] + t["Duration"] / 2,
                    i * 10,
                    t["Job"],
                    ha="center",
                    va="center",
                    color="white",
                    fontweight="bold",
                    fontsize=9,
                )

        plt.yticks(yticks, yticklabels)
        plt.xlabel("Time Units")
        plt.title(title, fontsize=14)

        patches = [mpatches.Patch(color=color_map[j], label=j) for j in job_ids]
        plt.legend(handles=patches, bbox_to_anchor=(1.05, 1), loc="upper left")

        plt.tight_layout()
        if save_path:
            plt.savefig(save_path)
        plt.show()

    @staticmethod
    def plot_route_trajectory(
        coords: np.ndarray,
        route_order: List[int],
        title: str = "Optimized Route Trajectory",
    ):
        """
        [6. 路径轨迹图] 针对 TSP / 无人机路径。
        :param coords: 坐标数组 [[x1, y1], [x2, y2], ...]
        :param route_order: 访问顺序索引 [0, 5, 2, 0]
        """
        plt.figure(figsize=(8, 8))

        x = coords[:, 0]
        y = coords[:, 1]

        plt.scatter(x, y, c="red", s=100, zorder=2, label="Locations")
        for i, (xi, yi) in enumerate(coords):
            plt.text(xi, yi + 0.5, str(i), fontsize=12, ha="center")

        path_x = x[route_order]
        path_y = y[route_order]

        plt.plot(path_x, path_y, c="blue", linestyle="--", alpha=0.5, zorder=1)

        u = np.diff(path_x)
        v = np.diff(path_y)
        pos_x = path_x[:-1] + u / 2
        pos_y = path_y[:-1] + v / 2
        norm = np.sqrt(u**2 + v**2)

        plt.quiver(
            pos_x,
            pos_y,
            u / norm,
            v / norm,
            angles="xy",
            scale_units="xy",
            scale=0.05,
            color="blue",
            zorder=3,
            width=0.005,
        )

        plt.scatter(path_x[0], path_y[0], c="green", s=200, label="Start", marker="*")
        plt.scatter(path_x[-1], path_y[-1], c="black", s=150, label="End", marker="X")

        plt.title(title, fontsize=14)
        plt.legend()
        plt.grid(True)
        plt.show()


def plot_convergence(history: Sequence[float], title: str = "Convergence Curve") -> None:
    if isinstance(history, dict):
        Visualizer.plot_convergence(history, title=title)
        return
    Visualizer.plot_convergence({"Series": list(history)}, title=title)


def draw_network(
    edges: Sequence[Tuple[Any, Any, float]],
    pos: Optional[Dict[Any, Tuple[float, float]]] = None,
    highlight_edges: Optional[Sequence[Tuple[Any, Any]]] = None,
    title: str = "Network",
) -> None:
    G = nx.Graph()
    for u, v, w in edges:
        G.add_edge(u, v, weight=float(w))
    Visualizer.plot_network_analysis(G, pos=pos, highlight_edges=list(highlight_edges) if highlight_edges else None, title=title)


def plot_gantt(
    tasks: Sequence[Tuple[str, float, float, str]],
    title: str = "Gantt Chart",
) -> None:
    tasks_data = [
        {"Machine": res, "Start": float(start), "Duration": float(dur), "Job": str(name)}
        for name, start, dur, res in tasks
    ]
    Visualizer.plot_gantt_chart(tasks_data, title=title)


def _extract_points_2d(solutions: Any) -> np.ndarray:
    """Accept iterable of (f1,f2) or archive-like object; return ndarray (n,2)."""
    pts = None
    if solutions is None:
        pts = []
    elif isinstance(solutions, (list, tuple, np.ndarray)):
        pts = solutions
    else:
        for attr in ("solutions", "front", "points"):
            if hasattr(solutions, attr):
                pts = getattr(solutions, attr)
                break
        if pts is None:
            pts = solutions

    arr = np.asarray(list(pts), dtype=float)
    if arr.size == 0:
        return np.empty((0, 2), dtype=float)
    arr = np.atleast_2d(arr)
    if arr.shape[1] < 2:
        raise ValueError("plot_pareto_front expects points like (obj1, obj2).")
    return arr[:, :2]


def pareto_filter_2d(points: np.ndarray, sense: Tuple[int, int] = (1, 1)) -> np.ndarray:
    """Return non-dominated subset (2D). sense=(1,1) means minimize both; use -1 for maximize."""
    if points.size == 0:
        return points

    # Convert to minimization form
    pts = points.copy()
    pts[:, 0] *= sense[0]
    pts[:, 1] *= sense[1]

    n = pts.shape[0]
    keep = np.ones(n, dtype=bool)
    for i in range(n):
        if not keep[i]:
            continue
        dominates = np.all(pts <= pts[i], axis=1) & np.any(pts < pts[i], axis=1)
        dominates[i] = False
        if np.any(dominates):
            keep[i] = False
    return points[keep]


def plot_pareto_front(
    solutions: Any,
    title: str = "Pareto Front",
    xlabel: str = "Objective 1",
    ylabel: str = "Objective 2",
    save_path: Optional[str] = None,
    connect: bool = True,
    filter_nondominated: bool = True,
    sense: Tuple[int, int] = (1, 1),  # (1,1)=min/min; (-1,1)=max/min ...
) -> None:
    """Plot a 2D Pareto front (scatter + optional envelope), optionally filtering non-dominated points."""
    pts = _extract_points_2d(solutions)
    if pts.size == 0:
        print("Warning: empty Pareto set; nothing to plot.")
        return

    mask = np.isfinite(pts[:, 0]) & np.isfinite(pts[:, 1])
    pts = pts[mask]
    if pts.size == 0:
        print("Warning: non-finite points; nothing to plot.")
        return

    if filter_nondominated and pts.shape[0] >= 2:
        pts = pareto_filter_2d(pts, sense=sense)

    xs, ys = pts[:, 0], pts[:, 1]

    plt.figure(figsize=(8, 6))
    plt.scatter(xs, ys, s=45, alpha=0.85, label="Non-dominated" if filter_nondominated else "Points")

    if connect and xs.size >= 2:
        order = np.argsort(xs)
        plt.plot(xs[order], ys[order], linewidth=1.5, alpha=0.7)

    plt.title(title, fontsize=14, fontweight="bold")
    plt.xlabel(xlabel, fontsize=12)
    plt.ylabel(ylabel, fontsize=12)
    plt.grid(True, linestyle="--", alpha=0.6)
    plt.legend(frameon=True)

    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches="tight")
    plt.show()


def draw_network_flow(
    G: nx.Graph,
    flow: Dict[Tuple[Any, Any], float],
    capacity: Optional[Dict[Tuple[Any, Any], float]] = None,
    pos: Optional[Dict[Any, Tuple[float, float]]] = None,
    title: str = "Network Flow / Utilization",
    cmap: str = "Reds",
    min_width: float = 0.6,
    max_width: float = 6.0,
    node_size: int = 520,
    show_colorbar: bool = True,
    save_path: Optional[str] = None,
) -> None:
    """Draw network with edge color by utilization (flow/capacity) and width by flow.
    Supports directed graphs (DiGraph) with arrows.
    """
    plt.figure(figsize=(12, 8))
    if pos is None:
        pos = nx.spring_layout(G, seed=42)

    edges = list(G.edges())
    flows = []
    caps = []
    for u, v in edges:
        if G.is_directed():
            f = float(flow.get((u, v), 0.0))
        else:
            f = float(flow.get((u, v), flow.get((v, u), 0.0)))
        flows.append(f)

        cap = None
        if capacity is not None:
            cap = capacity.get((u, v), capacity.get((v, u), None)) if not G.is_directed() else capacity.get((u, v), None)
        if cap is None:
            data = G.get_edge_data(u, v, default={}) or {}
            cap = data.get("capacity", data.get("cap", None))
        caps.append(float(cap) if cap is not None else np.nan)

    flows_arr = np.asarray(flows, dtype=float)
    caps_arr = np.asarray(caps, dtype=float)

    # Width mapping
    max_flow = float(np.nanmax(flows_arr)) if flows_arr.size else 0.0
    if max_flow <= 1e-12:
        widths = np.full_like(flows_arr, min_width, dtype=float)
    else:
        widths = min_width + (flows_arr / (max_flow + 1e-12)) * (max_width - min_width)

    # Color mapping
    has_cap = np.isfinite(caps_arr).any()
    if has_cap:
        util = np.divide(flows_arr, caps_arr, out=np.zeros_like(flows_arr), where=np.isfinite(caps_arr) & (caps_arr > 0))
        util = np.clip(util, 0.0, None)
        vmax = max(1.0, float(np.nanmax(util)))  # allow >1 to display overload
        norm = plt.Normalize(vmin=0.0, vmax=vmax)
        color_vals = util
        cbar_label = "Utilization (flow / capacity)"
    else:
        norm = plt.Normalize(vmin=0.0, vmax=max_flow if max_flow > 0 else 1.0)
        color_vals = flows_arr
        cbar_label = "Flow (normalized)"

    cmap_obj = plt.cm.get_cmap(cmap)
    edge_colors = [cmap_obj(norm(val)) for val in color_vals]

    nx.draw_networkx_nodes(G, pos, node_size=node_size, node_color="#3498db", edgecolors="white", alpha=0.95)
    nx.draw_networkx_labels(G, pos, font_size=10, font_color="black", font_weight="bold")

    if G.is_directed():
        nx.draw_networkx_edges(
            G,
            pos,
            edgelist=edges,
            width=widths,
            edge_color=edge_colors,
            alpha=0.9,
            arrows=True,
            arrowstyle="-|>",
            arrowsize=16,
            connectionstyle="arc3,rad=0.05",
        )
    else:
        nx.draw_networkx_edges(G, pos, edgelist=edges, width=widths, edge_color=edge_colors, alpha=0.9)

    plt.title(title, fontsize=15, fontweight="bold")
    plt.axis("off")

    if show_colorbar:
        sm = plt.cm.ScalarMappable(cmap=cmap_obj, norm=norm)
        sm.set_array([])
        plt.colorbar(sm, shrink=0.8, label=cbar_label)

    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches="tight")
    plt.show()


def plot_resilience_curve(
    x: Sequence[float],
    y: Sequence[float],
    title: str = "Resilience Curve",
    xlabel: str = "Fraction of Removed Nodes/Edges",
    ylabel: str = "Performance Ratio",
    baseline: float = 1.0,
    save_path: Optional[str] = None,
) -> None:
    """Plot resilience curve: x=attack fraction, y=normalized performance."""
    x_arr = np.asarray(list(x), dtype=float)
    y_arr = np.asarray(list(y), dtype=float)

    plt.figure(figsize=(9, 6))
    plt.plot(x_arr, y_arr, marker="o", linewidth=2, alpha=0.85, label="Observed")

    if baseline is not None:
        plt.axhline(float(baseline), linestyle="--", alpha=0.6, label="Baseline")

    plt.title(title, fontsize=14, fontweight="bold")
    plt.xlabel(xlabel, fontsize=12)
    plt.ylabel(ylabel, fontsize=12)
    plt.grid(True, linestyle="--", alpha=0.6)
    plt.legend(frameon=True)

    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches="tight")
    plt.show()


def plot_value_distribution(
    values: Sequence[float],
    kind: str = "ccdf",
    title: str = "Value Distribution",
    xlabel: str = "Value",
    ylabel: Optional[str] = None,
    bins: int = 30,
    logx: bool = False,
    logy: bool = False,
    save_path: Optional[str] = None,
) -> None:
    """Plot histogram or CCDF for a sequence of values."""
    vals = np.asarray(list(values), dtype=float)
    vals = vals[np.isfinite(vals)]
    if vals.size == 0:
        print("Warning: empty/invalid values; nothing to plot.")
        return

    plt.figure(figsize=(9, 6))

    kind_l = kind.lower()
    if kind_l == "hist":
        plt.hist(vals, bins=bins, alpha=0.85, edgecolor="black")
        if ylabel is None:
            ylabel = "Count"
    elif kind_l == "ccdf":
        xs = np.sort(vals)
        n = xs.size
        ys = 1.0 - (np.arange(1, n + 1) / n)
        plt.step(xs, ys, where="post", linewidth=2, alpha=0.9)
        if ylabel is None:
            ylabel = "CCDF  P(X ≥ x)"
    else:
        raise ValueError("kind must be 'hist' or 'ccdf'")

    if logx:
        plt.xscale("log")
    if logy:
        plt.yscale("log")

    plt.title(title, fontsize=14, fontweight="bold")
    plt.xlabel(xlabel, fontsize=12)
    plt.ylabel(ylabel, fontsize=12)
    plt.grid(True, linestyle="--", alpha=0.6)

    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches="tight")
    plt.show()
