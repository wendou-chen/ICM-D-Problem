"""
Speciale 计划器：调用 OpenRouter 的 Speciale 模型生成实验计划 JSON。

支持在线（OpenRouter API）和离线（stub 计划）两种模式。

Notes:
- 支持注入 human prior（--prior），以强制硬约束与产物路径。
- 默认 base_url 为 OpenRouter ChatCompletions 端点前缀（--base_url），避免硬编码。
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional

# 尝试加载 .env 中的环境变量（不回显内容）
try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:
    # python-dotenv 未安装时静默跳过
    pass

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

from pydantic import ValidationError

from schema import ExperimentPlan, StepConfig

# 可选：PDF 解析（用于从题面 PDF 中提取文本）
try:
    from pypdf import PdfReader  # 推荐的新库名
    HAS_PDF = True
except ImportError:  # pragma: no cover - 环境可能没装 pypdf
    try:
        from PyPDF2 import PdfReader  # 兼容旧库名
        HAS_PDF = True
    except ImportError:
        HAS_PDF = False


def get_stub_plan() -> Dict[str, Any]:
    """生成离线模式的最小可用计划 stub"""
    return {
        "hypotheses": [
            "假设1：在关键节点增加公交线路可以显著提高网络可达性",
            "假设2：混合优化算法（PSO+GA）比单一算法能获得更好的解",
            "假设3：网络对随机攻击的鲁棒性优于针对性攻击"
        ],
        "metrics_definition": {
            "reachable_ratio": "可达OD对比例",
            "mean_cost": "平均路径成本",
            "total_objective": "总目标函数值",
            "unreachable_count": "不可达OD对数量"
        },
        "runs": [
            {
                "tool_name": "run_etl",
                "args": {
                    "raw_dir": "data/raw",
                    "out_dir": "data/processed",
                    "strict": True,
                    "random_seed": 42
                },
                "expected_artifacts": [
                    "data/processed/nodes_clean.csv",
                    "data/processed/edges_clean.csv",
                    "data/processed/bus_stops_clean.csv"
                ],
                "acceptance_test": "检查 *_clean.csv 文件存在且非空"
            },
            {
                "tool_name": "build_graph",
                "args": {
                    "processed_dir": "data/processed",
                    "graph_out": "data/processed/graph.pkl",
                    "export": True
                },
                "expected_artifacts": [
                    "data/processed/graph.pkl",
                    "data/processed/graph_nodes.csv",
                    "data/processed/graph_edges.csv"
                ],
                "acceptance_test": "检查 graph.pkl 存在且可加载"
            },
            {
                "tool_name": "run_baseline",
                "args": {
                    "graph_pkl": "data/processed/graph.pkl",
                    "od_samples": 100,
                    "metrics": ["reachable_ratio", "mean_cost"],
                    "out_dir": "outputs/baseline"
                },
                "expected_artifacts": [
                    "outputs/baseline/baseline_metrics.csv",
                    "outputs/baseline/baseline_report.md"
                ],
                "acceptance_test": "检查 baseline_metrics.csv 存在且包含 reachable_ratio 字段"
            },
            {
                "tool_name": "run_task2",
                "args": {
                    "random_seed": 42,
                    "out_dir": "outputs/task2",
                    "mode": "normal"
                },
                "expected_artifacts": [
                    "outputs/task2/best_solution.json",
                    "outputs/task2/metrics.csv",
                    "outputs/task2/convergence_history.csv"
                ],
                "acceptance_test": "检查 best_solution.json 存在且 reachable_ratio >= 0.8"
            },
            {
                "tool_name": "sensitivity",
                "args": {
                    "base_run_dir": "outputs/task2",
                    "delta": 0.1,
                    "trials": 5,
                    "what": "cost",
                    "out_dir": "outputs/task2/sensitivity"
                },
                "expected_artifacts": [
                    "outputs/task2/sensitivity/sensitivity_table.csv"
                ],
                "acceptance_test": "检查 sensitivity_table.csv 存在"
            },
            {
                "tool_name": "attack_nodes",
                "args": {
                    "graph_pkl": "data/processed/graph.pkl",
                    "k_list": [5, 10, 15, 20],
                    "centrality": "betweenness",
                    "recompute_metric": True,
                    "out_dir": "outputs/task2/attack"
                },
                "expected_artifacts": [
                    "outputs/task2/attack/attack_results.csv"
                ],
                "acceptance_test": "检查 attack_results.csv 存在"
            }
        ],
        "ablations": [
            {
                "name": "算法对比",
                "runs": [
                    {"tool_name": "run_task2", "args": {"mode": "pso_only"}},
                    {"tool_name": "run_task2", "args": {"mode": "ga_only"}},
                    {"tool_name": "run_task2", "args": {"mode": "hybrid"}}
                ]
            },
            {
                "name": "预算敏感性",
                "runs": [
                    {"tool_name": "run_task2", "args": {"budget": 1000000}},
                    {"tool_name": "run_task2", "args": {"budget": 2000000}},
                    {"tool_name": "run_task2", "args": {"budget": 3000000}}
                ]
            }
        ],
        "robustness_strategy": {
            "sensitivity": {
                "description": "成本参数 ±10% 扰动",
                "delta": 0.1,
                "trials": 5
            },
            "attack_nodes": {
                "description": "top-k 节点移除曲线",
                "k_list": [5, 10, 15, 20, 25],
                "centrality": "betweenness"
            }
        },
        "paper_map": {
            "run_etl": "Section 3.1: 数据预处理与清洗",
            "build_graph": "Section 3.2: 网络图构建",
            "run_baseline": "Section 4.1: 基线性能评估",
            "run_task2": "Section 4.2: 公交线路优化设计",
            "sensitivity": "Section 5.1: 参数敏感性分析",
            "attack_nodes": "Section 5.2: 网络鲁棒性分析"
        }
    }


def load_problem_text(problem_path: Path, max_chars: int = 16000) -> str:
    """
    从题面文件中提取文本。
    
    支持：
    - .pdf：使用 pypdf / PyPDF2 提取全部页面文本
    - 其他（.txt/.md/...）：按 UTF-8 文本读取
    
    会自动截断到 max_chars 长度，避免 prompt 过长。
    """
    if not problem_path.exists():
        print(f"[警告] 问题文件未找到: {problem_path}", file=sys.stderr)
        return ""
    
    text = ""
    if problem_path.suffix.lower() == ".pdf":
        if not HAS_PDF:
            print(
                "[警告] 未安装 pypdf / PyPDF2；无法从 PDF 提取文本。"
                "请安装: pip install pypdf",
                file=sys.stderr,
            )
            return ""
        try:
            reader = PdfReader(str(problem_path))
            pages = []
            for page in reader.pages:
                content = page.extract_text() or ""
                pages.append(content)
            text = "\n\n".join(pages)
        except Exception as e:  # pragma: no cover - I/O/解析异常
            print(f"[警告] 从 PDF 提取文本失败 {problem_path}: {e}", file=sys.stderr)
            return ""
    else:
        try:
            text = problem_path.read_text(encoding="utf-8", errors="ignore")
        except Exception as e:
            print(f"[警告] 读取问题文件失败 {problem_path}: {e}", file=sys.stderr)
            return ""
    
    text = text.strip()
    if not text:
        return ""
    
    if len(text) > max_chars:
        return text[:max_chars] + "\n\n[已截断: 问题文本已缩短以适应提示长度]"
    return text


def call_openrouter_speciale(
    api_key: str,
    model: str = "deepseek/deepseek-v3.2-speciale",
    base_url: str = "https://openrouter.ai/api/v1",
    zdr: bool = True,
    timeout_sec: int = 120,
    messages: list = None
) -> Dict[str, Any]:
    """调用 OpenRouter Speciale API"""
    if not HAS_REQUESTS:
        raise ImportError("需要 requests 库。请安装: pip install requests>=2")
    
    url = base_url.rstrip("/") + "/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    
    body: Dict[str, Any] = {
        "model": model,
        "messages": messages or [],
    }
    
    if zdr:
        body["provider"] = {"zdr": True}
    
    response = requests.post(url, json=body, headers=headers, timeout=timeout_sec)
    response.raise_for_status()
    return response.json()


def extract_json_from_content(content: str) -> Optional[Dict[str, Any]]:
    """从响应内容中提取 JSON（去除 Markdown 代码块）"""
    content = content.strip()
    
    # 移除 Markdown 代码块标记
    if content.startswith("```json"):
        content = content[7:]
    elif content.startswith("```"):
        content = content[3:]
    
    if content.endswith("```"):
        content = content[:-3]
    
    content = content.strip()
    
    # 找到第一个 { 和最后一个 }
    start_idx = content.find("{")
    end_idx = content.rfind("}")
    
    if start_idx == -1 or end_idx == -1 or start_idx >= end_idx:
        return None
    
    json_str = content[start_idx:end_idx + 1]
    
    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        return None


def generate_plan_online(
    api_key: str,
    model: str = "deepseek/deepseek-v3.2-speciale",
    base_url: str = "https://openrouter.ai/api/v1",
    zdr: bool = True,
    timeout_sec: int = 120,
    max_attempts: int = 3,
    prior_text: str = "",
    problem_text: str = "",
) -> Dict[str, Any]:
    """在线生成计划（带自动修复）"""
    
    system_prompt = """你是运筹学与复杂网络审稿人。你只能输出"裸 JSON"，首字符必须是 {，末字符必须是 }，禁止 Markdown 代码块，禁止多余解释。"""
    
    problem_block = ""
    if problem_text.strip():
        problem_block = f"\n\n【PROBLEM STATEMENT（题面摘要，需对齐此描述）】\n{problem_text.strip()}\n"
    prior_block = ""
    if prior_text.strip():
        prior_block = f"\n\n【HUMAN PRIOR（硬约束，必须遵守）】\n{prior_text.strip()}\n"
    user_prompt = (
        f"""请为 ICM D 题构建 O 奖级"建模+算法+鲁棒性"实验链。

