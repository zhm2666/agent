"""
结果修正器
根据评估结果决定如何修正/重试
"""

from typing import Dict, Any, Optional, List, Callable
from .state import (
    ValidationResult,
    RetryAction,
    RetryStrategy,
    ErrorType,
    ReflectionRecord
)


class ResultRevisor:
    """
    结果修正器

    负责根据评估结果决定修正策略：
    1. 决定是否需要重试
    2. 选择合适的修正动作
    3. 构建修正后的输入
    """

    def __init__(self, llm_client=None):
        self.llm_client = llm_client

    def decide_action(
        self,
        step: str,
        validation: ValidationResult,
        retry_strategy: RetryStrategy,
        current_attempts: int = 0
    ) -> tuple[bool, RetryAction, str]:
        """
        决定修正动作

        Args:
            step: 步骤名称
            validation: 验证结果
            retry_strategy: 重试策略
            current_attempts: 当前尝试次数

        Returns:
            (should_continue, action, reason)
            - should_continue: 是否继续执行
            - action: 采取的动作
            - reason: 原因说明
        """

        # 如果验证通过
        if validation.is_valid:
            if validation.score >= 0.8:
                return False, RetryAction.SKIP_STEP, "结果质量良好，无需修正"
            else:
                # 质量一般，可以优化但不强制
                return False, RetryAction.SKIP_STEP, f"结果可接受 (分数: {validation.score:.2f})"

        # 验证失败，确定错误类型
        error_type = validation.error_type or ErrorType.UNKNOWN_ERROR

        # 检查是否可以重试
        step_config = retry_strategy.step_configs.get(step, {})
        max_retries = step_config.get("max_retries", retry_strategy.max_retries)

        if current_attempts < max_retries:
            # 可以重试，选择动作
            action = self._select_retry_action(step, error_type, validation)
            return True, action, f"需要重试 ({error_type.value})"

        # 超过最大重试次数
        fallback_action = retry_strategy.get_fallback_action(step)
        return False, fallback_action, f"超过最大重试次数，使用回退动作: {fallback_action.value}"

    def _select_retry_action(
        self,
        step: str,
        error_type: ErrorType,
        validation: ValidationResult
    ) -> RetryAction:
        """根据错误类型选择重试动作"""
        action_map = {
            # 产品识别
            ErrorType.PRODUCT_NOT_FOUND: RetryAction.REIDENTIFY_PRODUCT,
            ErrorType.PRODUCT_AMBIGUOUS: RetryAction.ASK_USER,
            ErrorType.PRODUCT_MISIDENTIFIED: RetryAction.REIDENTIFY_PRODUCT,

            # 数据获取
            ErrorType.DATA_NOT_FOUND: RetryAction.REFETCH_DATA,
            ErrorType.DATA_INSUFFICIENT: RetryAction.USE_FALLBACK,
            ErrorType.DATA_INVALID: RetryAction.REFETCH_DATA,

            # 图表生成
            ErrorType.CHART_GENERATION_FAILED: RetryAction.REGENERATE_CHART,
            ErrorType.CHART_RENDERING_ERROR: RetryAction.REGENERATE_CHART,

            # 分析
            ErrorType.ANALYSIS_INVALID: RetryAction.REANALYZE,
            ErrorType.ANALYSIS_INCOMPLETE: RetryAction.REANALYZE,
            ErrorType.ANALYSIS_INCONSISTENT: RetryAction.REANALYZE,

            # 通用
            ErrorType.UNKNOWN_ERROR: RetryAction.REFETCH_DATA,
            ErrorType.TIMEOUT: RetryAction.REFETCH_DATA,
            ErrorType.VALIDATION_FAILED: RetryAction.REFETCH_DATA,
        }

        return action_map.get(error_type, RetryAction.REFETCH_DATA)

    def get_modified_input(
        self,
        step: str,
        action: RetryAction,
        original_input: Dict[str, Any],
        validation: ValidationResult,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        根据动作获取修正后的输入

        Args:
            step: 步骤名称
            action: 采取的动作
            original_input: 原始输入
            validation: 验证结果
            context: 上下文（包含之前的执行结果）

        Returns:
            修正后的输入
        """
        if action == RetryAction.SKIP_STEP:
            return original_input

        if action == RetryAction.ASK_USER:
            # 需要用户输入，无法自动修正
            return {
                **original_input,
                "_requires_user_input": True,
                "_user_prompt": self._generate_user_prompt(step, validation)
            }

        if action == RetryAction.USE_FALLBACK:
            return {
                **original_input,
                "_use_fallback": True,
                "_fallback_mode": "mock" if step == "data_fetch" else "skip"
            }

        # 其他动作，使用原始输入但添加修正提示
        return {
            **original_input,
            "_correction_hints": validation.suggestions,
            "_error_context": {
                "error_type": validation.error_type.value if validation.error_type else None,
                "error_message": validation.error_message,
                "suggestions": validation.suggestions
            }
        }

    def _generate_user_prompt(
        self,
        step: str,
        validation: ValidationResult
    ) -> str:
        """生成用户提示"""
        prompts = {
            "product_identification": f"""
产品识别存在疑问：
{validation.error_message}

建议：
{chr(10).join(f"- {s}" for s in validation.suggestions)}

请提供更具体的产品信息，例如：
- 完整的产品名称
- 产品类别
- 产品代码（如果知道）
""",
            "analysis": f"""
分析结果不完整：
{validation.error_message}

建议：
{chr(10).join(f"- {s}" for s in validation.suggestions)}

请调整您的问题或提供更多背景信息。
"""
        }

        return prompts.get(step, validation.error_message)

    def build_reflection_prompt(
        self,
        step: str,
        input_data: Dict[str, Any],
        output_data: Dict[str, Any],
        validation: ValidationResult
    ) -> str:
        """
        构建反思提示词

        用于让LLM反思失败原因并提出改进建议
        """
        return f"""
## 反思任务

步骤: {step}

原始输入:
{json.dumps(input_data, ensure_ascii=False, indent=2)}

执行结果:
{json.dumps(output_data, ensure_ascii=False, indent=2)}

验证结果:
- 有效: {validation.is_valid}
- 分数: {validation.score:.2f}
- 错误类型: {validation.error_type.value if validation.error_type else 'N/A'}
- 错误消息: {validation.error_message}
- 建议: {validation.suggestions}

请分析：
1. 失败的根本原因是什么？
2. 如何改进输入或方法？
3. 下一次执行应该注意什么？
"""

    def should_use_llm_reflection(
        self,
        step: str,
        validation: ValidationResult
    ) -> bool:
        """判断是否需要LLM深度反思"""
        # 复杂步骤或低分结果需要深度反思
        complex_steps = ["analysis", "product_identification"]
        return step in complex_steps or validation.score < 0.5

    def modify_output_with_llm(
        self,
        step: str,
        output: Dict[str, Any],
        validation: ValidationResult,
        context: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        使用LLM修正输出

        Args:
            step: 步骤名称
            output: 原始输出
            validation: 验证结果
            context: 上下文

        Returns:
            修正后的输出，如果无法修正则返回None
        """
        if not self.llm_client:
            return None

        prompt = f"""
## 任务
修正以下{step}步骤的输出结果，使其更准确或完整。

## 原始输出
{json.dumps(output, ensure_ascii=False, indent=2)}

## 问题描述
{validation.error_message}

## 建议改进
{chr(10).join(f"- {s}" for s in validation.suggestions)}

## 上下文
{json.dumps(context, ensure_ascii=False, indent=2)}

请直接返回修正后的输出（JSON格式）。如果无法修正，返回原始输出。
"""

        try:
            response = self.llm_client.invoke(
                "你是一个专业的AI助手，擅长修正和改进输出。直接返回修正后的JSON。",
                prompt
            )

            # 尝试解析JSON
            import json
            # 清理响应中的markdown代码块
            if "```json" in response:
                start = response.find("```json") + 7
                end = response.find("```", start)
                response = response[start:end]
            elif "```" in response:
                start = response.find("```") + 3
                end = response.find("```", start)
                response = response[start:end]

            return json.loads(response.strip())

        except Exception:
            return None


def json.dumps(obj, **kwargs):
    """本地json.dumps包装"""
    import json
    return json.dumps(obj, **kwargs)
