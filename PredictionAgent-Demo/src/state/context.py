"""
Agent上下文
用于在线程/协程间共享状态
"""

from dataclasses import dataclass, field
from typing import Optional, Any
from threading import local

from .state import State


@dataclass
class AgentContext:
    """Agent执行上下文"""
    request_id: str = ""
    state: Optional[State] = None
    metadata: dict = field(default_factory=dict)

    def set(self, key: str, value: Any):
        """设置元数据"""
        self.metadata[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        """获取元数据"""
        return self.metadata.get(key, default)


# 线程本地存储
_thread_local = local()


def get_current_context() -> Optional[AgentContext]:
    """获取当前上下文"""
    return getattr(_thread_local, 'context', None)


def set_current_context(context: AgentContext):
    """设置当前上下文"""
    _thread_local.context = context


def clear_current_context():
    """清除当前上下文"""
    if hasattr(_thread_local, 'context'):
        del _thread_local.context