工具列表：run_etl, build_graph, run_baseline, run_task2, sensitivity, attack_nodes

必须输出 JSON 字段（与 schema.py 对齐）：
- hypotheses（>=3，可证伪）
- metrics_definition（KPI 口径）
- runs（按顺序：tool_name + args + expected_artifacts + acceptance_test）
- ablations（>=2 组）
- robustness_strategy（必须包含 sensitivity 与 attack_nodes 设计）
- paper_map（每一步对应论文小节与图表标题草案）

强制约束：
- runs 第一步必须是 run_etl，第二步 build_graph，第三步 run_baseline
- robustness 中必须包含 ±10% 扰动和 top-k 节点移除曲线
- 产物路径必须使用 outputs/task2/*, outputs/task2/sensitivity/*, outputs/task2/attack/*（不要写 outputs/2024/...）
- run_task2 不要传 config_path（工具实现不支持，会失败）

请输出 ExperimentPlan JSON（裸 JSON，不要 Markdown 代码块）。"""
        + problem_block
        + prior_block
    )
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]
    
    for attempt in range(max_attempts):
        try:
            # 调用 API
            response = call_openrouter_speciale(
                api_key=api_key,
                model=model,
                base_url=base_url,
                zdr=zdr,
                timeout_sec=timeout_sec,
                messages=messages
            )
            
            # 提取内容
            content = response["choices"][0]["message"]["content"]
            
            # 解析 JSON
            plan_dict = extract_json_from_content(content)
            
            if plan_dict is None:
                raise ValueError("从响应中提取 JSON 失败")
            
            # 校验
            plan = ExperimentPlan.model_validate(plan_dict)
            
            # 成功
            return plan.model_dump()
            
        except (ValueError, json.JSONDecodeError, KeyError) as e:
            error_msg = str(e)
            if attempt < max_attempts - 1:
                # 追加修复请求
                messages.append({
                    "role": "assistant",
                    "content": content if 'content' in locals() else ""
                })
                messages.append({
                    "role": "user",
                    "content": f"你的输出不是合法的 ExperimentPlan JSON，错误如下：{error_msg} 请仅返回修复后的裸 JSON，不要解释。"
                })
            else:
                # 最后一次尝试失败
                print(f"[错误] 经过 {max_attempts} 次尝试后仍无法生成有效计划", file=sys.stderr)
                print(f"[错误] 最后错误: {error_msg}", file=sys.stderr)
                if 'content' in locals():
                    print(f"[错误] 最后响应: {content[:500]}", file=sys.stderr)
                sys.exit(1)
        except ValidationError as e:
            error_msg = f"验证错误: {str(e)}"
            if attempt < max_attempts - 1:
                messages.append({
                    "role": "assistant",
                    "content": content if 'content' in locals() else ""
                })
                messages.append({
                    "role": "user",
                    "content": f"你的输出不是合法的 ExperimentPlan JSON，错误如下：{error_msg} 请仅返回修复后的裸 JSON，不要解释。"
                })
            else:
                print(f"[错误] 经过 {max_attempts} 次尝试后仍无法验证计划", file=sys.stderr)
                print(f"[错误] 验证错误: {e.errors()}", file=sys.stderr)
                sys.exit(1)
        except Exception as e:
            print(f"[错误] 意外错误: {e}", file=sys.stderr)
            sys.exit(1)
    
    # 不应该到达这里
    sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Speciale 计划器：生成实验计划 JSON")
    parser.add_argument("--out", type=str, default="plans/plan.json", help="输出路径")
    parser.add_argument("--max_attempts", type=int, default=3, help="JSON 修复最大轮数")
    parser.add_argument("--zdr", type=str, default="true", help="是否启用 OpenRouter provider.zdr")
    parser.add_argument("--model", type=str, default="deepseek/deepseek-v3.2-speciale", help="模型名称")
    parser.add_argument("--base_url", type=str, default="https://openrouter.ai/api/v1", help="OpenRouter base_url（例如 https://openrouter.ai/api/v1）")
    parser.add_argument("--timeout_sec", type=int, default=120, help="API 超时时间（秒）")
    parser.add_argument("--offline", type=str, default="auto", help="离线模式（auto/true/false）")
    parser.add_argument("--prior", type=str, default="", help="human prior 文件路径（会注入到 prompt 作为硬约束）")
    parser.add_argument(
        "--problem",
        type=str,
        default="",
        help="ICM 题面文件路径（支持 .pdf/.txt/.md；内容将作为 PROBLEM STATEMENT 注入 prompt）",
    )
    
    args = parser.parse_args()
    
    # 解析 zdr 和 offline
    zdr = args.zdr.lower() in ("true", "1", "yes")
    offline = args.offline.lower() in ("true", "1", "yes")
    
    # 检查 API key
    api_key = os.getenv("OPENROUTER_API_KEY")
    if args.offline.lower() == "auto" and not api_key:
        offline = True
    
    # 生成计划
    if offline or not api_key:
        print("[信息] 运行在离线模式", file=sys.stderr)
        plan_dict = get_stub_plan()
    else:
        print("[信息] 运行在在线模式", file=sys.stderr)
        prior_text = ""
        if args.prior:
            prior_path = Path(args.prior)
            if prior_path.exists():
                prior_text = prior_path.read_text(encoding="utf-8")
            else:
                print(f"[警告] prior 文件未找到: {prior_path}", file=sys.stderr)
        problem_text = ""
        if args.problem:
            problem_path = Path(args.problem)
            problem_text = load_problem_text(problem_path)
        plan_dict = generate_plan_online(
            api_key=api_key,
            model=args.model,
            base_url=args.base_url,
            zdr=zdr,
            timeout_sec=args.timeout_sec,
            max_attempts=args.max_attempts,
            prior_text=prior_text,
            problem_text=problem_text,
        )
    
    # 校验
    plan = ExperimentPlan.model_validate(plan_dict)
    
    # 写入文件
    output_path = Path(args.out)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(plan.model_dump(), f, indent=2, ensure_ascii=False)
    
    # stdout 只输出一行成功标识（不带 [ ] 前缀）
    mode_str = "OFFLINE_OK" if (offline or not api_key) else "OK"
    print(f"{mode_str}: 计划已写入 {output_path}")


if __name__ == "__main__":
    main()

