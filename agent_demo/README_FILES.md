# Agent Demo 项目文件详解

本文档详细说明 `agent_demo/` 项目中每个文件的作用、依赖关系和设计意图。

## 项目概述

这是一个 **FastAPI + LangGraph** 的翻译质检服务，支持多用户会话管理和人工审核（Interrupt）机制，并集成了 **OpenTelemetry** 和 **LangSmith** 分布式追踪。

```
┌─────────────────────────────────────────────────────────────────┐
│                        用户请求                                  │
│                    POST /chat { text }                          │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                     FastAPI (main.py)                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐ │
│  │ HTTP 中间件  │  │ /chat 接口  │  │ /review 接口             │ │
│  │ (追踪所有   │  │ 启动翻译    │  │ 恢复人工审核             │ │
│  │ HTTP 请求)  │  │             │  │                         │ │
│  └─────────────┘  └──────┬──────┘  └───────────┬─────────────┘ │
└─────────────────────────┬───────────────────────┼───────────────┘
                          │                       │
                          ▼                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                   LangGraph (graph.py)                         │
│                                                                 │
│    START ──▶ translate ──▶ evaluate ──┬──▶ END                   │
│                                      │                          │
│                                      └──▶ human_review ──┬──▶ END
│                                                              │
│                                    (interrupt 暂停) ◀────┘     │
│                                                              │
│                        每个节点都带 OpenTelemetry 追踪         │
└─────────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                      追踪系统                                   │
│  ┌──────────────────────┐    ┌──────────────────────────────┐ │
│  │  OpenTelemetry        │    │  LangSmith                    │ │
│  │  (otel_setup.py)      │    │  (@traceable 装饰器)          │ │
│  │  - spans → OTLP      │    │  - runs → LangSmith Cloud     │ │
│  │  - metrics → OTLP    │    │  - 可视化 Dashboard           │ │
│  └──────────────────────┘    └──────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

---

## 文件清单

| 文件 | 类型 | 作用 |
|------|------|------|
| `main.py` | 核心 | FastAPI 应用入口，定义 HTTP 接口 |
| `graph.py` | 核心 | LangGraph 状态图定义（翻译流程） |
| `models.py` | 数据 | Pydantic 请求/响应模型 |
| `database.py` | 数据 | SQLite 数据库操作 |
| `auth.py` | 安全 | 用户认证（Bearer Token） |
| `demo.py` | 演示 | 命令行演示脚本 |
| `requirements.txt` | 配置 | Python 依赖列表 |
| `.env` | 配置 | 环境变量配置 |

### 追踪相关文件

| 文件 | 类型 | 作用 |
|------|------|------|
| `otel_setup.py` | 追踪 | OpenTelemetry 初始化（TracerProvider + MeterProvider） |
| `langgraph_tracing.py` | 追踪 | LangGraph 节点追踪工具类 |
| `tracing.py` | 追踪 | OpenTelemetry + LangSmith 统一管理器 |
| `graph_langsmith.py` | 追踪 | 使用 @traceable 的 LangGraph 版本 |
| `demo_langsmith.py` | 追踪 | LangSmith 演示脚本 |

---

## 核心文件详解

### 1. main.py

**作用**: FastAPI 应用主入口，定义所有 HTTP 接口。

```
用户请求 → FastAPI → HTTP 中间件 → Endpoint → LangGraph → 响应
```

**主要组件**:

| 组件 | 行号 | 说明 |
|------|------|------|
| `lifespan()` | 33-60 | 应用生命周期管理，初始化 DB 和 OpenTelemetry |
| `otel_middleware()` | 74-101 | HTTP 中间件，自动为每个请求创建 trace span |
| `/chat` | 105-191 | 启动翻译任务接口 |
| `/review` | 263-340 | 人工审核后恢复执行接口 |
| `/sessions` | 344-351 | 列出用户会话接口 |
| `/health` | 354-356 | 健康检查接口 |

**追踪集成**:
- 每个 HTTP 请求自动创建 span（通过中间件）
- `/chat` 和 `/review` 端点记录详细参数（user_id, thread_id, decision 等）
- 调用 `graph.invoke()` 执行 LangGraph

---

### 2. graph.py

**作用**: 定义 LangGraph 状态图，包含翻译、评估、人工审核节点。

```
┌─────────────┐
│   START     │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  translate  │  ←── 生成翻译结果
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  evaluate   │  ←── 判断翻译质量
└──────┬──────┘
       │
       ├────────────────┐
       │                │
       ▼                ▼
   [quality=good]   [quality=bad]
       │                │
       ▼                ▼
   ┌───────┐    ┌────────────────┐
   │  END  │    │ human_review  │ ← interrupt() 暂停
   └───────┘    └───────┬────────┘
                         │
                         ├────────────────┐
                         │                │
                         ▼                ▼
                    [approve]         [retry]
                         │                │
                         ▼                │
                     ┌───────┐            │
                     │  END  │◀───────────┘
                     └───────┘
