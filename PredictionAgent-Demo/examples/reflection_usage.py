"""
反思机制使用示例
展示如何使用反思型Agent和结果验证
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.agent_reflective import ReflectiveAgent, create_reflective_agent
from src.reflection import ResultEvaluator, ResultRevisor, ReflectionState
from src.llms import DeepSeekLLM


def example_basic_reflection():
    """基础反思示例"""
    print("\n" + "=" * 60)
    print("示例1: 基础反思")
    print("=" * 60)

    # 创建反思型Agent
    agent = create_reflective_agent()

    # 执行分析（启用反思）
    result = agent.analyze(
        query="分析iPhone 15 Pro的销量预测",
        chart_type="combined",
        use_mock_data=True,
        enable_reflection=True
    )

    if result.get("success"):
        print(f"\n分析成功！")
        print(f"产品: {result['product']['name']}")

        # 查看反思历史
        reflection = result.get("reflection", {})
        if reflection:
            print(f"\n反思记录:")
            print(f"  反思次数: {reflection.get('reflection_count', 0)}")
            print(f"  记录数: {len(reflection.get('records', []))}")
    else:
        print(f"分析失败: {result.get('error')}")


def example_validation():
    """结果验证示例"""
    print("\n" + "=" * 60)
    print("示例2: 结果验证")
    print("=" * 60)

    evaluator = ResultEvaluator()

    # 测试产品识别验证
    print("\n--- 产品识别验证 ---")
    product_result = {
        "identified": True,
        "product_code": "P001",
        "product_name": "iPhone 15 Pro",
        "confidence": 0.95,
        "reasoning": "根据产品名称匹配",
        "alternatives": []
    }

    validation = evaluator.evaluate("product_identification", {}, product_result)
    print(f"验证结果: {'通过' if validation.is_valid else '失败'}")
    print(f"质量分数: {validation.score:.2f}")

    # 测试数据获取验证
    print("\n--- 数据获取验证 ---")
    data_result = {
        "fetched": True,
        "historical_data": [
            {"date": "2024-01-01", "actual_value": 100},
            {"date": "2024-01-02", "actual_value": 120}
        ],
        "future_predictions": [
            {"date": "2024-01-10", "predicted_value": 150}
        ],
        "statistics": {"avg_daily_sales": 110}
    }

    validation = evaluator.evaluate("data_fetch", {}, data_result)
    print(f"验证结果: {'通过' if validation.is_valid else '失败'}")
    print(f"分数: {validation.score:.2f}")
    if validation.suggestions:
        print(f"建议: {validation.suggestions}")

    # 测试图表验证
    print("\n--- 图表生成验证 ---")
    chart_result = {
        "generated": True,
        "chart_url": "/charts/test.png",
        "chart_filepath": "output/charts/test.png",
        "chart_type": "combined"
    }

    validation = evaluator.evaluate("chart_generation", {}, chart_result)
    print(f"验证结果: {'通过' if validation.is_valid else '失败'}")
    print(f"分数: {validation.score:.2f}")

    # 测试分析验证
    print("\n--- 分析结果验证 ---")
    analysis_result = {
        "analyzed": True,
        "analysis_result": "iPhone销量呈上升趋势，预计未来30天日均销量将达到150台。",
        "key_insights": ["趋势上升", "周末销量更高"],
        "recommendations": ["增加库存", "优化周末配送"]
    }

    validation = evaluator.evaluate("analysis", {}, analysis_result)
    print(f"验证结果: {'通过' if validation.is_valid else '失败'}")
    print(f"分数: {validation.score:.2f}")


def example_revisor():
    """修正器示例"""
    print("\n" + "=" * 60)
    print("示例3: 修正器决策")
    print("=" * 60)

    revisor = ResultRevisor()
    from src.reflection import RetryStrategy, ErrorType, RetryAction

    # 测试不同错误类型的决策
    test_cases = [
        {
            "name": "产品未找到",
            "validation": type('obj', (object,), {
                'is_valid': False,
                'error_type': ErrorType.PRODUCT_NOT_FOUND,
                'error_message': '无法识别产品',
                'suggestions': ['提供更具体的名称']
            })()
        },
        {
            "name": "数据不足",
            "validation": type('obj', (object,), {
                'is_valid': False,
                'error_type': ErrorType.DATA_INSUFFICIENT,
                'error_message': '历史数据不足7天',
                'suggestions': ['使用更多历史数据']
            })()
        },
        {
            "name": "图表生成失败",
            "validation": type('obj', (object,), {
                'is_valid': False,
                'error_type': ErrorType.CHART_GENERATION_FAILED,
                'error_message': '图表渲染失败',
                'suggestions': ['检查数据格式']
            })()
        }
    ]

    strategy = RetryStrategy()

    for case in test_cases:
        should_continue, action, reason = revisor.decide_action(
            "test_step",
            case["validation"],
            strategy,
            current_attempts=0
        )
        print(f"\n{case['name']}:")
        print(f"  继续执行: {should_continue}")
        print(f"  动作: {action.value}")
        print(f"  原因: {reason}")


def example_reflection_state():
    """反思状态示例"""
    print("\n" + "=" * 60)
    print("示例4: 反思状态管理")
    print("=" * 60)

    from src.reflection import ReflectionState, ReflectionRecord, ValidationResult, ErrorType

    # 创建反思状态
    state = ReflectionState(enabled=True, max_reflections=3)

    # 添加记录
    record1 = ReflectionRecord(
        step="product_identification",
        input_data={"query": "iPhone销量"},
        output_data={"identified": True, "confidence": 0.9},
        validation=ValidationResult(is_valid=True, score=0.9),
        retry_count=0
    )

    record2 = ReflectionRecord(
        step="data_fetch",
        input_data={"product_code": "P001"},
        output_data={"fetched": False},
        validation=ValidationResult(
            is_valid=False,
            score=0.0,
            error_type=ErrorType.DATA_NOT_FOUND,
            error_message="数据获取失败"
        ),
        retry_count=1
    )

    state.add_record(record1)
    state.add_record(record2)

    print(f"反思状态:")
    print(f"  启用: {state.enabled}")
    print(f"  反思次数: {state.reflection_count}")
    print(f"  记录数: {len(state.records)}")
    print(f"  失败步骤: {state.get_failed_steps()}")
    print(f"  可继续: {state.can_continue_reflection()}")

    # 序列化
    state_dict = state.to_dict()
    print(f"\n状态JSON:")
    import json
    print(json.dumps(state_dict, indent=2, ensure_ascii=False)[:500] + "...")


def example_disable_reflection():
    """禁用反思示例"""
    print("\n" + "=" * 60)
    print("示例5: 禁用反思机制")
    print("=" * 60)

    agent = create_reflective_agent()

    # 执行分析（禁用反思）
    result = agent.analyze(
        query="分析MacBook的销量",
        chart_type="line",
        use_mock_data=True,
        enable_reflection=False  # 禁用反思
    )

    if result.get("success"):
        print(f"\n分析成功（无反思）!")
        print(f"产品: {result['product']['name']}")
        print(f"反思记录: {result.get('reflection')}")  # 应该为None
    else:
        print(f"分析失败: {result.get('error')}")


def example_error_handling():
    """错误处理示例"""
    print("\n" + "=" * 60)
    print("示例6: 错误处理流程")
    print("=" * 60)

    agent = create_reflective_agent()

    # 测试错误场景：识别不存在的查询
    result = agent.analyze(
        query="分析不存在的xyz产品12345",
        chart_type="combined",
        use_mock_data=True,
        enable_reflection=True
    )

    print(f"\n结果:")
    print(f"  成功: {result.get('success')}")
    if result.get('reflection'):
        reflection = result['reflection']
        print(f"  反思次数: {reflection.get('reflection_count', 0)}")
        print(f"  失败步骤: {reflection.get('records', [])[-1] if reflection.get('records') else 'N/A'}")


def main():
    """主函数"""
    print("=" * 60)
    print("反思机制使用示例")
    print("=" * 60)

    # 示例1: 基础使用
    example_basic_reflection()

    # 示例2: 结果验证
    example_validation()

    # 示例3: 修正器
    example_revisor()

    # 示例4: 反思状态
    example_reflection_state()

    # 示例5: 禁用反思
    example_disable_reflection()

    # 示例6: 错误处理
    example_error_handling()

    print("\n" + "=" * 60)
    print("示例完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
