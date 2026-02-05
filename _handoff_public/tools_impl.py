"""
工具封装层：将脚本调用封装为统一的工具函数，返回 RunResult。

所有工具函数都调用 runner.run_cmd 执行命令，并返回标准化的 RunResult。
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

from runner import run_cmd
from schema import RunResult


def run_etl(
    raw_dir: str = "data/raw",
    out_dir: str = "data/processed",
    strict: bool = True,
    random_seed: int = 42,
    **kwargs,  # 忽略未知参数，增强鲁棒性
) -> RunResult:
    """
    运行 ETL 数据清洗。
    
    Args:
        raw_dir: 原始数据目录
        out_dir: 输出目录
        strict: 严格模式（当前脚本不支持，记录在 paper_hooks）
        random_seed: 随机种子
    
    Returns:
        RunResult: 运行结果
    """
    cmd = [
        "python",
        "scripts/data_clean.py",
        "--outdir", out_dir,
        "--nodes_raw", str(Path(raw_dir) / "nodes_all.csv"),
        "--edges_raw", str(Path(raw_dir) / "edges_all.csv"),
        "--bus_stops_raw", str(Path(raw_dir) / "Bus_Stops.csv"),
    ]
    
    result = run_cmd(
        tool="run_etl",
        cmd=cmd,
        out_dir=out_dir,
        random_seed=random_seed,
    )
    
    # 记录 strict 参数（脚本当前不支持）
    if strict:
        result.paper_hooks["strict_mode"] = "requested but not implemented in data_clean.py"
    
    return result


def build_graph(
    processed_dir: str = "data/processed",
    graph_out: str = "data/processed/graph.pkl",
    export: Optional[str] = None,
    **kwargs,  # 忽略未知参数，增强鲁棒性
) -> RunResult:
    """
    构建图并保存为 graph.pkl。
    
    Args:
        processed_dir: 处理后的数据目录
        graph_out: 图输出路径
        export: 导出选项（记录在 provenance/paper_hooks，脚本可能不支持）
    
    Returns:
        RunResult: 运行结果
    """
    # 注意：实际脚本可能没有命令行接口，这里使用 Python 模块调用
    # 如果 scripts/data_loader.py 不存在，尝试使用 src/data_loader.py
    cmd = [
        "python",
        "-c",
        f"""
import sys
from pathlib import Path
from shutil import copyfile

sys.path.insert(0, str(Path('.').resolve()))

processed_dir = Path(r"{processed_dir}").resolve()
graph_out = Path(r"{graph_out}").resolve()

try:
    from src.data_loader import BaltimoreDataManager
    root_dir = processed_dir.parent.parent
    manager = BaltimoreDataManager(root_dir=str(root_dir))
    manager.processed_data_dir = str(processed_dir)
    manager.load_raw_data()
    manager.build_drive_layer()
    manager.build_bus_layer_and_connect()
    manager.sanity_check_and_prune()
    manager.finalize_cost()
    manager.export_data()

    default_graph = processed_dir / "graph.pkl"
    if graph_out != default_graph:
        graph_out.parent.mkdir(parents=True, exist_ok=True)
        copyfile(default_graph, graph_out)
    print(f"Graph saved to {{graph_out}}")
except Exception as ex:
    print(f"Error: {{ex}}", file=sys.stderr)
    sys.exit(1)