```

**节点说明**:

| 节点 | 函数 | 说明 |
|------|------|------|
| `translate` | `translate()` | 模拟翻译，前 2 次返回差的翻译，第 3 次变好 |
| `evaluate` | `evaluate()` | 判断翻译质量，"good" 或 "bad" |
| `human_review` | `human_review()` | 调用 `interrupt()` 暂停，等待人工决策 |

**追踪集成**:
- 每个节点使用 `tracer.start_as_current_span()` 创建 span
- 记录输入输出属性（text_preview, quality, decision 等）
- 路由函数也带追踪

---

### 3. models.py

**作用**: 定义 Pydantic 数据模型，用于请求验证和响应格式化。

```python
ChatRequest        # /chat 请求参数
ReviewRequest      # /review 请求参数
ChatResponse       # /chat 响应
ReviewResponse     # /review 响应
SessionInfo        # /sessions 响应
```

**字段说明**:

| 模型 | 字段 | 类型 | 说明 |
|------|------|------|------|
| `ChatRequest` | text | str | 待翻译文本 |
| | session_id | str? | 会话 ID（可选） |
| `ReviewRequest` | thread_id | str | LangGraph 线程 ID |
| | decision | str | "retry" 或 "approve" |
| `ChatResponse` | status | str | "completed" 或 "waiting_for_review" |
| | translation | str? | 翻译结果 |
| | review_data | dict? | 中断时返回的审核信息 |

---

### 4. database.py

**作用**: SQLite 数据库操作，管理用户会话和线程映射。

```
┌─────────────────────────────────────────┐
│     conversation_threads 表             │
├─────────────────────────────────────────┤
│ thread_id   TEXT PRIMARY KEY            │
│ user_id     TEXT NOT NULL               │
│ session_id  TEXT NOT NULL               │
│ created_at  TIMESTAMP DEFAULT NOW        │
│ UNIQUE(user_id, session_id)             │
└─────────────────────────────────────────┘
```

**函数说明**:

| 函数 | 作用 |
|------|------|
| `get_connection()` | 获取 SQLite 连接 |
| `init_db()` | 创建表结构 |
| `get_or_create_thread()` | 获取或创建线程 ID（多用户隔离） |
| `list_user_sessions()` | 列出用户的所有会话 |

**追踪集成**:
- 每个 DB 操作创建 span
- 记录 `db.operation`、`db.table`、`user.id` 等属性

---

### 5. auth.py

**作用**: 简单的 Bearer Token 认证。

```
Authorization: Bearer user_kevin
                        │
                        ▼
              验证 token 是否以 "user_" 开头
                        │
                        ▼
              返回 user_id (如 "user_kevin")
```

**追踪集成**:
- 创建 `auth.validate_token` span
- 记录认证结果和 user_id

---

### 6. demo.py

**作用**: 命令行演示脚本，无需启动 HTTP 服务即可测试 LangGraph。

```
python demo.py

输出:
  📤 启动翻译...
  ⏸️ 图已暂停，等待人工审核
  👤 请输入你的决定 (retry/approve): approve
  ✅ 最终结果
```

---

## 追踪文件详解

### 7. otel_setup.py

**作用**: OpenTelemetry 初始化模块，配置 TracerProvider 和 MeterProvider。

```
┌─────────────────────────────────────────────────────────────┐
│                    初始化流程                                │
├─────────────────────────────────────────────────────────────┤
│ 1. 创建 Resource (service_name, version, environment)       │
│ 2. 创建 TracerProvider (AlwaysOnSampler)                   │
│ 3. 添加 OTLP Exporter (BatchSpanProcessor)                │
│ 4. 创建 MeterProvider                                     │
│ 5. 添加 OTLP Metric Exporter                              │
│ 6. 设置全局 Propagator (TraceContext + Baggage)          │
└─────────────────────────────────────────────────────────────┘
```

**导出目标**:
- `OTLP_ENDPOINT` 环境变量指定的收集器
- 数据流: App → OTLP → Collector → Jaeger/Prometheus

---

### 8. langgraph_tracing.py

**作用**: LangGraph 节点追踪工具类，提供装饰器和指标记录。

```python
class LangGraphTracer:
    node_counter      # 节点执行次数 (Counter)
    node_duration     # 节点执行时长 (Histogram)

    trace_node()      # 追踪节点装饰器
    record_router()   # 记录路由决策
    record_graph_invocation()  # 记录图调用
