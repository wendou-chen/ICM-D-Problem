"""
DeepSeek-Chat 工具调用闭环执行器。

支持两种模式：
- --self-test: 使用 ping 工具验证 tool-loop
- --plan <path>: 读取 ExperimentPlan 并逐步执行（Step4 用）
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from runner import append_jsonl
from schema import ExperimentPlan, RunResult
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

# 尝试导入 OpenAI SDK
try:
    from openai import OpenAI
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False
    # 如果 OpenAI SDK 不可用，使用 requests
    try:
        import requests
        HAS_REQUESTS = True
    except ImportError:
        HAS_REQUESTS = False


def _get_deepseek_client() -> Any:
    """获取 DeepSeek API 客户端"""
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        raise ValueError("DEEPSEEK_API_KEY environment variable not set")
    
    base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    
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


def _call_tool(tool_name: str, arguments: Dict[str, Any]) -> RunResult:
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
        from datetime import datetime, timezone
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
    
    func = tool_map[tool_name]
    try:
        return func(**arguments)
    except Exception as e:
        from datetime import datetime, timezone
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


def _run_tool_loop(
    client: Any,
    tools: List[dict],
    system_prompt: str,
    user_prompt: str,
    max_turns: int = 10,
    log_path: str = "experiment_log.jsonl",
) -> Dict[str, Any]:
    """执行工具调用闭环"""
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    
    turn = 0
    all_results = []
    
    while turn < max_turns:
        turn += 1
        
        # 调用 LLM
        if HAS_OPENAI:
            response = client.chat.completions.create(
                model=os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
                messages=messages,
                tools=tools,
                tool_choice="auto",
            )
            response_dict = response.model_dump()
        else:
            # requests 客户端
            response_dict = client.chat(
                model=os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
                messages=messages,
                tools=tools,
                tool_choice="auto",
            )
        
        # 提取 assistant 消息
        choice = response_dict["choices"][0]
        message = choice["message"]
        
        # 处理 reasoning（如果有）
        if "reasoning_content" in message:
            # 写入本地日志文件（不进入 messages）
            reasoning_path = Path("outputs/agent/reasoning") / f"step_{turn}.txt"
            reasoning_path.parent.mkdir(parents=True, exist_ok=True)
            reasoning_path.write_text(message["reasoning_content"], encoding="utf-8")
        
        # 添加到 messages
        messages.append({
            "role": "assistant",
            "content": message.get("content", ""),
            "tool_calls": message.get("tool_calls", []),
        })
        
        # 如果没有 tool_calls，结束
        if not message.get("tool_calls"):
            break
        
        # 执行每个 tool_call
        for tool_call in message["tool_calls"]:
            tool_name = tool_call["function"]["name"]
            try:
                arguments = json.loads(tool_call["function"]["arguments"])
            except json.JSONDecodeError:
                arguments = {}
            
            # 调用工具
            result = _call_tool(tool_name, arguments)
            all_results.append(result)
            
            # 记录到 JSONL
            append_jsonl(log_path, result)
            
            # 回灌 tool 输出
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call["id"],
                "content": result.to_json(indent=None),  # 单行 JSON
            })
    
    return {
        "turns": turn,
        "results": all_results,
        "final_message": messages[-1] if messages else None,
    }


def self_test(log_path: str = "experiment_log.jsonl") -> bool:
    """运行 self-test（使用 ping 工具）"""
    print("=" * 80)
    print("Step3 Self-Test: Tool-Loop Verification")
    print("=" * 80)
    
    # 检查 API key
    if not os.getenv("DEEPSEEK_API_KEY"):
        print("[WARN]  DEEPSEEK_API_KEY not set, skipping API call")
        print("   设置方法: $env:DEEPSEEK_API_KEY='your-key'")
        return False
    
    try:
        client = _get_deepseek_client()
    except Exception as e:
        print(f"[ERROR] Failed to initialize client: {e}")
        return False
    
    # 获取工具定义（包含 ping）
    tools = get_tools(include_test=True)
    
    # 设置提示词
    system_prompt = "你是实验编排器，只能通过工具完成任务；现在必须调用一次 ping(message='step3')，然后给出简短完成 JSON"
    user_prompt = "请调用 ping 并结束"
    
    # 运行 tool-loop
    try:
        result = _run_tool_loop(
            client=client,
            tools=tools,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_turns=5,
            log_path=log_path,
        )
        
        # 检查是否成功调用了 ping
        ping_called = any(
            r.tool == "ping" and r.ok for r in result["results"]
        )
        
        if ping_called:
            print("[OK] Self-test passed: ping tool called successfully")
            print(f"   Turns: {result['turns']}")
            print(f"   Results: {len(result['results'])}")
            return True
        else:
            print("[ERROR] Self-test failed: ping tool not called or failed")
            return False
            
    except Exception as e:
        print(f"[ERROR] Self-test error: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_plan(plan_path: str, log_path: str = "experiment_log.jsonl") -> bool:
    """运行 ExperimentPlan（Step4 用）"""
    print("=" * 80)
    print(f"Running ExperimentPlan: {plan_path}")
    print("=" * 80)
    
    # 加载计划
    plan_data = json.loads(Path(plan_path).read_text(encoding="utf-8"))
    plan = ExperimentPlan(**plan_data)
    
    # TODO: Step4 实现
    print("[WARN]  Plan execution not implemented in Step3")
    return False


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="DeepSeek-Chat Tool-Loop Executor")
    parser.add_argument("--self-test", action="store_true", help="Run self-test with ping")
    parser.add_argument("--plan", type=str, help="Path to ExperimentPlan JSON")
    parser.add_argument("--log", type=str, default="experiment_log.jsonl", help="Log file path")
    
    args = parser.parse_args()
    
    if args.self_test:
        success = self_test(log_path=args.log)
        sys.exit(0 if success else 1)
    elif args.plan:
        success = run_plan(args.plan, log_path=args.log)
        sys.exit(0 if success else 1)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
