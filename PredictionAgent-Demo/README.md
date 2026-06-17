# PredictionAgent-Demo

基于深度学习的销量预测分析Agent实现

## 项目概述

这是一个智能预测分析Agent系统，可以：
1. 从用户自然语言问题中识别目标产品
2. 访问MySQL数据库获取历史销量和LSTM预测数据
3. **通过MCP协议**调用绘图服务生成可视化图表
4. 调用大模型进行深度预测分析

## 核心特性

- **MCP集成**: 绘图服务通过MCP (Model Context Protocol) 调用，支持本地和远程模式
- **多LLM支持**: DeepSeek / OpenAI
- **多图表类型**: 柱状图 / 折线图 / 组合图
- **状态管理**: 完整的执行状态追踪

## 项目结构

```
PredictionAgent-Demo/
├── src/
│   ├── agent.py              # Agent主控制器
│   ├── agent_mcp.py          # MCP版Agent
│   ├── llms/                 # LLM客户端
│   ├── nodes/                # 处理节点
│   ├── database/             # 数据库层
│   ├── state/               # 状态管理
│   ├── prompts/              # 提示词
│   ├── tools/               # 工具
│   ├── mcp/                  # MCP服务 ⭐
│   │   ├── chart_mcp_server.py  # MCP服务器
│   │   └── client.py            # MCP客户端
│   └── utils/               # 工具函数
├── examples/                # 示例代码
│   ├── basic_usage.py
│   ├── advanced_usage.py
│   ├── mcp_usage.py          # MCP使用示例 ⭐
│   └── streamlit_app.py
├── scripts/                 # 脚本
│   ├── init_database.py
│   ├── schema.sql
│   └── run_mcp_server.py     # MCP服务器启动 ⭐
├── output/                  # 输出目录
├── MCP使用指南.md             # MCP详细文档 ⭐
├── requirements.txt
└── README.md
```

## 安装

```bash
pip install -r requirements.txt
```

## 配置

在环境变量中设置API密钥：

```bash
export DEEPSEEK_API_KEY="your-deepseek-api-key"
export OPENAI_API_KEY="your-openai-api-key"  # 可选

# MySQL配置
export MYSQL_HOST="localhost"
export MYSQL_PORT="3306"
export MYSQL_USER="root"
export MYSQL_PASSWORD="your-password"
export MYSQL_DATABASE="prediction_db"
```

## 初始化数据库

```bash
cd scripts
python init_database.py
```

这将创建示例产品数据、销售数据和LSTM预测数据。

## 使用示例

### 基础使用

```python
from src.agent import create_agent

# 创建Agent
agent = create_agent()

# 执行分析（使用模拟数据）
result = agent.analyze(
    query="分析iPhone 15 Pro的销量预测",
    chart_type="combined",  # bar/line/combined
    use_mock_data=True
)

print(result)
```

### 使用真实数据库

```python
from src.agent import PredictionAgent
from src.utils import Config

config = Config(
    mysql_host="localhost",
    mysql_port=3306,
    mysql_user="root",
    mysql_password="",
    mysql_database="prediction_db"
)

agent = PredictionAgent(config)
result = agent.analyze(
    query="预测小米手机的销量",
    use_mock_data=False
)
```

### Streamlit应用

```bash
cd examples
streamlit run streamlit_app.py
```

## Agent工作流程

```
用户问题
    │
    ▼
┌─────────────────────────────────────────┐
│  Step 1: 产品识别                         │
│  ProductIdentificationNode                │
│  → LLM理解用户问题，识别产品                │
│  → 输出: product_code, confidence         │
└─────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────┐
│  Step 2: 数据获取                         │
│  DataFetchNode                           │
│  → 查询MySQL获取历史销量数据               │
│  → 获取LSTM模型预测值                     │
│  → 获取未来预测值                         │
└─────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────┐
│  Step 3: 图表生成 (MCP)                  │
│  ChartNode → MCPChartClient              │
│  → 通过MCP协议调用绘图服务               │
│  → 支持: bar/line/combined              │
│  → 保存图片，返回URL                     │
└─────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────┐
│  Step 4: 预测分析                         │
│  AnalysisNode                            │
│  → 整合数据、图表URL到提示词               │
│  → LLM进行深度分析和预测                  │
│  → 输出分析报告和建议                     │
└─────────────────────────────────────────┘
```

## 返回结果示例

```json
{
  "success": true,
  "product": {
    "code": "P001",
    "name": "iPhone 15 Pro",
    "confidence": 0.95
  },
  "data": {
    "historical_data": [...],
    "future_predictions": [...],
    "statistics": {
      "avg_daily_sales": 186.5,
      "trend_direction": "up",
      "trend_change_percent": 8.3
    }
  },
  "chart": {
    "url": "/charts/sales_forecast_abc123.png",
    "type": "combined"
  },
  "analysis": {
    "result": "基于历史数据分析...",
    "key_insights": ["洞察1", "洞察2"],
    "recommendations": ["建议1", "建议2"]
  }
}
```

## 环境要求

- Python 3.8+
- MySQL 5.7+ (可选，如需真实数据)
- DeepSeek API Key 或 OpenAI API Key

## MCP (Model Context Protocol)

本项目使用MCP协议调用绘图服务，支持两种模式：

### 本地模式（推荐）

```python
from src.mcp import MCPChartClient

client = MCPChartClient(mode="local")
result = client.plot_sales_forecast(
    product_name="iPhone 15 Pro",
    dates=["2024-01-01", "2024-01-02"],
    actual_values=[100, 120],
    predicted_values=[95, 118],
    future_dates=["2024-01-03"],
    future_predictions=[125],
    chart_type="combined"
)
print(f"图表: {result.url}")
```

### 远程模式

```bash
# 启动MCP服务器
python scripts/run_mcp_server.py --mode http --port 8000
```

```python
# 调用远程服务
from src.mcp import MCPChartClient

client = MCPChartClient(mode="remote", server_url="http://localhost:8000")
result = client.plot_sales_forecast(...)
```

详细文档请查看 [MCP使用指南.md](MCP使用指南.md)
