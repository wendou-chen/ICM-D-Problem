"""
Pack Task1/2/3 artifacts and team share bundle.
Standard library only.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple
from zipfile import ZIP_DEFLATED, ZipFile


LOG_FALLBACKS = [
    "outputs/experiment_log.jsonl",
    "outputs/experiment_log_full_first3.jsonl",
    "outputs/experiment_log_dry.jsonl",
]

TASK_TOOL_MAP = {
    "task1": ["run_etl", "build_graph", "run_baseline"],
    "task2": ["run_task2", "run_task2_ablation", "analyze_task2_ablation"],
    "task3": ["sensitivity", "attack_nodes"],
}

FORBIDDEN_DIRS = {
    ".git",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    "node_modules",
    "venv",
    ".venv",
}


def _pick_log_path(explicit: str | None) -> Path:
    if explicit:
        p = Path(explicit)
        if p.exists():
            return p
    for cand in LOG_FALLBACKS:
        p = Path(cand)
        if p.exists():
            return p
    raise FileNotFoundError("No log jsonl found")


def _is_forbidden(path: Path) -> bool:
    lower = str(path).lower()
    name = path.name.lower()
    if ".env" in name or ".env" in lower:
        return True
    if name.endswith(".key") or "_key" in lower or "_token" in lower:
        return True
    if "token" in lower or "apikey" in lower:
        return True
    for part in path.parts:
        if part.lower() in FORBIDDEN_DIRS:
            return True
    return False


def _resolve_artifact(path_str: str, root: Path) -> Path | None:
    raw = path_str.replace("\\", "/")
    candidate = root / raw
    if candidate.exists():
        return candidate
    for base in ["data/processed", "outputs", "paper", "data", "scripts"]:
        cand = root / base / raw
        if cand.exists():
            return cand
    return None


def _load_log(log_path: Path) -> Tuple[List[dict], List[str]]:
    records: List[dict] = []
    lines: List[str] = []
    for line in log_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        lines.append(line)
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        records.append(rec)
    return records, lines


def _git_commit() -> str:
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            stderr=subprocess.DEVNULL,
            text=True,
        )
        return out.strip()
    except Exception:
        return "unknown"


def _write_zip(
    zip_path: Path,
    root: Path,
    include_files: List[Path],
    manifest: dict,
    log_lines: List[str],
) -> None:
    if zip_path.exists():
        zip_path.unlink()
    with ZipFile(zip_path, "w", compression=ZIP_DEFLATED) as zf:
        manifest_bytes = json.dumps(manifest, ensure_ascii=False, indent=2).encode("utf-8")
        zf.writestr("manifest.json", manifest_bytes)

        log_bytes = ("\n".join(log_lines) + "\n").encode("utf-8")
        zf.writestr("task_log.jsonl", log_bytes)

        for fpath in include_files:
            rel = fpath.relative_to(root).as_posix()
            zf.write(fpath, rel)


def main() -> int:
    parser = argparse.ArgumentParser(description="Pack task artifacts and team share bundle.")
    parser.add_argument("--plan", default="plans/plan.json")
    parser.add_argument("--log", default=None)
    parser.add_argument("--out_dir", default="handoff")
    parser.add_argument("--task1_zip", default="task1_artifacts.zip")
    parser.add_argument("--task2_zip", default="task2_artifacts.zip")
    parser.add_argument("--task3_zip", default="task3_artifacts.zip")
    parser.add_argument("--all_zip", default="all_teamshare.zip")
    args = parser.parse_args()

    root = Path.cwd()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    log_path = _pick_log_path(args.log)
    records, lines = _load_log(log_path)

    # Build task zips
    task_zip_paths = {}
    for task_name, tools in TASK_TOOL_MAP.items():
        task_records = [r for r in records if r.get("tool") in tools]
        task_lines = [l for l in lines if json.loads(l).get("tool") in tools]

        included_files: List[Path] = []
        included_rel: List[str] = []
        missing_files: List[str] = []
        runs_summary: List[dict] = []

        for rec in task_records:
            runs_summary.append(
                {
                    "tool": rec.get("tool"),
                    "ok": rec.get("ok"),
                    "run_id": rec.get("run_id"),
                    "runtime_sec": rec.get("runtime_sec"),
                    "metrics": rec.get("metrics") or {},
                    "command": rec.get("command"),
                }
            )
            for art in rec.get("artifacts", []):
                path_str = art.get("path", "")
                if not path_str:
                    continue
                if _is_forbidden(Path(path_str)):
                    raise SystemExit(f"Forbidden artifact path: {path_str}")
                resolved = _resolve_artifact(path_str, root)
                if resolved and resolved.exists():
                    if _is_forbidden(resolved):
                        raise SystemExit(f"Forbidden file resolved: {resolved}")
                    rel = resolved.relative_to(root).as_posix()
                    if rel not in included_rel:
                        included_rel.append(rel)
                        included_files.append(resolved)
                else:
                    missing_files.append(path_str)

        manifest = {
            "task": task_name,
            "log_used": str(log_path),
            "included_files": included_rel,
            "missing_files": missing_files,
            "runs": runs_summary,
        }

        zip_name = getattr(args, f"{task_name}_zip")
        zip_path = out_dir / zip_name
        _write_zip(zip_path, root, included_files, manifest, task_lines)
        task_zip_paths[task_name] = zip_path

    # Build all_teamshare.zip
    all_zip_path = out_dir / args.all_zip
    if all_zip_path.exists():
        all_zip_path.unlink()

    must_include = [
        Path("paper/main_submission.pdf"),
        Path("paper/ai_appendix.pdf"),
        Path("paper/main_submission_cn.tex"),
        Path("paper/sections/overview_cn.tex"),
        Path("plans/plan.json"),
        Path("schemas/experiment_plan.schema.json"),
    ]

    log_candidates = list(Path("outputs").glob("experiment_log*.jsonl"))
    if not log_candidates:
        log_candidates = [log_path]

    for f in must_include + log_candidates + list(task_zip_paths.values()):
        if _is_forbidden(f):
            raise SystemExit(f"Forbidden file in package list: {f}")

    handoff_manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "git_commit": _git_commit(),
        "log_used": str(log_path),
        "included_files": [],
    }

    with ZipFile(all_zip_path, "w", compression=ZIP_DEFLATED) as zf:
        for fpath in must_include + log_candidates + list(task_zip_paths.values()):
            fpath_abs = fpath if fpath.is_absolute() else (root / fpath)
            if not fpath_abs.exists():
                raise SystemExit(f"Missing file for all_teamshare: {fpath_abs}")
            rel = fpath_abs.relative_to(root).as_posix()
            handoff_manifest["included_files"].append(rel)
            zf.write(fpath_abs, rel)

        manifest_bytes = json.dumps(handoff_manifest, ensure_ascii=False, indent=2).encode("utf-8")
        zf.writestr("handoff_manifest.json", manifest_bytes)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
