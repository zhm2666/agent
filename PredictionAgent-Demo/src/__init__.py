"""
PredictionAgent - 产品销量预测分析Agent
基于深度学习的销量预测系统
"""

from .agent import PredictionAgent, create_agent
from .agent_mcp import PredictionAgent as PredictionAgentMCP
from .agent_reflective import ReflectiveAgent, create_reflective_agent

# 为了向后兼容，导出原agent
__all__ = [
    "PredictionAgent",
    "PredictionAgentMCP",
    "ReflectiveAgent",
    "create_agent",
    "create_reflective_agent"
]
