"""
Streamlit Web应用
提供可视化的预测分析界面
"""

import streamlit as st
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.agent import PredictionAgent
from src.utils import load_config


# 页面配置
st.set_page_config(
    page_title="销量预测分析Agent",
    page_icon="📊",
    layout="wide"
)


@st.cache_resource
def get_agent():
    """获取Agent实例（缓存）"""
    return PredictionAgent()


def main():
    """主函数"""
    st.title("📊 销量预测分析Agent")
    st.markdown("基于深度学习的智能销量预测分析系统")

    # 侧边栏配置
    st.sidebar.header("⚙️ 配置")

    chart_type = st.sidebar.selectbox(
        "选择图表类型",
        ["combined", "line", "bar"],
        format_func=lambda x: {
            "combined": "📈 组合图（推荐）",
            "line": "📉 折线图",
            "bar": "📊 柱状图"
        }.get(x, x)
    )

    use_mock = st.sidebar.checkbox("使用模拟数据", value=True)

    st.sidebar.markdown("---")
    st.sidebar.markdown("""
    ### 使用说明

    1. 在下方输入您的问题
    2. 选择图表类型
    3. 点击"开始分析"按钮
    4. 查看分析结果和可视化图表

    ### 示例问题

    - "分析iPhone 15 Pro的销量预测"
    - "预测MacBook Pro的销量趋势"
    - "华为手机的市场表现如何"
    """)

    # 主内容区
    query = st.text_input(
        "💬 输入您的问题",
        placeholder="例如：帮我分析iPhone的销量预测",
        help="输入您想要分析的产品相关问题"
    )

    col1, col2 = st.columns([1, 4])

    with col1:
        analyze_button = st.button("🔍 开始分析", type="primary", use_container_width=True)

    # 分析结果
    if analyze_button and query:
        with st.spinner("正在分析，请稍候..."):
            try:
                agent = get_agent()
                result = agent.analyze(
                    query=query,
                    chart_type=chart_type,
                    use_mock_data=use_mock
                )

                if result.get("success"):
                    st.success("✅ 分析完成！")

                    # 产品信息
                    product = result.get("product", {})
                    st.subheader(f"📦 {product.get('name', 'N/A')}")
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("产品代码", product.get('code', 'N/A'))
                    with col2:
                        st.metric("识别置信度", f"{product.get('confidence', 0):.0%}")
                    with col3:
                        stats = result.get("data", {}).get("statistics", {})
                        st.metric("日均销量", f"{stats.get('avg_daily_sales', 0):.1f}")

                    # 统计信息
                    st.subheader("📈 统计摘要")
                    stats = result.get("data", {}).get("statistics", {})
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("分析周期", f"{stats.get('period_days', 0)}天")
                    with col2:
                        st.metric("日均销量", f"{stats.get('avg_daily_sales', 0):.1f}")
                    with col3:
                        trend = stats.get('trend_direction', 'stable')
                        trend_emoji = {"up": "📈", "down": "📉", "stable": "➡️"}.get(trend, "➡️")
                        st.metric("趋势方向", f"{trend_emoji} {trend}")
                    with col4:
                        st.metric("趋势变化", f"{stats.get('trend_change_percent', 0):+.1f}%")

                    # 图表
                    chart = result.get("chart", {})
                    if chart.get("url"):
                        st.subheader("📊 可视化图表")
                        chart_path = chart.get("filepath", "")
                        if os.path.exists(chart_path):
                            st.image(chart_path, use_container_width=True)
                        else:
                            st.info(f"图表URL: {chart.get('url')}")

                    # 分析报告
                    st.subheader("📝 预测分析报告")
                    analysis = result.get("analysis", {})
                    st.markdown(analysis.get("result", "暂无分析报告"))

                    # 关键洞察
                    insights = analysis.get("key_insights", [])
                    if insights:
                        st.subheader("💡 关键洞察")
                        for i, insight in enumerate(insights, 1):
                            st.markdown(f"{i}. {insight}")

                    # 建议
                    recommendations = analysis.get("recommendations", [])
                    if recommendations:
                        st.subheader("📋 业务建议")
                        for i, rec in enumerate(recommendations, 1):
                            st.markdown(f"{i}. {rec}")

                else:
                    st.error(f"❌ 分析失败: {result.get('error', '未知错误')}")

            except Exception as e:
                st.error(f"❌ 发生错误: {str(e)}")

    elif not analyze_button:
        st.info("👆 请输入问题并点击'开始分析'按钮开始预测分析")


if __name__ == "__main__":
    main()