```

---

### 9. tracing.py

**作用**: OpenTelemetry + LangSmith 统一追踪管理器，支持双轨输出。

```
┌─────────────────────────────────────────────────────────────┐
│                   追踪管理器                                 │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  @trace_node("translate")                                   │
│  def translate(state):                                      │
│      ...                                                     │
│                    │                                         │
│        ┌───────────┴───────────┐                            │
│        ▼                       ▼                            │
│  ┌──────────────┐      ┌──────────────┐                    │
│  │ OpenTelemetry │      │  LangSmith   │                    │
│  │   Tracer      │      │  @traceable  │                    │
│  └───────┬───────┘      └──────┬───────┘                    │
│          │                     │                            │
│          ▼                     ▼                            │
│   OTLP → Collector → Jaeger   LangSmith Cloud               │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

### 10. graph_langsmith.py

**作用**: 使用 LangSmith `@traceable` 装饰器的 LangGraph 版本。

```python
@traceable(name="translate", tags=["langgraph-node"])
def translate(state: State) -> dict:
    # 自动追踪输入输出到 LangSmith
    ...
```

**与 graph.py 的区别**:
- 使用 `@traceable` 而非手动 `tracer.start_as_current_span()`
- 直接输出到 LangSmith，无需配置 OTLP
- 可在 https://smith.langchain.com 查看可视化追踪

---

### 11. demo_langsmith.py

**作用**: 使用 `graph_langsmith.py` 的演示脚本，输出到 LangSmith。

```bash
python demo_langsmith.py

# 访问 https://smith.langchain.com 查看追踪
```

---

## 依赖关系图

```
main.py
├── models.py           (数据模型)
├── database.py         (数据库)
├── auth.py            (认证)
├── graph.py           (状态图)
├── langgraph_tracing.py  (追踪工具)
├── otel_setup.py      (OTEL 初始化)
└── langgraph.types    (Command, interrupt)

demo.py
├── graph.py
└── otel_setup.py

graph_langsmith.py      (独立版本)
├── langsmith.run_helpers  (@traceable)
└── langgraph.types

tracing.py
├── opentelemetry SDK
└── langsmith SDK
```

---

## 配置说明

### .env

```bash
# LangSmith (分布式追踪平台)
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=lsv2_pt_...
LANGSMITH_PROJECT=translation-agent-dev

# OpenTelemetry (可选)
OTLP_ENDPOINT=http://localhost:4317

# 开关
USE_LANGSMITH=true   # 是否启用 LangSmith
USE_OTEL=false       # 是否启用 OpenTelemetry
```

### requirements.txt

| 包 | 用途 |
|---|------|
| `fastapi` | Web 框架 |
| `uvicorn` | ASGI 服务器 |
| `langgraph` | 状态图/Agent 框架 |
| `langsmith` | LangSmith 追踪 |
| `opentelemetry-*` | 分布式追踪 |
| `aiosqlite` | SQLite 异步驱动 |
| `python-dotenv` | 环境变量加载 |
| `PyJWT` | JWT 认证 |

---

## 运行方式

### 方式 1: HTTP 服务

```bash
pip install -r requirements.txt
python main.py
# 或
uvicorn main:app --reload --port 8000

# 测试
curl -X POST http://localhost:8000/chat \
  -H "Authorization: Bearer user_test" \
  -H "Content-Type: application/json" \
  -d '{"text": "你好世界"}'
```

### 方式 2: 命令行演示

```bash
# LangSmith 追踪版
python demo_langsmith.py

# OpenTelemetry 追踪版
python demo.py
```

### 方式 3: Docker

```dockerfile
FROM python:3.10
COPY . /app
WORKDIR /app
RUN pip install -r requirements.txt
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## 追踪数据流向

### OpenTelemetry 路径

```
┌─────────┐     OTLP gRPC      ┌────────────┐     OTLP      ┌─────────┐
│ App     │ ─────────────────▶ │  Collector │ ────────────▶ │ Jaeger  │
│ spans   │     :4317         │  (Go版)    │   :4317       │ UI      │
└─────────┘                   └────────────┘               └─────────┘
                                       │
                                       ▼
                                  ┌─────────┐
                                  │Prometheus│
                                  │ :8889    │
                                  └─────────┘
```

### LangSmith 路径

```
┌─────────┐     HTTPS        ┌─────────────────┐
│ App     │ ────────────────▶ │ LangSmith Cloud │
│ @trace  │   api.langchain.com │ smith.langchain.com │
└─────────┘                   └─────────────────┘
                                   │
                                   ▼
                              ┌─────────┐
                              │Dashboard│
                              └─────────┘
```

---

## 调试技巧

### 查看 LangSmith 追踪

1. 访问 https://smith.langchain.com
2. 登录你的账号
3. 选择项目 `translation-agent-dev`
4. 查看每个 run 的输入/输出/耗时

### 查看 OpenTelemetry (Jaeger)

1. 启动 OTEL Collector
2. 访问 http://localhost:16686
3. 选择服务 `agent-demo`
4. 查看 Trace 瀑布图

### 禁用追踪

```bash
# 禁用所有追踪
USE_LANGSMITH=false
USE_OTEL=false
python main.py
```
