"""
严格按 ExperimentPlan 执行 runs，自动生成 experiment_log.jsonl，并做 expected_artifacts 校验。

执行引擎使用 DeepSeek-Chat（thinking+tools）进行 tool-loop，但由代码强制顺序与一致性，
防止模型乱序/乱调用。
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# 加载 .env 文件中的环境变量
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv 未安装时静默跳过

from runner import append_jsonl
from schema import ExperimentPlan, RunResult, StepConfig
from tool_schemas import get_tools
from tools_impl import (
    attack_nodes,
    build_graph,
    ping,
    run_baseline,
    run_etl,
    run_task2,
    sensitivity,
)

# Avoid UnicodeEncodeError on Windows consoles (e.g., GBK).
def _safe_text(text: Optional[str]) -> str:
    if text is None:
        return ""
    encoding = sys.stdout.encoding or "utf-8"
    try:
        text.encode(encoding)
        return text
    except UnicodeEncodeError:
        return text.encode(encoding, errors="replace").decode(encoding, errors="replace")

# 尝试导入 OpenAI SDK
try:
    from openai import OpenAI
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False
    try:
        import requests
        HAS_REQUESTS = True
    except ImportError:
        HAS_REQUESTS = False


def _get_deepseek_client(base_url: str = "https://api.deepseek.com") -> Any:
    """获取 DeepSeek API 客户端"""
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        raise ValueError("DEEPSEEK_API_KEY environment variable not set")
    
    if HAS_OPENAI:
        return OpenAI(api_key=api_key, base_url=base_url)
    elif HAS_REQUESTS:
        # 使用 requests 直连（简化实现）
        class RequestsClient:
            def __init__(self, api_key: str, base_url: str):
                self.api_key = api_key
                self.base_url = base_url.rstrip("/")
            
            def chat(self, **kwargs):
                import requests
                url = f"{self.base_url}/v1/chat/completions"
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                }
                response = requests.post(url, json=kwargs, headers=headers)
                response.raise_for_status()
                return response.json()
        
        return RequestsClient(api_key, base_url)
    else:
        raise ImportError("Neither openai nor requests is available. Install: pip install openai>=1")


def _call_tool(tool_name: str, arguments: Dict[str, Any], dry_run: bool = False) -> RunResult:
    """调用工具函数并返回 RunResult"""
    tool_map = {
        "run_etl": run_etl,
        "build_graph": build_graph,
        "run_baseline": run_baseline,
        "run_task2": run_task2,
        "sensitivity": sensitivity,
        "attack_nodes": attack_nodes,
        "ping": ping,
    }
    
    if tool_name not in tool_map:
        return RunResult(
            ok=False,
            tool=tool_name,
            run_id=f"unknown_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}",
            command="",
            started_at=datetime.now(timezone.utc),
            ended_at=datetime.now(timezone.utc),
            runtime_sec=0.0,
            stderr_tail=f"Unknown tool: {tool_name}",
        )
    
    if dry_run:
        # 生成模拟 RunResult
        return RunResult(
            ok=True,
            tool=tool_name,
            run_id=f"{tool_name}_dry_run_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}",
            command=f"DRY_RUN: {tool_name} with args {arguments}",
            started_at=datetime.now(timezone.utc),
            ended_at=datetime.now(timezone.utc),
            runtime_sec=0.0,
            metrics={"dry_run": True},
        )
    
    # 真实执行
    func = tool_map[tool_name]
    try:
        return func(**arguments)
    except Exception as e:
        return RunResult(
            ok=False,
            tool=tool_name,
            run_id=f"{tool_name}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}",
            command=str(arguments),
            started_at=datetime.now(timezone.utc),
            ended_at=datetime.now(timezone.utc),
            runtime_sec=0.0,
            stderr_tail=f"Tool execution error: {str(e)}",
        )


def _check_expected_artifacts(
    run_result: RunResult,
    expected_artifacts: List[str],
    full_mode: bool = False,
) -> RunResult:
    """检查 expected_artifacts 是否存在"""
    if not full_mode or not expected_artifacts:
        return run_result
    
    missing = []
    for artifact_path in expected_artifacts:
        if not Path(artifact_path).exists():
            missing.append(artifact_path)
    
    if missing:
        # 保留 ok=True，但在 metrics 和 stderr_tail 中记录缺失
        run_result.metrics["missing_expected"] = missing
        run_result.stderr_tail += f"\nMissing expected artifacts: {', '.join(missing)}"
    
    return run_result


def _execute_step_with_llm(
    client: Any,
    tools: List[dict],
    step_config: StepConfig,
    step_index: int,
    total_steps: int,
    dry_run: bool = False,
    thinking: bool = True,
    model: str = "deepseek-chat",
    max_retries: int = 2,
) -> RunResult:
    """使用 LLM 执行单个步骤（带顺序强制检查）"""
    
    tool_name = step_config.tool_name
    plan_args = step_config.args
    
    # System prompt（强约束）
    system_prompt = """你是实验编排器。你必须严格按计划 runs 的顺序执行。每一轮你只能调用"下一步"指定的工具，且参数必须来自计划。不要解释，不要输出多余文字；当你需要执行时，直接发起 tool_call。"""
    
    # User prompt（每步提示）
    user_prompt = f"下一步：{tool_name}。参数：{json.dumps(plan_args, ensure_ascii=False)}。请调用该工具。"
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    
    retry_count = 0
    
    while retry_count <= max_retries:
        # 调用 LLM
        try:
            if HAS_OPENAI:
                response = client.chat.completions.create(
                    model=model,
                    messages=messages,
                    tools=tools,
                    tool_choice="required",  # 强制要求工具调用
                )
                response_dict = response.model_dump()
            else:
                # requests 客户端
                response_dict = client.chat(
                    model=model,
                    messages=messages,
                    tools=tools,
                    tool_choice="required",
                )
        except Exception as e:
            return RunResult(
                ok=False,
                tool=tool_name,
                run_id=f"{tool_name}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}",
                command="",
                started_at=datetime.now(timezone.utc),
                ended_at=datetime.now(timezone.utc),
                runtime_sec=0.0,
                stderr_tail=f"LLM API error: {str(e)}",
            )
        
        # 提取 assistant 消息
        choice = response_dict["choices"][0]
        message = choice["message"]
        
        # 处理 reasoning（如果有）
        if thinking and "reasoning_content" in message:
            reasoning_path = Path("logs/reasoning") / f"step_{step_index}.txt"
            reasoning_path.parent.mkdir(parents=True, exist_ok=True)
            reasoning_path.write_text(message["reasoning_content"], encoding="utf-8")
            # 不回灌到 messages
        
        # 检查 tool_calls
        tool_calls = message.get("tool_calls", [])
        if not tool_calls:
            # 没有 tool_call，让模型重试
            if retry_count < max_retries:
                messages.append({
                    "role": "assistant",
                    "content": message.get("content", ""),
                })
                messages.append({
                    "role": "user",
                    "content": f"你必须调用工具 {tool_name}，请直接发起 tool_call。",
                })
                retry_count += 1
                continue
            else:
                return RunResult(
                    ok=False,
                    tool=tool_name,
                    run_id=f"{tool_name}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}",
                    command="",
                    started_at=datetime.now(timezone.utc),
                    ended_at=datetime.now(timezone.utc),
                    runtime_sec=0.0,
                    stderr_tail="No tool_call generated after retries",
                )
        
        # 检查第一个 tool_call 是否匹配期望的工具
        first_tool_call = tool_calls[0]
        called_tool_name = first_tool_call["function"]["name"]
        
        if called_tool_name != tool_name:
            # 工具名不匹配，纠错
            if retry_count < max_retries:
                messages.append({
                    "role": "assistant",
                    "content": message.get("content", ""),
                    "tool_calls": tool_calls,
                })
                messages.append({
                    "role": "user",
                    "content": f"下一步必须调用 {tool_name}，请仅调用该工具并使用给定 args。",
                })
                retry_count += 1
                continue
            else:
                return RunResult(
                    ok=False,
                    tool=tool_name,
                    run_id=f"{tool_name}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}",
                    command="",
                    started_at=datetime.now(timezone.utc),
                    ended_at=datetime.now(timezone.utc),
                    runtime_sec=0.0,
                    stderr_tail=f"Wrong tool called: {called_tool_name} (expected: {tool_name})",
                )
        
        # 解析参数（以 plan 为准）
        try:
            model_args = json.loads(first_tool_call["function"]["arguments"])
        except json.JSONDecodeError:
            model_args = {}
        
        # 以 plan 为准覆盖参数（仅使用 plan 中的 args，不混入内部字段）
        tool_args = dict(step_config.args)  # 仅此一份，严格来自 plan
        
        # 记录参数覆盖信息到 RunResult（不传入工具函数）
        notes = []
        if model_args != tool_args:
            notes.append("model_args_overridden")
        
        # 执行工具（只传 plan 中的 args）
        run_result = _call_tool(tool_name, tool_args, dry_run=dry_run)
        
        # 将 notes 写入 RunResult（不污染工具参数）
        if notes:
            if "notes" not in run_result.metrics:
                run_result.metrics["notes"] = []
            if isinstance(run_result.metrics["notes"], list):
                run_result.metrics["notes"].extend(notes)
        
        # 检查 expected_artifacts
        run_result = _check_expected_artifacts(
            run_result,
            step_config.expected_artifacts,
            full_mode=not dry_run,
        )
        
        return run_result
    
    # 不应该到达这里
    return RunResult(
        ok=False,
        tool=tool_name,
        run_id=f"{tool_name}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}",
        command="",
        started_at=datetime.now(timezone.utc),
        ended_at=datetime.now(timezone.utc),
        runtime_sec=0.0,
        stderr_tail="Max retries exceeded",
    )


def execute_plan(
    plan_path: str,
    log_path: str = "outputs/experiment_log.jsonl",
    dry_run: bool = True,
    max_turns: int = 30,
    thinking: bool = True,
    base_url: str = "https://api.deepseek.com",
    model: str = "deepseek-chat",
    full_first_k: Optional[int] = None,
) -> bool:
    """执行 ExperimentPlan"""
    
    print("=" * 80)
    print("Execute ExperimentPlan")
    print("=" * 80)
    print(f"Plan: {plan_path}")
    print(f"Log: {log_path}")
    print(f"Mode: {'DRY-RUN' if dry_run else 'FULL'}")
    print(f"Thinking: {thinking}")
    print()
    
    # 加载计划
    plan_data = json.loads(Path(plan_path).read_text(encoding="utf-8"))
    plan = ExperimentPlan.model_validate(plan_data)
    
    print(f"Plan loaded: {len(plan.runs)} runs")
    print(f"  Hypotheses: {len(plan.hypotheses)}")
    print(f"  Metrics: {len(plan.metrics_definition)}")
    print()
    
    # 准备日志文件
    log_file = Path(log_path)
    log_file.parent.mkdir(parents=True, exist_ok=True)
    
    # 获取工具定义（不含 ping，生产工具）
    tools = get_tools(include_test=False)
    
    # 初始化客户端（如果非 dry-run）
    client = None
    if not dry_run:
        try:
            client = _get_deepseek_client(base_url=base_url)
        except (ValueError, ImportError) as e:
            print(f"[ERROR] Failed to initialize client: {e}")
            print("  Set DEEPSEEK_API_KEY or use --dry-run mode")
            return False
    
    # 执行每个步骤（如果指定了 full_first_k，只执行前 k 步）
    runs_to_execute = plan.runs
    if not dry_run and full_first_k is not None:
        runs_to_execute = plan.runs[:full_first_k]
        print(f"  [INFO] Executing first {full_first_k} steps only")
    
    all_passed = True
    
    for i, step_config in enumerate(runs_to_execute):
        print(f"[{i+1}/{len(runs_to_execute)}] Executing: {step_config.tool_name}")
        
        if dry_run:
            # Dry-run：直接生成模拟结果
            run_result = _call_tool(step_config.tool_name, step_config.args, dry_run=True)
            
            # 检查 expected_artifacts 路径规范（不强求存在）
            for artifact_path in step_config.expected_artifacts:
                artifact_path_obj = Path(artifact_path)
                if artifact_path_obj.parent.exists():
                    print(f"  [DRY-RUN] Expected artifact path check: {artifact_path}")
                else:
                    print(f"  [DRY-RUN] Warning: artifact path parent missing: {artifact_path}")
            
        else:
            # Full 模式：使用 LLM 执行
            run_result = _execute_step_with_llm(
                client=client,
                tools=tools,
                step_config=step_config,
                step_index=i,
                total_steps=len(plan.runs),
                dry_run=False,
                thinking=thinking,
                model=model,
            )
        
        # 写入日志
        append_jsonl(log_path, run_result)
        
        # 检查结果
        if run_result.ok:
            print(f"  [OK] {step_config.tool_name}")
        else:
            print(f"  [FAIL] {step_config.tool_name}: {_safe_text(run_result.stderr_tail)}")
            all_passed = False
        
        # 如果失败且不是 dry-run，可以选择继续或停止
        if not run_result.ok and not dry_run:
            print(f"  [WARN] Step {i+1} failed, continuing...")
    
    print()
    print("=" * 80)
    if all_passed:
        print("[OK] All steps completed successfully")
    else:
        print("[WARN] Some steps failed (check log for details)")
    print(f"Log file: {log_path}")
    print("=" * 80)
    
    return all_passed


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="Execute ExperimentPlan")
    parser.add_argument("--plan", type=str, default="plans/plan.json", help="ExperimentPlan JSON path")
    parser.add_argument("--log", type=str, default="outputs/experiment_log.jsonl", help="Log file path")
    parser.add_argument("--dry-run", action="store_true", help="Dry-run mode (default if --full not set)")
    parser.add_argument("--full", action="store_true", help="Full execution mode")
    parser.add_argument("--max_turns", type=int, default=30, help="Max turns per step")
    parser.add_argument("--thinking", type=str, default="true", help="Enable thinking (true/false)")
    parser.add_argument("--base_url", type=str, default="https://api.deepseek.com", help="API base URL")
    parser.add_argument("--model", type=str, default="deepseek-chat", help="Model name")
    parser.add_argument("--full-first-k", type=int, default=None, help="In --full mode, only execute first k steps")
    
    args = parser.parse_args()
    
    # 解析 dry-run 和 thinking（默认 dry-run=True，除非显式指定 --full）
    dry_run = not args.full
    thinking = args.thinking.lower() in ("true", "1", "yes", "on")
    
    success = execute_plan(
        plan_path=args.plan,
        log_path=args.log,
        dry_run=dry_run,
        max_turns=args.max_turns,
        thinking=thinking,
        base_url=args.base_url,
        model=args.model,
        full_first_k=args.full_first_k,
    )
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
