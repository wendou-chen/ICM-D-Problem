"""
统一数据结构定义，供 runner.py / tools_impl.py / agent_exec.py / writer.py 使用。

Schema Contract：所有输出必须有合同，使用 Pydantic v2 进行数据验证。
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


# ============================================================================
# Enum / Literal 定义
# ============================================================================

class ArtifactType(str, Enum):
    """产物类型枚举"""
    TABLE = "table"
    PLOT = "plot"
    LOG = "log"
    MODEL = "model"
    CONFIG = "config"
    OTHER = "other"


ToolName = Literal[
    "run_etl",
    "build_graph",
    "run_baseline",
    "run_task2",
    "run_task2_ablation",
    "analyze_task2_ablation",
    "sensitivity",
    "attack_nodes",
    "run_robustness"
]


# ============================================================================
# 核心模型定义
# ============================================================================

class Artifact(BaseModel):
    """产物定义：实验输出的文件/数据"""
    path: str
    type: ArtifactType
    desc: str
    
    # 可选增强字段
    sha256: Optional[str] = None
    bytes: Optional[int] = None
    mime: Optional[str] = None


class RunResult(BaseModel):
    """运行结果：单次工具执行的完整记录"""
    ok: bool
    tool: str
    run_id: str
    command: str
    started_at: datetime
    ended_at: datetime
    runtime_sec: float
    stdout_tail: str = Field(default="", description="标准输出尾部内容")
    stderr_tail: str = Field(default="", description="标准错误尾部内容")
    artifacts: List[Artifact] = Field(default_factory=list)
    metrics: Dict[str, Any] = Field(default_factory=dict)
    paper_hooks: Dict[str, str] = Field(default_factory=dict)
    provenance: Dict[str, Any] = Field(default_factory=dict)
    
    def to_json(self, indent: int = 2) -> str:
        """转换为JSON字符串"""
        return self.model_dump_json(indent=indent)
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return self.model_dump()


class StepConfig(BaseModel):
    """步骤配置：单个实验步骤的参数"""
    tool_name: ToolName
    args: Dict[str, Any] = Field(default_factory=dict)
    expected_artifacts: List[str] = Field(default_factory=list)
    
    # 可选增强字段
    acceptance_test: Optional[str] = None


class ExperimentPlan(BaseModel):
    """实验计划：完整的实验设计"""
    hypotheses: List[str] = Field(default_factory=list)
    metrics_definition: Dict[str, str] = Field(default_factory=dict)
    runs: List[StepConfig] = Field(default_factory=list)
    ablations: List[Dict[str, Any]] = Field(default_factory=list)
    robustness_strategy: Dict[str, Any] = Field(default_factory=dict)
    paper_map: Dict[str, str] = Field(default_factory=dict)
