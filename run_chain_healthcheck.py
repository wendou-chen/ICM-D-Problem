"""
链路健康自检脚本（轻量版，不跑任何真实 heavy 任务）

功能：
- 校验 ExperimentPlan schema 可用；
- 校验 plans/plan.json 存在且能被 ExperimentPlan 解析；
- 调用 execute_plan.py 以 --dry-run 模式执行整条 runs；
- 解析 dry-run 日志，检查：
  - 日志行数 == plan.runs 数量
  - 每一行 ok == True
  - metrics.notes 如果存在，则为 list 类型（防止参数污染成奇怪结构）

使用方式（仓库根目录）：
    python run_chain_healthcheck.py
"""

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from pydantic import ValidationError

from schema import ExperimentPlan


def check_plan_exists_and_valid(plan_path: Path) -> bool:
    """检查计划文件是否存在且能被 ExperimentPlan 解析"""
    print("\n[1] 检查 plans/plan.json ...")
    if not plan_path.exists():
        print(f"[失败] 计划文件未找到: {plan_path}")
        return False

    try:
        data = json.loads(plan_path.read_text(encoding="utf-8"))
        plan = ExperimentPlan.model_validate(data)
        print(f"[成功] 计划已加载: {len(plan.runs)} 个运行, "
              f"{len(plan.hypotheses)} 个假设, "
              f"{len(plan.metrics_definition)} 个指标")
        return True
    except json.JSONDecodeError as e:
        print(f"[失败] 计划不是有效的 JSON: {e}")
        return False
    except ValidationError as e:
        print("[失败] 计划验证失败:")
        for err in e.errors():
            print(f"  - {err['loc']}: {err['msg']}")
        return False
    except Exception as e:
        print(f"[失败] 加载计划时发生意外错误: {e}")
        return False


def run_dry_execute(plan_path: Path, log_path: Path) -> bool:
    """调用 execute_plan.py --dry-run（轻量，不执行 heavy 工具）"""
    print("\n[2] 执行 execute_plan.py --dry-run ...")

    # 确保输出目录存在
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    # 每次自检必须使用“干净”的日志文件，避免 append 导致行数翻倍
    if log_path.exists():
        try:
            log_path.unlink()
            print(f"[信息] 已删除现有日志以避免追加: {log_path}")
        except Exception as e:
            print(f"[失败] 删除现有日志失败 {log_path}: {e}")
            return False

    cmd = [
        sys.executable,
        "execute_plan.py",
        "--plan",
        str(plan_path),
        "--log",
        str(log_path),
        "--dry-run",
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except Exception as e:
        print(f"[失败] 运行 execute_plan.py 失败: {e}")
        return False

    if result.returncode != 0:
        print(f"[失败] execute_plan.py 以代码 {result.returncode} 退出")
        print("标准输出:")
        print(result.stdout)
        print("标准错误:")
        print(result.stderr)
        return False

    print("[成功] execute_plan.py --dry-run 已完成")
    return True


def check_dry_log(plan_path: Path, log_path: Path) -> bool:
    """解析 dry-run 日志并做一致性检查"""
    print("\n[3] 检查 dry-run 日志 ...")

    if not log_path.exists():
        print(f"[失败] 日志文件未找到: {log_path}")
        return False

    try:
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
        runs_len = len(plan.get("runs", []))

        lines_raw = log_path.read_text(encoding="utf-8").splitlines()
        entries = [json.loads(l) for l in lines_raw if l.strip()]
    except json.JSONDecodeError as e:
        print(f"[失败] 日志文件包含无效的 JSON: {e}")
        return False
    except Exception as e:
        print(f"[失败] 读取日志时发生意外错误: {e}")
        return False

    log_len = len(entries)
    all_ok = all(e.get("ok") for e in entries)
    notes_types = [
        type(e.get("metrics", {}).get("notes"))
        for e in entries
        if "notes" in e.get("metrics", {})
    ]

    print(f"  - 计划中的运行数: {runs_len}")
    print(f"  - 日志行数      : {log_len}")
    print(f"  - 全部成功      : {all_ok}")
    if notes_types:
        print(f"  - notes 类型    : {notes_types}")
    else:
        print("  - notes 类型    : (无)")

    ok = True
    if runs_len != log_len:
        print("[失败] 计划运行数 != 日志行数")
        ok = False
    if not all_ok:
        print("[失败] 部分干运行条目 ok=False")
        ok = False
    # notes_types 允许为空或 list 类型
    if any(t is not list for t in notes_types):
        print("[警告] 部分 metrics.notes 不是 list 类型:", notes_types)

    if ok:
        print("[成功] 干运行日志一致性检查通过")
    return ok


def main() -> None:
    print("=" * 80)
    print("实验链路健康检查（仅干运行模式）")
    print("=" * 80)

    plan_path = Path("plans/plan.json")
    # 为避免与历史运行冲突，默认写入一个独立的 healthcheck 日志文件
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = Path("outputs") / f"experiment_log_dry_healthcheck_{ts}.jsonl"

    all_ok = True

    if not check_plan_exists_and_valid(plan_path):
        all_ok = False

    if all_ok and not run_dry_execute(plan_path, log_path):
        all_ok = False

    if all_ok and not check_dry_log(plan_path, log_path):
        all_ok = False

    print("\n" + "=" * 80)
    if all_ok:
        print("[成功] 链路健康检查（干运行）通过")
        print(f"  - 计划: {plan_path}")
        print(f"  - 日志: {log_path}")
    else:
        print("[失败] 链路健康检查（干运行）失败")
        print("  请根据上面的错误信息检查 plan / execute_plan / 日志写入是否正常。")
    print("=" * 80)

    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()

