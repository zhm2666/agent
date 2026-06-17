"""
分析节点
负责基于数据和图表进行最终的预测分析
"""

import json
from typing import Dict, Any
from .base_node import BaseNode
from ..prompts import SYSTEM_PROMPT_DATA_ANALYSIS


class AnalysisNode(BaseNode):
    """分析节点"""

    def __init__(self, llm_client):
        super().__init__(llm_client, "Analysis")

    def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行预测分析

        Args:
            input_data: {
                "product_name": str,
                "product_code": str,
                "user_query": str,
                "historical_data": List[Dict],
                "future_predictions": List[Dict],
                "statistics": Dict,
                "chart_url": str
            }

        Returns:
            {
                "analyzed": bool,
                "analysis_result": str,
                "key_insights": List[str],
                "recommendations": List[str]
            }
        """
        product_name = input_data.get("product_name", "")
        product_code = input_data.get("product_code", "")
        user_query = input_data.get("user_query", "")
        historical_data = input_data.get("historical_data", [])
        future_predictions = input_data.get("future_predictions", [])
        statistics = input_data.get("statistics", {})
        chart_url = input_data.get("chart_url", "")

        self.log_info(f"正在分析产品: {product_name}")

        try:
            # 构建分析数据
            analysis_context = self._build_analysis_context(
                product_name, product_code, user_query,
                historical_data, future_predictions, statistics
            )

            # 调用LLM进行分析
            prompt = SYSTEM_PROMPT_DATA_ANALYSIS.format(
                chart_url=chart_url,
                data_json=json.dumps(analysis_context, ensure_ascii=False, indent=2)
            )

            analysis_result = self.llm_client.invoke(prompt, "")

            # 提取关键洞察和建议
            key_insights = self._extract_insights(analysis_result)
            recommendations = self._extract_recommendations(analysis_result)

            result = {
                "analyzed": True,
                "analysis_result": analysis_result,
                "key_insights": key_insights,
                "recommendations": recommendations
            }

            self.log_info("分析完成")
            return result

        except Exception as e:
            self.log_error(f"分析失败: {str(e)}")
            return {
                "analyzed": False,
                "analysis_result": f"分析过程中出错: {str(e)}",
                "key_insights": [],
                "recommendations": []
            }

    def _build_analysis_context(
        self,
        product_name: str,
        product_code: str,
        user_query: str,
        historical_data: list,
        future_predictions: list,
        statistics: dict
    ) -> Dict[str, Any]:
        """构建分析上下文"""
        return {
            "product": {
                "name": product_name,
                "code": product_code
            },
            "user_query": user_query,
            "data_summary": {
                "historical_period": f"最近{len(historical_data)}天",
                "data_points": len(historical_data),
                "future_predictions_days": len(future_predictions)
            },
            "historical_data": historical_data[-30:] if len(historical_data) > 30 else historical_data,  # 最近30天
            "future_predictions": future_predictions,
            "statistics": statistics
        }

    def _extract_insights(self, analysis_text: str) -> list:
        """提取关键洞察"""
        insights = []

        # 简单的模式匹配
        lines = analysis_text.split("\n")
        for line in lines:
            line = line.strip()
            if any(keyword in line for keyword in ["洞察", "发现", "关键", "重点", "关键洞察"]):
                insights.append(line)

        return insights[:5]  # 最多5个

    def _extract_recommendations(self, analysis_text: str) -> list:
        """提取建议"""
        recommendations = []

        lines = analysis_text.split("\n")
        for line in lines:
            line = line.strip()
            if any(keyword in line for keyword in ["建议", "措施", "行动", "方案", "优化"]):
                recommendations.append(line)

        return recommendations[:5]  # 最多5个
