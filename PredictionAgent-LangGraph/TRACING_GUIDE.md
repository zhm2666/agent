# PredictionAgent-LangGraph 分布式链路追踪指南

## 概述

已为 `PredictionAgent-LangGraph` 项目添加完整的分布式链路追踪支持，支持：

- **LangSmith** - 推荐，简单易用，云端可视化
- **OpenTelemetry** - 可选，自托管，支持 OTLP 协议

## 修改的文件

| 文件 | 改动 |
|------|------|
| `requirements.txt` | 添加 `langsmith`, `opentelemetry-*` |
| `src/tracing.py` | **新建** - 统一追踪模块 |
| `src/agent.py` | 添加 `@traceable` 装饰器 |
| `src/nodes/*.py` | 添加 `@trace_node` 装饰器 |
| `.env` | 添加追踪配置 |

## 快速开始

### 1. 安装依赖

```bash
cd PredictionAgent-LangGraph
pip install -r requirements.txt
```

### 2. 配置环境变量

编辑 `.env` 文件：

```bash
# LangSmith 配置（推荐）
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=your-langsmith-api-key
LANGSMITH_PROJECT=prediction-agent-dev

# OpenTelemetry 配置（可选）
USE_OTEL=false
OTLP_ENDPOINT=http://localhost:4317
```

### 3. 运行示例

```bash
python examples/basic_usage.py
```

### 4. 查看追踪

访问 https://smith.langchain.com 查看 LangSmith Dashboard。

---

## 追踪覆盖范围

```
┌─────────────────────────────────────────────────────────────────┐
│                    PredictionAgent.analyze()                    │
│                    @traceable("agent.analyze")                 │
└─────────────────────────────┬─────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌───────────────┐    ┌───────────────┐    ┌───────────────┐
│ product_      │    │   data_fetch  │    │ chart_        │
│ identification│───▶│               │───▶│ generation     │
│ @trace_node   │    │ @trace_node   │    │ @trace_node   │
└───────────────┘    └───────────────┘    └───────┬───────┘
                              │                    │
                              │              ┌─────┴─────┐
                              │              ▼           ▼
                              │      ┌───────────┐ ┌───────────┐
                              │      │ analysis  │ │ reflection│
                              │      │@trace_node│ │@trace_node│
                              │      └─────┬─────┘ └───────────┘
                              │            │
                              │            ▼
                              │      ┌───────────┐
                              │      │ should_   │
                              │      │ retry_or_ │
                              │      │ end       │
                              │      └─────┬─────┘
                              │            │
                              └────────────┴──── END
```

### 追踪的组件

| 组件 | 追踪类型 | 说明 |
|------|----------|------|
| `analyze()` | `@traceable` | Agent 主入口 |
| `stream_analysis()` | `@traceable` | 流式分析 |
| `product_identification` | `@trace_node` | 产品识别节点 |
| `data_fetch` | `@trace_node` | 数据获取节点 |
| `chart_generation` | `@trace_node` | 图表生成节点 |
| `analysis` | `@trace_node` | 分析节点 |
| `reflection` | `@trace_node` | 反思节点 |
| LLM 调用 | `@trace_llm_call` | 记录 token 使用、模型等 |

---

## API 参考

### TracingConfig

追踪配置类，读取环境变量：

```python
from src.tracing import TracingConfig

# 检查是否启用
if TracingConfig.is_enabled():
    ...

# 配置项
TracingConfig.LANGSMITH_TRACING  # 是否启用 LangSmith
TracingConfig.LANGSMITH_API_KEY  # LangSmith API Key
TracingConfig.LANGSMITH_PROJECT   # LangSmith 项目名
TracingConfig.USE_OTEL           # 是否启用 OpenTelemetry
TracingConfig.OTLP_ENDPOINT      # OTLP 收集器地址
```

### @traceable

方法追踪装饰器：

