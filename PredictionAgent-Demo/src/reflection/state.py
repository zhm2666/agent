"""
反思状态管理
定义反思、重试、验证相关的状态数据
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum


class ErrorType(Enum):
    """错误类型枚举"""
    # 产品识别错误
    PRODUCT_NOT_FOUND = "product_not_found"
    PRODUCT_AMBIGUOUS = "product_ambiguous"
    PRODUCT_MISIDENTIFIED = "product_misidentified"

    # 数据获取错误
    DATA_NOT_FOUND = "data_not_found"
    DATA_INSUFFICIENT = "data_insufficient"
    DATA_INVALID = "data_invalid"

    # 图表生成错误
    CHART_GENERATION_FAILED = "chart_generation_failed"
    CHART_RENDERING_ERROR = "chart_rendering_error"

    # 分析错误
    ANALYSIS_INVALID = "analysis_invalid"
    ANALYSIS_INCOMPLETE = "analysis_incomplete"
    ANALYSIS_INCONSISTENT = "analysis_inconsistent"

    # 通用错误
    UNKNOWN_ERROR = "unknown_error"
    TIMEOUT = "timeout"
    VALIDATION_FAILED = "validation_failed"


class RetryAction(Enum):
    """重试动作枚举"""
    REIDENTIFY_PRODUCT = "reidentify_product"
    REFETCH_DATA = "refetch_data"
    REGENERATE_CHART = "regenerate_chart"
    REANALYZE = "reanalyze"
    USE_FALLBACK = "use_fallback"
    ASK_USER = "ask_user"
    SKIP_STEP = "skip_step"


@dataclass
class ValidationResult:
    """验证结果"""
    is_valid: bool = True
    score: float = 1.0  # 0-1之间的置信度分数
    error_type: Optional[ErrorType] = None
    error_message: str = ""
    suggestions: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "score": self.score,
            "error_type": self.error_type.value if self.error_type else None,
            "error_message": self.error_message,
            "suggestions": self.suggestions,
            "metadata": self.metadata
        }


@dataclass
class RetryStrategy:
    """重试策略"""
    max_retries: int = 3  # 最大重试次数
    current_attempts: int = 0  # 当前尝试次数
    backoff_multiplier: float = 2.0  # 退避倍数
    initial_delay: float = 1.0  # 初始延迟（秒）

    # 特定步骤的重试配置
    step_configs: Dict[str, Dict[str, Any]] = field(default_factory=lambda: {
        "product_identification": {
            "max_retries": 2,
            "fallback_action": RetryAction.ASK_USER,
            "validate_after": True
        },
        "data_fetch": {
            "max_retries": 3,
            "fallback_action": RetryAction.USE_FALLBACK,
            "validate_after": True
        },
        "chart_generation": {
            "max_retries": 2,
            "fallback_action": RetryAction.SKIP_STEP,
            "validate_after": True
        },
        "analysis": {
            "max_retries": 2,
            "fallback_action": RetryAction.REFETCH_DATA,
            "validate_after": True
        }
    })

    def should_retry(self, step: str) -> bool:
        """检查是否应该重试"""
        config = self.step_configs.get(step, {"max_retries": 1})
        return self.current_attempts < config.get("max_retries", self.max_retries)

    def get_fallback_action(self, step: str) -> RetryAction:
        """获取回退动作"""
        config = self.step_configs.get(step, {})
        action_str = config.get("fallback_action", RetryAction.SKIP_STEP)
        if isinstance(action_str, str):
            return RetryAction(action_str)
        return action_str

    def increment_attempts(self):
        """增加尝试次数"""
        self.current_attempts += 1

    def reset(self):
        """重置重试计数器"""
        self.current_attempts = 0

    def get_delay(self) -> float:
        """获取延迟时间（指数退避）"""
        return self.initial_delay * (self.backoff_multiplier ** self.current_attempts)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "max_retries": self.max_retries,
            "current_attempts": self.current_attempts,
            "backoff_multiplier": self.backoff_multiplier,
            "initial_delay": self.initial_delay,
            "step_configs": self.step_configs
        }


@dataclass
class ReflectionRecord:
    """反思记录"""
    step: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    input_data: Dict[str, Any] = field(default_factory=dict)
    output_data: Dict[str, Any] = field(default_factory=dict)
    validation: Optional[ValidationResult] = None
    retry_count: int = 0
    final_action: str = ""
    notes: str = ""


@dataclass
class ReflectionState:
    """反思状态"""
    enabled: bool = True
    reflection_count: int = 0
    max_reflections: int = 5  # 最大反思次数

    # 反思记录
    records: List[ReflectionRecord] = field(default_factory=list)

    # 当前验证结果
    current_validation: Optional[ValidationResult] = None

    # 重试策略
    retry_strategy: RetryStrategy = field(default_factory=RetryStrategy)

    # 是否正在进行反思
    is_reflecting: bool = False

    # 反思历史摘要
    reflection_summary: List[str] = field(default_factory=list)

    def start_reflection(self):
        """开始反思"""
        self.is_reflecting = True
        self.reflection_count += 1

    def end_reflection(self):
        """结束反思"""
        self.is_reflecting = False

    def add_record(self, record: ReflectionRecord):
        """添加反思记录"""
        self.records.append(record)

    def can_continue_reflection(self) -> bool:
        """是否可以继续反思"""
        return self.reflection_count < self.max_reflections

    def add_summary(self, summary: str):
        """添加反思摘要"""
        self.reflection_summary.append(summary)

    def get_last_record(self) -> Optional[ReflectionRecord]:
        """获取最后一条记录"""
        return self.records[-1] if self.records else None

    def get_failed_steps(self) -> List[str]:
        """获取失败的步骤"""
        failed = []
        for record in self.records:
            if record.validation and not record.validation.is_valid:
                failed.append(record.step)
        return failed

    def to_dict(self) -> Dict[str, Any]:
        return {
            "enabled": self.enabled,
            "reflection_count": self.reflection_count,
            "max_reflections": self.max_reflections,
            "records": [
                {
                    "step": r.step,
                    "timestamp": r.timestamp,
                    "retry_count": r.retry_count,
                    "final_action": r.final_action,
                    "validation": r.validation.to_dict() if r.validation else None,
                    "notes": r.notes
                }
                for r in self.records
            ],
            "current_validation": self.current_validation.to_dict() if self.current_validation else None,
            "retry_strategy": self.retry_strategy.to_dict(),
            "is_reflecting": self.is_reflecting,
            "reflection_summary": self.reflection_summary
        }


def update_state_with_reflection(
    state: "State",
    reflection_state: ReflectionState
) -> "State":
    """
    将反思状态更新到主状态中

    Args:
        state: 主状态
        reflection_state: 反思状态

    Returns:
        更新后的主状态
    """
    if hasattr(state, 'reflection'):
        state.reflection = reflection_state
    return state
