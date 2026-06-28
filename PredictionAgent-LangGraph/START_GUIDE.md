# PredictionAgent-LangGraph 启动指南

## 方式一：运行示例脚本（推荐新手）

```bash
cd PredictionAgent-LangGraph

# 1. 安装依赖
pip install -r requirements.txt

# 2. 复制并编辑环境变量
copy .env.example .env
# 然后编辑 .env，填入你的 API Key

# 3. 运行基础示例
python examples/basic_usage.py

# 4. 运行高级示例
python examples/advanced_usage.py
```

## 方式二：代码中直接使用

```python
from src.agent import PredictionAgent

# 创建 Agent（会自动从 .env 加载配置）
agent = PredictionAgent()

# 执行分析（使用模拟数据，无需数据库）
result = agent.analyze(
    query="分析 iPhone 15 的销量预测",
    chart_type="combined",
    use_mock_data=True,  # True=模拟数据，False=真实数据库
)

# 查看结果
if result["success"]:
    print(f"产品: {result['product']['name']}")
    print(f"图表: {result['chart']['url']}")
    print(f"分析: {result['analysis']['result']}")
```

## 方式三：集成到 Web 服务

```python
from src.agent import PredictionAgent
from fastapi import FastAPI

app = FastAPI()
agent = PredictionAgent()

@app.post("/analyze")
async def analyze(query: str, chart_type: str = "combined"):
    result = agent.analyze(query=query, chart_type=chart_type)
    return result
```

---

## 环境变量说明

| 变量 | 必须 | 说明 |
|------|------|------|
| `DEEPSEEK_API_KEY` | 是* | DeepSeek API Key |
| `OPENAI_API_KEY` | 是* | 或 OpenAI API Key（二选一） |
| `MYSQL_*` | 否 | 数据库配置，不填则用模拟数据 |
| `USE_OTEL` | 否 | 是否启用 OpenTelemetry |
| `LANGSMITH_API_KEY` | 否 | LangSmith 追踪 |

---

## 常见问题

### Q: ImportError: No module named 'langgraph'
```bash
pip install -r requirements.txt
```

### Q: API Key 错误
检查 `.env` 文件中的 API Key 是否正确配置

### Q: 数据库连接失败
- 设置 `use_mock_data=True` 使用模拟数据
- 或检查 `MYSQL_*` 环境变量是否正确
