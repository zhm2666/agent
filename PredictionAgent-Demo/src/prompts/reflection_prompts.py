"""
反思机制相关提示词
"""

# 步骤验证提示词
PRODUCT_VALIDATION_PROMPT = """
## 产品识别验证

请验证以下产品识别结果的质量：

识别结果：
- 产品代码: {product_code}
- 产品名称: {product_name}
- 置信度: {confidence}
- 推理过程: {reasoning}
- 备选方案: {alternatives}

请检查：
1. 产品信息是否完整？
2. 置信度是否合理？
3. 是否有多个可能的匹配？

返回JSON格式：
{{"is_valid": bool, "issues": ["问题1", "问题2"], "suggestions": ["建议1"]}}
"""

DATA_VALIDATION_PROMPT = """
## 数据获取验证

请验证以下数据获取结果的质量：

数据概况：
- 历史数据条数: {historical_count}
- 未来预测条数: {future_count}
- 统计指标: {statistics}

数据样例（前5条）：
{historical_sample}

请检查：
1. 数据量是否足够？
2. 数据格式是否正确？
3. 是否存在明显异常值？

返回JSON格式：
{{"is_valid": bool, "issues": [], "suggestions": []}}
"""

CHART_VALIDATION_PROMPT = """
## 图表生成验证

请验证以下图表生成结果：

图表信息：
- 图表URL: {chart_url}
- 图表类型: {chart_type}
- 文件路径: {chart_filepath}

请检查：
1. 图表是否成功生成？
2. 文件是否存在？
3. URL是否有效？

返回JSON格式：
{{"is_valid": bool, "issues": [], "suggestions": []}}
"""

ANALYSIS_VALIDATION_PROMPT = """
## 分析结果验证

请验证以下分析报告的质量：

分析报告：
{analysis_result}

关键洞察：
{key_insights}

业务建议：
{recommendations}

请检查：
1. 是否回答了用户问题？
2. 是否有数据支撑？
3. 建议是否可操作？
4. 是否包含趋势分析？

返回JSON格式：
{{"is_valid": bool, "quality_score": 0.0-1.0, "issues": [], "suggestions": []}}
"""

# 反思提示词
REFLECTION_PROMPT = """
## 反思任务

任务：{task}
步骤：{step}
原始输入：{input}
执行结果：{output}
错误信息：{error}

请分析：
1. 失败的根本原因是什么？
2. 如何改进？
3. 下次应该注意什么？

以JSON格式返回：
{{"root_cause": "...", "improvements": ["..."], "cautions": ["..."]}}
"""

# 修正提示词
CORRECTION_PROMPT = """
## 结果修正任务

原始输出：
{original_output}

问题描述：
{problem}

建议改进：
{suggestions}

请直接输出修正后的结果（JSON格式）。
"""

# LLM自我反思提示词
LLM_SELF_REFLECTION = """
你是一个专业的销量预测分析师。请反思以下分析结果的质量。

分析结果：
{analysis}

请从以下维度评分（0-1）：
1. 准确性：分析结论是否有数据支撑
2. 完整性：是否涵盖了所有重要方面
3. 可操作性：建议是否实际可行
4. 清晰度：表达是否清晰易懂

返回格式：
{{
    "accuracy": 0.8,
    "completeness": 0.7,
    "actionability": 0.9,
    "clarity": 0.85,
    "overall": 0.82,
    "improvements": ["改进建议1", "改进建议2"]
}}
"""