```python
from src.tracing import traceable

@traceable(name="my.operation", tags=["tag1", "tag2"])
def my_function(arg1, arg2):
    ...
```

### @trace_node

LangGraph 节点追踪装饰器：

```python
from src.tracing import trace_node

@trace_node("node_name")
def my_node(state, **kwargs):
    return {"result": "..."}
```

### @trace_llm_call

LLM 调用追踪装饰器：

```python
from src.tracing import trace_llm_call

@trace_llm_call("my.llm")
def call_llm(prompt):
    response = client.chat.completions.create(...)
    return response  # 自动记录 token 使用
```

### TracingContext

手动追踪上下文管理器：

```python
from src.tracing import TracingContext

with TracingContext("my_operation") as ctx:
    ctx.set_attribute("key", "value")
    # 执行操作
    result = do_something()
    ctx.set_result("success", True)
```

---

## LangSmith 使用

### 查看追踪

1. 访问 https://smith.langchain.com
2. 登录并选择项目 `prediction-agent-dev`
3. 查看每个 `analyze()` 调用的完整链路

### LangSmith 特性

- **自动关联会话** - 使用相同的 `thread_id` 自动关联多轮对话
- **输入/输出记录** - 自动记录函数参数和返回值
- **耗时分析** - 显示每个节点的执行时间
- **错误追踪** - 自动记录异常和堆栈

---

## OpenTelemetry 使用

### 启动 OTEL Collector

```yaml
# otel-collector-config.yaml
receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317
      http:
        endpoint: 0.0.0.0:4318

exporters:
  jaeger:
    endpoint: jaeger:14250
  prometheus:
    endpoint: 0.0.0.0:8889

service:
  pipelines:
    traces:
      receivers: [otlp]
      exporters: [jaeger]
    metrics:
      receivers: [otlp]
      exporters: [prometheus]
```

### 启动 Collector

```bash
docker run -d --name otel-collector \
  -p 4317:4317 -p 4318:4318 -p 8889:8889 \
  -v $(pwd)/otel-collector-config.yaml:/etc/otelcol-contrib/config.yaml \
  otel/opentelemetry-collector-contrib:latest
```

### 配置环境变量

```bash
USE_OTEL=true
OTLP_ENDPOINT=http://localhost:4317
```

---

## 故障排除

### LangSmith 未生效

1. 检查 `LANGSMITH_API_KEY` 是否正确设置
2. 确认 `LANGSMITH_TRACING=true`
3. 查看控制台输出 `[Tracing] LangSmith initialized`

### OpenTelemetry 未生效

1. 确认 OTEL Collector 正在运行
2. 检查 `OTLP_ENDPOINT` 地址是否正确
3. 确认 `USE_OTEL=true`

### 导入错误

```bash
# 确保安装所有依赖
pip install -r requirements.txt

# 如果 langsmith 未安装
pip install langsmith
```

---

## 高级用法

### 禁用追踪

```python
import os
os.environ["LANGSMITH_TRACING"] = "false"
os.environ["USE_OTEL"] = "false"
```

### 自定义追踪

```python
from src.tracing import traceable, trace_node

# 追踪整个方法
@traceable(name="custom.operation", tags=["custom"])
def custom_operation():
    ...

# 追踪 LangGraph 节点
@trace_node("my_custom_node")
def my_custom_node(state, **kwargs):
    ...
```

### 在外部调用中添加追踪

```python
from src.tracing import TracingContext

def my_external_function(data):
    with TracingContext("external.operation") as ctx:
        ctx.set_attribute("data.size", len(data))
        result = process(data)
        ctx.set_attribute("result.count", len(result))
        return result
```

---

## 参考资料

- [LangSmith 文档](https://docs.smith.langchain.com/)
- [OpenTelemetry Python SDK](https://opentelemetry.io/docs/instrumentation/python/)
- [LangGraph 追踪指南](https://python.langchain.com/docs/guides/langsmith/)
