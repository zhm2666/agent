"""
LLM基类
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any


class BaseLLM(ABC):
    """LLM基类"""

    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None):
        self.api_key = api_key
        self.model_name = model_name

    @abstractmethod
    def invoke(self, system_prompt: str, user_prompt: str, **kwargs) -> str:
        """
        调用LLM生成回复

        Args:
            system_prompt: 系统提示词
            user_prompt: 用户输入
            **kwargs: 其他参数

        Returns:
            LLM生成的回复文本
        """
        pass

    @abstractmethod
    def get_model_info(self) -> Dict[str, Any]:
        """获取当前模型信息"""
        pass

    def validate_response(self, response: str) -> str:
        """验证响应"""
        if response is None:
            return ""
        return str(response).strip()
