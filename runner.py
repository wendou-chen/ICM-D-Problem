"""
统一命令执行器，将"脚本运行"标准化为 RunResult。

核心功能：
- run_cmd: 执行命令并返回 RunResult
- append_jsonl: 将 RunResult 追加到 JSONL 文件
"""

import json
import os
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from schema import Artifact, ArtifactType, RunResult


def _infer_artifact_type(file_path: str) -> ArtifactType:
    """根据文件后缀推断产物类型"""
    suffix = Path(file_path).suffix.lower()
    type_map = {
        '.csv': ArtifactType.TABLE,
        '.json': ArtifactType.TABLE,
        '.geojson': ArtifactType.TABLE,
        '.pkl': ArtifactType.MODEL,
        '.png': ArtifactType.PLOT,
        '.jpg': ArtifactType.PLOT,
        '.jpeg': ArtifactType.PLOT,
        '.svg': ArtifactType.PLOT,
        '.pdf': ArtifactType.PLOT,
        '.md': ArtifactType.LOG,
        '.txt': ArtifactType.LOG,
        '.log': ArtifactType.LOG,
    }
    return type_map.get(suffix, ArtifactType.OTHER)


def _get_file_snapshot(directory: Path) -> Dict[str, float]:
    """获取目录下所有文件的快照（路径 -> 修改时间）"""
    snapshot = {}
    if not directory.exists():
        return snapshot
    
    for root, dirs, files in os.walk(directory):
        for file in files:
            file_path = Path(root) / file
            try:
                snapshot[str(file_path.relative_to(directory))] = file_path.stat().st_mtime
            except (OSError, ValueError):
                pass
    return snapshot


def _extract_metrics_from_stdout(stdout: str) -> Dict[str, Any]:
    """从 stdout 中提取 metrics JSON"""
    metrics = {}
    # 确保 stdout 是字符串
    if stdout is None:
        return metrics
    if not isinstance(stdout, str):
        stdout = str(stdout)
    for line in stdout.splitlines():
        if line.strip().startswith("__METRICS_JSON__="):
            json_str = line.split("__METRICS_JSON__=", 1)[1].strip()
            try:
                metrics = json.loads(json_str)
            except json.JSONDecodeError:
                pass
            break
    return metrics


def _get_git_commit() -> Optional[str]:
    """获取当前 git commit hash"""
    try:
        result = subprocess.run(
            ['git', 'rev-parse', 'HEAD'],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        pass
    return None


def _tail_text(text: str, max_lines: int = 200) -> str:
    """保留文本的最后 N 行"""
    # 确保 text 是字符串（防止 None）
    if text is None:
        return ""
    if not isinstance(text, str):
        return str(text)
    lines = text.splitlines()
    if len(lines) <= max_lines:
        return text
    return '\n'.join(lines[-max_lines:])


def run_cmd(
    tool: str,
    cmd: List[str],
    workdir: Optional[str] = None,
    out_dir: Optional[str] = None,
    random_seed: Optional[int] = None,
    timeout_sec: Optional[int] = None,
    env_overrides: Optional[Dict[str, str]] = None,
    run_id: Optional[str] = None,
) -> RunResult:
    """
    执行命令并返回 RunResult。
    
    Args:
        tool: 工具名称
        cmd: 命令列表（如 ['python', 'script.py', '--arg', 'value']）
        workdir: 工作目录（命令执行的工作目录）
        out_dir: 输出目录（用于收集产物）
        random_seed: 随机种子（会设置到环境变量）
        timeout_sec: 超时时间（秒）
        env_overrides: 环境变量覆盖
        run_id: 运行ID（如果不提供则自动生成）
    
    Returns:
        RunResult: 运行结果
    """
    # 生成 run_id
    if run_id is None:
        run_id = f"{tool}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    
    # 记录开始时间
    started_at = datetime.now(timezone.utc)
    
    # 准备工作目录
    if workdir:
        workdir_path = Path(workdir).resolve()
    else:
        workdir_path = Path.cwd()
    
    # 准备输出目录快照（执行前）
    out_dir_path = None
    before_snapshot = {}
    if out_dir:
        out_dir_path = Path(out_dir).resolve()
        before_snapshot = _get_file_snapshot(out_dir_path)
    
    # 准备环境变量
    env = os.environ.copy()
    if random_seed is not None:
        env['PYTHONHASHSEED'] = str(random_seed)
        env['RANDOM_SEED'] = str(random_seed)
    if env_overrides:
        env.update(env_overrides)
    
    # 执行命令
    ok = False
    stdout_text = ""
    stderr_text = ""
    exit_code = -1
    
    try:
        result = subprocess.run(
            cmd,
            cwd=str(workdir_path),
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_sec,
        )
        exit_code = result.returncode
        # 确保 stdout/stderr 是字符串（防止 None）
        stdout_text = result.stdout if result.stdout is not None else ""
        stderr_text = result.stderr if result.stderr is not None else ""
        ok = exit_code == 0
    except subprocess.TimeoutExpired:
        stdout_text = ""
        stderr_text = f"Command timed out after {timeout_sec} seconds"
        ok = False
    except Exception as e:
        stdout_text = ""
        stderr_text = f"Error running command: {str(e)}"
        ok = False
    
    # 记录结束时间
    ended_at = datetime.now(timezone.utc)
    runtime_sec = (ended_at - started_at).total_seconds()
    
    # 提取 metrics
    metrics = _extract_metrics_from_stdout(stdout_text)
    
    # 收集产物
    artifacts: List[Artifact] = []
    if out_dir_path and out_dir_path.exists():
        after_snapshot = _get_file_snapshot(out_dir_path)
        
        # 找出新增或修改的文件
        for rel_path, mtime in after_snapshot.items():
            if rel_path not in before_snapshot or before_snapshot[rel_path] != mtime:
                full_path = out_dir_path / rel_path
                try:
                    file_size = full_path.stat().st_size
                    artifact_type = _infer_artifact_type(rel_path)
                    artifacts.append(Artifact(
                        path=str(rel_path),
                        type=artifact_type,
                        desc=f"Generated by {tool}",
                        bytes=file_size,
                    ))
                except OSError:
                    pass
    
    # 准备 provenance
    provenance: Dict[str, Any] = {
        'python_version': sys.version,
        'platform': platform.platform(),
    }
    if random_seed is not None:
        provenance['random_seed'] = random_seed
    
    git_commit = _get_git_commit()
    if git_commit:
        provenance['git_commit'] = git_commit
    
    # 构建命令字符串
    command_str = ' '.join(cmd)
    
    # 创建 RunResult
    run_result = RunResult(
        ok=ok,
        tool=tool,
        run_id=run_id,
        command=command_str,
        started_at=started_at,
        ended_at=ended_at,
        runtime_sec=runtime_sec,
        stdout_tail=_tail_text(stdout_text),
        stderr_tail=_tail_text(stderr_text),
        artifacts=artifacts,
        metrics=metrics,
        provenance=provenance,
    )
    
    return run_result


def append_jsonl(path: str, run_result: RunResult) -> None:
    """
    将 RunResult 追加到 JSONL 文件。
    
    Args:
        path: JSONL 文件路径
        run_result: 要追加的 RunResult
    """
    json_path = Path(path)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(json_path, 'a', encoding='utf-8') as f:
        json_str = run_result.to_json(indent=None)  # 单行 JSON
        f.write(json_str + '\n')
