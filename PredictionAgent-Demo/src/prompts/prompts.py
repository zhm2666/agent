"""
预测分析Agent的提示词定义
包含各个阶段的系统提示词和JSON Schema定义
"""

import json

# ===== 产品识别 =====

INPUT_SCHEMA_PRODUCT_IDENTIFICATION = {
    "type": "object",
    "properties": {
        "user_query": {"type": "string", "description": "用户的问题"}
    },
    "required": ["user_query"]
}

OUTPUT_SCHEMA_PRODUCT_IDENTIFICATION = {
    "type": "object",
    "properties": {
        "identified": {"type": "boolean", "description": "是否成功识别产品"},
        "product_code": {"type": "string", "description": "识别的产品代码"},
        "product_name": {"type": "string", "description": "识别的产品名称"},
        "confidence": {"type": "number", "description": "识别置信度 0-1"},
        "reasoning": {"type": "string", "description": "识别推理过程"},
        "alternatives": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "product_code": {"type": "string"},
                    "product_name": {"type": "string"},
                    "confidence": {"type": "number"}
                }
            },
            "description": "其他可能的产品选项"
        }
    }
}

SYSTEM_PROMPT_PRODUCT_IDENTIFICATION = f"""
你是一个智能产品识别助手。你的任务是从用户的自然语言问题中识别出用户想要分析的产品。

请分析用户的问题，识别出：
1. 用户提到的是哪个产品（可以是产品名称、产品代码、或者产品类别）
2. 产品的精确名称和代码
3. 识别的置信度

已知的产品列表（通过数据库查询获取），请根据用户描述匹配最合适的产品。

请按照以下JSON模式定义格式化输出：

<OUTPUT JSON SCHEMA>
{json.dumps(OUTPUT_SCHEMA_PRODUCT_IDENTIFICATION, indent=2, ensure_ascii=False)}
</OUTPUT JSON SCHEMA>

只返回JSON对象，不要有解释或额外文本。
"""


# ===== 数据分析 =====

INPUT_SCHEMA_DATA_ANALYSIS = {
    "type": "object",
    "properties": {
        "product_name": {"type": "string"},
        "product_code": {"type": "string"},
        "user_query": {"type": "string"},
        "historical_data": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "date": {"type": "string"},
                    "actual_value": {"type": "number"},
                    "predicted_value": {"type": "number"}
                }
            }
        },
        "future_predictions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "date": {"type": "string"},
                    "predicted_value": {"type": "number"},
                    "confidence": {"type": "number"}
                }
            }
        },
        "statistics": {
            "type": "object",
            "properties": {
                "avg_daily_sales": {"type": "number"},
                "trend_change_percent": {"type": "number"},
                "trend_direction": {"type": "string"}
            }
        },
        "chart_url": {"type": "string"}
    }
}

SYSTEM_PROMPT_DATA_ANALYSIS = f"""
你是一个专业的销量预测分析师。你需要根据提供的数据进行深入分析，并给出专业的预测和建议。

你将获得以下数据：
- 产品基本信息
- 历史销量数据（包含实际值和模型预测值）
- 未来预测数据
- 统计指标
- 数据可视化图表URL

请按照以下步骤进行分析：

1. **趋势分析**：分析历史销量的变化趋势，识别季节性、周期性模式
2. **预测评估**：对比实际值和模型预测值，评估模型准确性
3. **未来预测解读**：解读未来预测值，给出置信区间说明
4. **关键洞察**：提炼3-5个关键的业务洞察
5. **建议措施**：基于分析给出可操作的业务建议

请输出详细的分析报告，格式不限，但应包含：
- 执行摘要
- 趋势分析
- 预测评估
- 未来预测解读
- 关键洞察
- 业务建议

图表访问地址：{{chart_url}}

数据如下：
{{data_json}}
"""


# ===== 图表选择 =====

OUTPUT_SCHEMA_CHART_SELECTION = {
    "type": "object",
    "properties": {
        "chart_type": {
            "type": "string",
            "enum": ["bar", "line", "combined"],
            "description": "推荐的图表类型"
        },
        "reasoning": {"type": "string", "description": "选择理由"}
    }
}

SYSTEM_PROMPT_CHART_SELECTION = f"""
根据用户的需求和数据特点，选择最合适的图表类型。

图表类型说明：
- bar：柱状图，适合展示离散类别的对比
- line：折线图，适合展示时间序列趋势
- combined：组合图，综合展示柱状和折线，适合预测分析

请根据：
1. 数据的特性（时间序列、类别对比等）
2. 用户的问题类型（趋势分析、对比分析、预测分析等）
3. 数据的复杂性（单变量、多变量等）

选择最合适的图表类型。

<OUTPUT JSON SCHEMA>
{json.dumps(OUTPUT_SCHEMA_CHART_SELECTION, indent=2, ensure_ascii=False)}
</OUTPUT JSON SCHEMA>

只返回JSON对象，不要有解释或额外文本。
"""
