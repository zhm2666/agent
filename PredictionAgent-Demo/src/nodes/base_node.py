"""
节点基类
"""

from abc import ABC, abstractmethod
from typing import Any, Dict


class BaseNode(ABC):
    """节点基类"""

    def __init__(self, llm_client, node_name: str = ""):
        self.llm_client = llm_client
        self.node_name = node_name or self.__class__.__name__

    @abstractmethod
    def run(self, input_data: Any, **kwargs) -> Any:
        """执行节点处理逻辑"""
        pass

    def log_info(self, message: str):
        """记录信息日志"""
        print(f"[{self.node_name}] {message}")

    def log_error(self, message: str):
        """记录错误日志"""
        print(f"[{self.node_name}] 错误: {message}")
