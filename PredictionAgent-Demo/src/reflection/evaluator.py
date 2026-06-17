"""
结果评估器
用于评估各步骤的执行结果，判断是否需要反思/重试
"""

import json
from typing import Dict, Any, Optional, List
from .state import (
    ValidationResult,
    ErrorType,
    ReflectionRecord
)


class ResultEvaluator:
    """
    结果评估器

    负责评估Agent各步骤的执行结果：
    1. 产品识别结果评估
    2. 数据获取结果评估
    3. 图表生成结果评估
    4. 分析结果评估
    """

    def __init__(self, llm_client=None):
        self.llm_client = llm_client

    def evaluate(
        self,
        step: str,
        input_data: Dict[str, Any],
        output_data: Dict[str, Any]
    ) -> ValidationResult:
        """
        评估执行结果

        Args:
            step: 步骤名称
            input_data: 输入数据
            output_data: 输出数据

        Returns:
            ValidationResult: 验证结果
        """
        evaluators = {
            "product_identification": self._evaluate_product_identification,
            "data_fetch": self._evaluate_data_fetch,
            "chart_generation": self._evaluate_chart_generation,
            "analysis": self._evaluate_analysis
        }

        evaluator = evaluators.get(step, self._evaluate_default)
        return evaluator(input_data, output_data)

    def _evaluate_product_identification(
        self,
        input_data: Dict[str, Any],
        output_data: Dict[str, Any]
    ) -> ValidationResult:
        """评估产品识别结果"""
        identified = output_data.get("identified", False)
        confidence = output_data.get("confidence", 0.0)
        product_code = output_data.get("product_code", "")
        reasoning = output_data.get("reasoning", "")

        suggestions = []
        error_type = None
        score = confidence

        # 检查是否识别成功
        if not identified:
            return ValidationResult(
                is_valid=False,
                score=0.0,
                error_type=ErrorType.PRODUCT_NOT_FOUND,
                error_message="无法识别产品",
                suggestions=["请提供更具体的产品名称", "尝试提供产品代码"]
            )

        # 检查置信度
        if confidence < 0.5:
            suggestions.append("置信度较低，建议用户确认")
            score = confidence
            error_type = ErrorType.PRODUCT_AMBIGUOUS

        # 检查产品代码
        if not product_code:
            suggestions.append("产品代码为空，可能识别错误")
            score = 0.0
            error_type = ErrorType.PRODUCT_MISIDENTIFIED

        # 检查推理过程
        if not reasoning and confidence < 0.8:
            suggestions.append("推理过程为空，置信度存疑")

        # 检查备选方案
        alternatives = output_data.get("alternatives", [])
        if not alternatives and confidence < 0.7:
            suggestions.append("没有提供备选方案，建议添加")

        return ValidationResult(
            is_valid=confidence >= 0.5 and bool(product_code),
            score=score,
            error_type=error_type,
            error_message="" if error_type is None else f"产品识别问题: {error_type.value}",
            suggestions=suggestions,
            metadata={
                "confidence": confidence,
                "has_alternatives": len(alternatives) > 0
            }
        )

    def _evaluate_data_fetch(
        self,
        input_data: Dict[str, Any],
        output_data: Dict[str, Any]
    ) -> ValidationResult:
        """评估数据获取结果"""
        fetched = output_data.get("fetched", False)
        historical_data = output_data.get("historical_data", [])
        future_predictions = output_data.get("future_predictions", [])
        error_message = output_data.get("error_message", "")

        suggestions = []
        error_type = None
        score = 1.0

        # 检查是否成功获取
        if not fetched:
            return ValidationResult(
                is_valid=False,
                score=0.0,
                error_type=ErrorType.DATA_NOT_FOUND,
                error_message=error_message or "数据获取失败",
                suggestions=["检查数据库连接", "尝试使用模拟数据"]
            )

        # 检查数据量
        if len(historical_data) < 7:
            suggestions.append("历史数据量过少（<7天），预测可能不准确")
            score *= 0.7
            error_type = ErrorType.DATA_INSUFFICIENT

        if len(historical_data) < 1:
            return ValidationResult(
                is_valid=False,
                score=0.0,
                error_type=ErrorType.DATA_NOT_FOUND,
                error_message="没有历史数据",
                suggestions=["检查产品代码是否正确", "检查数据库中是否有数据"]
            )

        # 检查数据有效性
        for item in historical_data:
            if "actual_value" not in item or "date" not in item:
                suggestions.append("部分数据缺少必要字段")
                score *= 0.8
                error_type = ErrorType.DATA_INVALID
                break

        # 检查未来预测
        if not future_predictions:
            suggestions.append("没有未来预测数据")
            score *= 0.9

        return ValidationResult(
            is_valid=fetched and len(historical_data) > 0,
            score=score,
            error_type=error_type,
            error_message="" if error_type is None else f"数据问题: {error_type.value}",
            suggestions=suggestions,
            metadata={
                "historical_count": len(historical_data),
                "future_count": len(future_predictions)
            }
        )

    def _evaluate_chart_generation(
        self,
        input_data: Dict[str, Any],
        output_data: Dict[str, Any]
    ) -> ValidationResult:
        """评估图表生成结果"""
        generated = output_data.get("generated", False)
        chart_url = output_data.get("chart_url", "")
        chart_filepath = output_data.get("chart_filepath", "")
        error = output_data.get("error", "")

        suggestions = []
        error_type = None
        score = 1.0

        # 检查是否生成成功
        if not generated:
            return ValidationResult(
                is_valid=False,
                score=0.0,
                error_type=ErrorType.CHART_GENERATION_FAILED,
                error_message=error or "图表生成失败",
                suggestions=["检查数据格式", "尝试更换图表类型", "跳过图表生成"]
            )

        # 检查URL
        if not chart_url:
            suggestions.append("图表URL为空")
            score *= 0.5
            error_type = ErrorType.CHART_RENDERING_ERROR

        # 检查文件路径
        if not chart_filepath:
            suggestions.append("图表文件路径为空")
            score *= 0.5
        else:
            import os
            if not os.path.exists(chart_filepath):
                suggestions.append("图表文件不存在")
                score *= 0.3
                error_type = ErrorType.CHART_RENDERING_ERROR

        return ValidationResult(
            is_valid=generated and bool(chart_url),
            score=score,
            error_type=error_type,
            error_message="" if error_type is None else f"图表问题: {error_type.value}",
            suggestions=suggestions,
            metadata={
                "chart_url": chart_url,
                "chart_type": output_data.get("chart_type", "")
            }
        )

    def _evaluate_analysis(
        self,
        input_data: Dict[str, Any],
        output_data: Dict[str, Any]
    ) -> ValidationResult:
        """评估分析结果"""
        analyzed = output_data.get("analyzed", False)
        analysis_result = output_data.get("analysis_result", "")
        key_insights = output_data.get("key_insights", [])
        recommendations = output_data.get("recommendations", [])

        suggestions = []
        error_type = None
        score = 1.0

        # 检查是否分析成功
        if not analyzed:
            return ValidationResult(
                is_valid=False,
                score=0.0,
                error_type=ErrorType.ANALYSIS_INVALID,
                error_message="分析失败",
                suggestions=["检查LLM调用", "尝试简化查询"]
            )

        # 检查分析结果长度
        if len(analysis_result) < 50:
            suggestions.append("分析结果过短，可能不完整")
            score *= 0.7
            error_type = ErrorType.ANALYSIS_INCOMPLETE

        # 检查关键洞察
        if not key_insights:
            suggestions.append("没有提取到关键洞察")
            score *= 0.8
            error_type = ErrorType.ANALYSIS_INCOMPLETE

        # 检查建议
        if not recommendations:
            suggestions.append("没有提供业务建议")
            score *= 0.9

        # 使用LLM进行深度评估（如果有LLM客户端）
        if self.llm_client and len(analysis_result) > 100:
            llm_eval = self._llm_evaluate_analysis(analysis_result, input_data)
            if llm_eval:
                score = (score + llm_eval) / 2

        return ValidationResult(
            is_valid=analyzed and len(analysis_result) > 50,
            score=score,
            error_type=error_type,
            error_message="" if error_type is None else f"分析问题: {error_type.value}",
            suggestions=suggestions,
            metadata={
                "result_length": len(analysis_result),
                "insights_count": len(key_insights),
                "recommendations_count": len(recommendations)
            }
        )

    def _evaluate_default(
        self,
        input_data: Dict[str, Any],
        output_data: Dict[str, Any]
    ) -> ValidationResult:
        """默认评估"""
        return ValidationResult(
            is_valid=True,
            score=1.0,
            suggestions=[]
        )

    def _llm_evaluate_analysis(
        self,
        analysis_result: str,
        input_data: Dict[str, Any]
    ) -> Optional[float]:
        """使用LLM评估分析结果质量"""
        if not self.llm_client:
            return None

        prompt = f"""
请评估以下销量预测分析报告的质量，只返回一个0-1之间的分数：

分析报告：
{analysis_result[:2000]}

评估标准：
1. 是否包含趋势分析
2. 是否有数据支撑
3. 是否提供了可操作的建议
4. 是否回答了用户的问题

只返回分数，格式：0.85
"""

        try:
            response = self.llm_client.invoke(
                "你是一个质量评估专家，只返回一个0-1之间的数字分数",
                prompt
            )
            # 提取数字
            import re
            match = re.search(r'0?\.\d+', response)
            if match:
                return float(match.group())
        except Exception:
            pass

        return None

    def create_record(
        self,
        step: str,
        input_data: Dict[str, Any],
        output_data: Dict[str, Any],
        validation: ValidationResult,
        retry_count: int = 0
    ) -> ReflectionRecord:
        """创建反思记录"""
        return ReflectionRecord(
            step=step,
            input_data=input_data,
            output_data=output_data,
            validation=validation,
            retry_count=retry_count
        )
