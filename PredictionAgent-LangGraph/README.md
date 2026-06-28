# PredictionAgent-LangGraph

基于 LangGraph 重构的销量预测分析 Agent，独立项目，不依赖 PredictionAgent-Demo。

## 快速开始

### 1. 安装依赖

```bash
cd PredictionAgent-LangGraph
pip install -r requirements.txt
```

### 2. 配置环境变量

有两种方式：

**方式 A：使用 .env 文件（推荐）**

```bash
cp .env.example .env
# 编辑 .env，填入你的 API Key
```

**方式 B：设置环境变量**

```bash
# LLM 配置（二选一）
export DEEPSEEK_API_KEY=sk-xxx
export DEEPSEEK_MODEL=deepseek-chat

# 或者
export OPENAI_API_KEY=sk-xxx
export OPENAI_MODEL=gpt-4o-mini

# 数据库配置（可选，缺省则使用模拟数据）
export MYSQL_HOST=localhost
export MYSQL_PORT=3306
export MYSQL_USER=root
export MYSQL_PASSWORD=xxx
export MYSQL_DATABASE=prediction_db
```

### 3. 运行示例

```bash
# 基础示例
python examples/basic_usage.py

# 高级示例（多轮对话、流式执行等）
python examples/advanced_usage.py
```

### 4. 启用分布式追踪（可选）

```bash
# 编辑 .env
USE_OTEL=true
OTLP_ENDPOINT=http://localhost:4318
LANGSMITH_API_KEY=your-langsmith-key
```

详细配置请参考 [TRACING_GUIDE.md](TRACING_GUIDE.md)

## 与原版对比

| 维度 | PredictionAgent-Demo | PredictionAgent-LangGraph |
|------|---------------------|--------------------------|
| 流程控制 | 手写顺序调用 | LangGraph StateGraph |
| 状态管理 | 自定义 State 类 | TypedDict + checkpointer |
| 会话管理 | 无 | thread_id 多轮续跑 |
| 持久化 | 文件/内存 | MemorySaver / PostgresSaver |
| 重试机制 | 手写循环 | 条件边 + 状态路由 |
| 流式执行 | 无 | stream_analysis() |

## 核心概念对照

### thread_id / user_id / session_id

```
调用方
  │
  ├── thread_id  ──► config["configurable"]["thread_id"]  ──► checkpointer（多轮续跑）
  ├── user_id    ──► config["configurable"]["user_id"]    ──► LangSmith 审计
  └── session_id ──► initial_state["session_id"]           ──► 业务追踪
```

### 图结构

```
__start__
    │
    ▼
product_identification
    │  (confidence < 0.5 ?)
    ▼
data_fetch
    │  (data insufficient ?)
    ▼
chart_generation
    │  (generation failed ?)
    ▼
analysis ───► should_retry_or_end
    │                   │
    │  validation OK    │  validation failed & retries > 0
    ▼                   ▼
  END              retry current node
```

## 目录结构

```
PredictionAgent-LangGraph/
├── src/
│   ├── agent.py               # Agent 入口，analyze() / stream_analysis()
│   ├── graph/
│   │   ├── builder.py         # 图构建器，create_prediction_graph()
│   │   └── conditional_routing.py  # 条件边路由
│   ├── nodes/
│   │   ├── product_identification_node.py
│   │   ├── data_fetch_node.py
│   │   ├── chart_node.py
│   │   └── analysis_node.py
│   ├── state/
│   │   └── prediction_state.py  # TypedDict 状态定义
│   ├── utils/
│   │   └── config.py
│   └── llms/
│       └── factory.py
├── examples/
│   ├── basic_usage.py
│   └── advanced_usage.py
└── requirements.txt
```

## 环境变量

```bash
# LLM 配置（二选一）
export DEEPSEEK_API_KEY=sk-xxx
export DEEPSEEK_MODEL=deepseek-chat

# 或者
export OPENAI_API_KEY=sk-xxx
export OPENAI_MODEL=gpt-4o-mini

# 数据库配置（可选，缺省则使用模拟数据）
export MYSQL_HOST=localhost
export MYSQL_PORT=3306
export MYSQL_USER=root
export MYSQL_PASSWORD=xxx
export MYSQL_DATABASE=prediction_db

# 图表输出目录
export CHART_OUTPUT_DIR=output/charts
```
