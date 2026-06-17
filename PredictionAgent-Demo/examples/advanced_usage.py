"""
高级使用示例 - 展示Agent的各种配置和使用方式
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.agent import PredictionAgent
from src.utils import Config, load_config
from src.database import DatabaseConnection, SalesRepository


def example_with_real_database():
    """使用真实数据库的示例"""
    print("\n" + "=" * 60)
    print("示例1: 使用真实数据库")
    print("=" * 60)

    config = Config(
        mysql_host="localhost",
        mysql_port=3306,
        mysql_user="root",
        mysql_password="",
        mysql_database="prediction_db",
        default_llm_provider="deepseek"
    )

    try:
        agent = PredictionAgent(config)

        result = agent.analyze(
            query="分析iPhone 15 Pro的销量预测",
            chart_type="combined",
            use_mock_data=False
        )

        if result.get("success"):
            print(f"产品: {result['product']['name']}")
            print(f"日均销量: {result['data']['statistics'].get('avg_daily_sales', 0):.2f}")
        else:
            print(f"分析失败: {result.get('error')}")

    except Exception as e:
        print(f"错误: {e}")


def example_with_mock_data():
    """使用模拟数据的示例"""
    print("\n" + "=" * 60)
    print("示例2: 使用模拟数据")
    print("=" * 60)

    agent = PredictionAgent()

    result = agent.analyze(
        query="预测小米手机的销量趋势",
        chart_type="combined",
        use_mock_data=True
    )

    if result.get("success"):
        print(f"分析成功！")
        print(f"图表保存在: {result['chart']['filepath']}")
        return result
    else:
        print(f"分析失败: {result.get('error')}")
        return None


def example_with_openai():
    """使用OpenAI的示例"""
    print("\n" + "=" * 60)
    print("示例3: 使用OpenAI")
    print("=" * 60)

    # 设置OpenAI API Key
    os.environ["OPENAI_API_KEY"] = "your-api-key-here"

    config = Config(
        default_llm_provider="openai",
        openai_model="gpt-4o-mini"
    )

    agent = PredictionAgent(config)

    result = agent.analyze(
        query="分析戴森吹风机的销量预测",
        chart_type="line",
        use_mock_data=True
    )

    if result.get("success"):
        print("分析完成！")
        print(result["analysis"]["result"][:500] + "...")


def example_direct_product_code():
    """直接指定产品代码的示例"""
    print("\n" + "=" * 60)
    print("示例4: 直接指定产品代码")
    print("=" * 60)

    agent = PredictionAgent()

    result = agent.analyze(
        query="销量分析",
        chart_type="bar",
        use_mock_data=True,
        product_code="P001"  # 直接指定iPhone 15 Pro
    )

    if result.get("success"):
        print(f"产品: {result['product']['name']}")
        print(f"分析报告:\n{result['analysis']['result']}")


def example_streamlit_app():
    """Streamlit应用示例"""
    print("\n" + "=" * 60)
    print("示例5: Streamlit应用")
    print("=" * 60)

    print("""
    要启动Streamlit应用，请运行：

    cd examples
    streamlit run streamlit_app.py

    应用功能：
    - 输入自然语言查询
    - 选择图表类型
    - 查看分析结果和可视化
    """)


def example_query_database():
    """直接查询数据库的示例"""
    print("\n" + "=" * 60)
    print("示例6: 直接查询数据库")
    print("=" * 60)

    config = load_config()

    try:
        db = DatabaseConnection(
            host=config.mysql_host,
            port=config.mysql_port,
            user=config.mysql_user,
            password=config.mysql_password,
            database=config.mysql_database
        )

        if db.connect():
            repo = SalesRepository(db)

            # 获取所有产品
            products = repo.get_all_products()
            print(f"\n数据库中的产品数量: {len(products)}")
            for p in products:
                print(f"  - {p.product_code}: {p.product_name}")

            # 获取特定产品的分析数据
            if products:
                analysis_data = repo.get_product_analysis_data(
                    products[0].product_code,
                    history_days=30,
                    future_days=7
                )
                print(f"\n{analysis_data.product.product_name} 的数据:")
                print(f"  历史数据: {len(analysis_data.sales_history)} 条")
                print(f"  未来预测: {len(analysis_data.future_predictions)} 条")

    except Exception as e:
        print(f"数据库查询失败: {e}")


def main():
    """主函数"""
    print("=" * 70)
    print("Prediction Agent 高级使用示例")
    print("=" * 70)

    # 使用模拟数据的示例
    example_with_mock_data()

    # 直接指定产品代码的示例
    example_direct_product_code()

    # 直接查询数据库的示例
    try:
        example_query_database()
    except:
        print("跳过数据库查询示例（数据库可能未连接）")

    # Streamlit应用说明
    example_streamlit_app()

    print("\n" + "=" * 70)
    print("示例执行完成！")
    print("=" * 70)


if __name__ == "__main__":
    main()