"""
    ]
    
    result = run_cmd(
        tool="build_graph",
        cmd=cmd,
        out_dir=str(Path(graph_out).parent),
        random_seed=None,
    )
    
    # 记录 export 参数（转换为字符串，确保符合 paper_hooks 的 Dict[str, str] 类型）
    if export:
        result.provenance["export_requested"] = export
        result.paper_hooks["export"] = str(export)
    
    return result


def run_baseline(
    graph_pkl: str = "data/processed/graph.pkl",
    od_samples: int = 5000,
    metrics: Optional[str] = None,
    out_dir: str = "outputs/baseline",
    **kwargs,  # 忽略未知参数，增强鲁棒性
) -> RunResult:
    """
    运行基线分析。
    
    Args:
        graph_pkl: 图文件路径
        od_samples: OD 样本数量（对应脚本的 --K 参数）
        metrics: 指标选项（记录但不强制脚本支持）
        out_dir: 输出目录
    
    Returns:
        RunResult: 运行结果
    """
    cmd = [
        "python",
        "scripts/baseline_analysis.py",
        "--graph", graph_pkl,
        "--K", str(od_samples),
        "--outdir", out_dir,
    ]
    
    result = run_cmd(
        tool="run_baseline",
        cmd=cmd,
        out_dir=out_dir,
        random_seed=42,  # baseline 默认使用 42
    )
    
    # 记录 metrics 参数（转换为字符串，确保符合 paper_hooks 的 Dict[str, str] 类型）
    if metrics:
        if isinstance(metrics, list):
            result.paper_hooks["metrics_requested"] = ",".join(str(m) for m in metrics)
        else:
            result.paper_hooks["metrics_requested"] = str(metrics)
    
    return result


def run_task2(
    config_path: Optional[str] = None,
    random_seed: int = 42,
    out_dir: str = "outputs/task2",
    mode: str = "fast",
    **kwargs,  # 忽略未知参数，增强鲁棒性
) -> RunResult:
    """
    运行 Task2 优化。
    
    Args:
        config_path: 配置文件路径（可选）
        random_seed: 随机种子
        out_dir: 输出目录
        mode: 运行模式（fast/normal）
    
    Returns:
        RunResult: 运行结果
    """
    # 检查是否存在 run_task2.py，否则使用 run_hybrid_pso_ga_task2.py
    if mode == "hybrid_pipeline":
         cmd = [
            "python",
            "scripts/run_task2_hybrid_pipeline.py",
            "--graph", "data/processed/graph.pkl",
            "--candidates", "data/processed/candidates_task2.json",
            "--output_dir", out_dir,
            "--seed", str(random_seed),
        ]
    elif Path("scripts/run_task2.py").exists():
        cmd = [
            "python",
            "scripts/run_task2.py",
            "--config", config_path or "config.json",
            "--out", out_dir,
            "--seed", str(random_seed),
            "--mode", mode,
        ]
    elif Path("scripts/reproduce_task2.ps1").exists():
        # 使用 PowerShell 脚本
        cmd = [
            "powershell",
            "-ExecutionPolicy", "Bypass",
            "-File", "scripts/reproduce_task2.ps1",
        ]
    else:
        # 使用 run_hybrid_pso_ga_task2.py（实际存在的脚本）
        cmd = [
            "python",
            "scripts/run_hybrid_pso_ga_task2.py",
            "--graph", "data/processed/graph.pkl",
            "--candidates", "data/processed/candidates_task2.json",
            "--output_dir", out_dir,
            "--seed", str(random_seed),
        ]
        if config_path:
            result = run_cmd(
                tool="run_task2",
                cmd=["echo", "Config file support not implemented"],
                out_dir=out_dir,
                random_seed=random_seed,
            )
            result.ok = False
            result.stderr_tail = "Config file parameter not supported by run_hybrid_pso_ga_task2.py"
            return result
    
    result = run_cmd(
        tool="run_task2",
        cmd=cmd,
        out_dir=out_dir,
        random_seed=random_seed,
    )
    
    # 自动收集 hybrid_log artifact
    if mode == "hybrid_pipeline":
        from pathlib import Path
        od = Path(out_dir)
        logs = list(od.glob("hybrid_log_*.json"))
        if logs:
            # 取最新的一个
            latest_log = max(logs, key=lambda p: p.stat().st_mtime)
            from schema import Artifact, ArtifactType
            result.artifacts.append(Artifact(
                path=str(latest_log).replace("\\", "/"),
                type=ArtifactType.LOG,
                desc="Hybrid Pipeline Run Log (PSO->GA->SA)"
            ))
    
    if config_path:
        result.provenance["config_path"] = config_path
    result.paper_hooks["mode"] = mode
    
    return result


def sensitivity(
    base_run_dir: str,
    delta: float = 0.1,
    trials: int = 20,
    what: Optional[str] = None,
    out_dir: str = "outputs/robustness/sensitivity",
    **kwargs,  # 忽略未知参数，增强鲁棒性
) -> RunResult:
    """
    运行敏感性分析。
    
    Args:
        base_run_dir: 基础运行目录
        delta: 变化量
        trials: 试验次数
        what: 分析对象（记录但不强制支持）
        out_dir: 输出目录
    
    Returns:
        RunResult: 运行结果
    """
    script_path = Path("scripts/robustness_sensitivity.py")
    
    if not script_path.exists():
        # 脚本不存在，返回失败结果但不抛异常
        from datetime import datetime, timezone
        result = RunResult(
            ok=False,
            tool="sensitivity",
            run_id=f"sensitivity_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}",
            command="",
            started_at=datetime.now(timezone.utc),
            ended_at=datetime.now(timezone.utc),
            runtime_sec=0.0,
            stderr_tail=f"Missing script: {script_path}",
        )
        return result
    
    cmd = [
        "python",
        str(script_path),
        "--base", base_run_dir,
        "--delta", str(delta),
        "--trials", str(trials),
        "--out", out_dir,
    ]
    
    result = run_cmd(
        tool="sensitivity",
        cmd=cmd,
        out_dir=out_dir,
        random_seed=None,
    )
    
    if what:
        result.paper_hooks["what"] = what
    
    return result


def attack_nodes(
    graph_pkl: str,
    k_list: Optional[List[int]] = None,
    centrality: str = "betweenness",
    recompute_metric: str = "giant_component",
    out_dir: str = "outputs/robustness/attack_nodes",
    **kwargs,  # 忽略未知参数，增强鲁棒性
) -> RunResult:
    """
    运行节点攻击分析。
    
    Args:
        graph_pkl: 图文件路径
        k_list: 攻击节点数量列表
        centrality: 中心性指标
        recompute_metric: 重新计算的指标
        out_dir: 输出目录
    
    Returns:
        RunResult: 运行结果
    """
    script_path = Path("scripts/robustness_attack_nodes.py")
    
    if not script_path.exists():
        # 脚本不存在，返回失败结果但不抛异常
        from datetime import datetime, timezone
        result = RunResult(
            ok=False,
            tool="attack_nodes",
            run_id=f"attack_nodes_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}",
            command="",
            started_at=datetime.now(timezone.utc),
            ended_at=datetime.now(timezone.utc),
            runtime_sec=0.0,
            stderr_tail=f"Missing script: {script_path}",
        )
        return result
    
    cmd = [
        "python",
        str(script_path),
        "--graph", graph_pkl,
        "--centrality", centrality,
        "--metric", recompute_metric,
        "--out", out_dir,
    ]
    
    if k_list:
        cmd.extend(["--k", ",".join(map(str, k_list))])
    
    result = run_cmd(
        tool="attack_nodes",
        cmd=cmd,
        out_dir=out_dir,
        random_seed=None,
    )
    
    return result


def ping(message: str = "ping") -> RunResult:
    """
    轻量 ping 工具，用于自检 tool-loop。
    
    Args:
        message: 回显消息
    
    Returns:
        RunResult: 运行结果（ok=True，metrics 包含 echo 字段）
    """
    from datetime import datetime, timezone
    
    result = RunResult(
        ok=True,
        tool="ping",
        run_id=f"ping_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}",
        command="ping",
        started_at=datetime.now(timezone.utc),
        ended_at=datetime.now(timezone.utc),
        runtime_sec=0.0,
        metrics={"echo": message},
    )
    
    return result

def run_robustness(
    graph_path: str = "data/processed/graph.pkl",
    solution_path: str = "outputs/task2/best_solution.json",
    out_dir: str = "outputs/robustness",
    smoke: bool = False,
    random_seed: int = 42,
    **kwargs,
) -> RunResult:
    """
    ig/a4iyO嬓CW˓,a`m ?
    
    Args:
        graph_path: epg`m`w[?
        solution_path: YtEUĉt}
        out_dir: HgdV)}
        smoke: ē`G qKUqtyt?
        random_seed: ŕ_n~]t ("$1,|o]G^)
        
    Returns:
        RunResult
    """
    cmd = [
        "python",
        "scripts/run_robustness_suite.py",
        "--graph", graph_path,
        "--solution", solution_path,
        "--out_dir", out_dir,
    ]
    if smoke:
        cmd.append("--smoke")
        
    # Note: run_robustness_suite internally uses multiprocessing which might
    # conflict with setting fixed numpy seed globally via run_cmd's mechanism?
    # run_cmd sets PYTHONHASHSEED but internal seed is passed via args usually.
    # run_robustness_suite handles its own seeding based on loops.
    # We pass random_seed via env logic in run_cmd if needed, 
    # but here just running the command is enough.
    
    result = run_cmd(
        tool="run_robustness",
        cmd=cmd,
        out_dir=out_dir,
        random_seed=random_seed,
    )
    
    # Auto-register artifacts
    # 1. Curves
    targets = [
        ("curve_random_failure.csv", "Robustness Curve (Random Failure)"),
        ("curve_targeted_attack.csv", "Robustness Curve (Targeted Attack)"),
        ("curve_perturbation.csv", "Robustness Curve (Perturbation)"),
    ]
    
    from schema import Artifact, ArtifactType
    
    for fname, desc in targets:
        fpath = Path(out_dir) / fname
        if fpath.exists():
            result.artifacts.append(Artifact(
                path=str(fpath).replace("\\", "/"),
                type=ArtifactType.TABLE,
                desc=desc
            ))
            
    # 2. Plots
    plots_dir = Path(out_dir) / "plots"
    if plots_dir.exists():
        for png in plots_dir.glob("*.png"):
            result.artifacts.append(Artifact(
                path=str(png).replace("\\", "/"),
                type=ArtifactType.PLOT,
                desc=f"Robustness Plot: {png.name}"
            ))
            
    return result


def run_task2_ablation(
    mode: str = "all",
    seed_base: int = 42,
    n_repeats: int = 5,
    out_dir: str = "outputs/task2",
    dry_run: bool = False,
    max_runs: int | None = None,
    sample_runs: int | None = None,
    force: bool = False,
    graph: str | None = None,
    candidates: str | None = None,
    budget: float | None = None,
    K: int | None = None,
    lambda_reg: float | None = None,
    od_policy: str | None = None,
    od_pairs_path: str | None = None,
    **kwargs,
) -> "RunResult":
    """
    运行 Task2 消融与超参扫描。
    """
    cmd = [
        "python",
        "scripts/run_algorithm_ablation.py",
        "--mode", mode,
        "--seed_base", str(seed_base),
        "--n_repeats", str(n_repeats),
        "--output_dir", out_dir,
    ]
    if dry_run:
        cmd.append("--dry-run")
    if max_runs is not None:
        cmd.extend(["--max_runs", str(max_runs)])
    if sample_runs is not None:
        cmd.extend(["--sample_runs", str(sample_runs)])
    if force:
        cmd.append("--force")
    if graph:
        cmd.extend(["--graph", graph])
    if candidates:
        cmd.extend(["--candidates", candidates])
    if budget is not None:
        cmd.extend(["--budget", str(budget)])
    if K is not None:
        cmd.extend(["--K", str(K)])
    if lambda_reg is not None:
        cmd.extend(["--lambda_reg", str(lambda_reg)])
    if od_policy:
        cmd.extend(["--od_policy", od_policy])
    if od_pairs_path:
        cmd.extend(["--od_pairs_path", od_pairs_path])

    result = run_cmd(
        tool="run_task2_ablation",
        cmd=cmd,
        out_dir=out_dir,
        random_seed=seed_base,
    )

    # attach artifacts if present
    try:
        from schema import Artifact, ArtifactType
        od = Path(out_dir)
        res = od / "ablation_results.csv"
        if res.exists():
            result.artifacts.append(Artifact(path=str(res).replace("\\", "/"), type=ArtifactType.TABLE, desc="Ablation results CSV"))
        logs = od / "ablation_logs"
        if logs.exists():
            result.artifacts.append(Artifact(path=str(logs).replace("\\", "/"), type=ArtifactType.LOG, desc="Ablation per-run logs"))
    except Exception:
        pass

    return result


def analyze_task2_ablation(
    in_csv: str = "outputs/task2/ablation_results.csv",
    out_dir: str = "outputs/task2",
    feasible_only: bool = False,
    topk: int = 5,
    **kwargs,
) -> "RunResult":
    """
    分析消融结果并生成对比表与可视化。
    """
    cmd = [
        "python",
        "scripts/analyze_ablation_results.py",
        "--in_csv", in_csv,
        "--out_dir", out_dir,
        "--topk", str(topk),
    ]
    if feasible_only:
        cmd.append("--feasible_only")

    result = run_cmd(
        tool="analyze_task2_ablation",
        cmd=cmd,
        out_dir=out_dir,
        random_seed=None,
    )

    try:
        from schema import Artifact, ArtifactType
        od = Path(out_dir)
        summary = od / "ablation_summary.md"
        if summary.exists():
            result.artifacts.append(Artifact(path=str(summary).replace("\\", "/"), type=ArtifactType.TABLE, desc="Ablation summary"))
        viz_dir = od / "viz"
        if viz_dir.exists():
            result.artifacts.append(Artifact(path=str(viz_dir).replace("\\", "/"), type=ArtifactType.PLOT, desc="Ablation plots"))
    except Exception:
        pass

    return result
