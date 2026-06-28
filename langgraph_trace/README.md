# LangGraph Trace 实战：分布式追踪聊天机器人

> 用通俗的方式讲解一个带有完整分布式追踪能力的 LangGraph 聊天机器人项目。

---

## 目录

1. [这个项目在解决什么问题](#1-这个项目在解决什么问题)
2. [整体架构：像看地图一样理解系统](#2-整体架构像看地图一样理解系统)
3. [追踪系统：三层 Span 的设计](#3-追踪系统三层-span-的设计)
4. [代码走读：一次对话是如何流转的](#4-代码走读一次对话是如何流转的)
5. [装饰器：零侵入的埋点魔法](#5-装饰器零侵入的埋点魔法)
6. [错误处理：让机器人更健壮](#6-错误处理让机器人更健壮)
7. [配置与启动](#7-配置与启动)
8. [常见问题](#8-常见问题)

---

## 1. 这个项目在解决什么问题

想象你开了一家餐厅，后厨有洗菜、切菜、炒菜、打荷好几个人。你站在前厅，客人点了菜，你怎么知道菜卡在哪一步？

**没有追踪时**：你只知道"客人等了 10 秒还没上菜"，但不知道慢在哪里。

**加上追踪后**：你能在 Jaeger/LangSmith 里看到一条完整的调用链——洗菜 0.5s → 切菜 1s → 炒菜 3s → 打荷 0.2s，哪一步慢一眼就看出来。

这个项目就是一个这样的"餐厅监控系统"，只不过监控的是 AI 聊天机器人的内部调用。

---

## 2. 整体架构：像看地图一样理解系统

```
┌─────────────────────────────────────────────────────────────────┐
│                         外部请求                                  │
│                    POST /chat 或 /chat/stream                     │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                     main.py (FastAPI)                            │
│                   初始化追踪 + 路由分发                           │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                  PureChatbotGraph.invoke()                       │
│                    @trace_graph (root span)                      │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                     LangGraph 图                          │  │
│  │                                                       │  │
│  │   process_input ──► reasoning ──► [条件判断]          │  │
│  │        (span)         (span)     ╱    ╲               │  │
│  │                            tools     respond          │  │
│  │                              ╲        ╱               │  │
│  │                           tool_execution            │  │
│  │                             (span)                    │  │
│  │                                │                      │  │
│  │                               ...                     │  │
│  │                                 └────► generate_response │
│  │                                       (span)           │  │
│  └───────────────────────────────────────────────────────────┘  │
└────────────────────────────┬────────────────────────────────────┘
                             │
              ┌──────────────┴──────────────┐
              │         工具层               │
              │  @trace_tool 修饰的函数      │
              │  search_knowledge_base       │
              │  get_current_time           │
              │  calculate                  │
              │  get_weather                │
              └─────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    追踪数据导出                                  │
│   ┌──────────────────────┐   ┌──────────────────────────────┐  │
│   │  OpenTelemetry (OTLP) │   │       LangSmith              │  │
│   │  → Jaeger / Tempo     │   │  → smith.langchain.com       │  │
│   └──────────────────────┘   └──────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

**简化理解**：
- **Graph（图）**：机器人的"大脑"，定义了处理流程
- **Node（节点）**：流程中的每个步骤（输入处理、推理、工具调用、生成回复）
- **Span（跨度）**：追踪系统里的"计时器"，记录每个步骤的开始、结束、耗时、属性
- **Trace（追踪）**：一次请求从头到尾的所有 Span 串成的链条

---

## 3. 追踪系统：三层 Span 的设计

这是整个项目最核心的设计思想：**三层 Span，自动形成树形结构**。

```
graph.invoke  (root span，根节点)
  │
  ├── node.process_input  (child span)
  ├── node.reasoning      (child span)
  │     └── tool.search_knowledge_base  (grandchild span)
  ├── node.tool_execution  (child span)
  │     ├── tool.calculate
  │     └── tool.get_weather
  └── node.generate_response (child span)
```

为什么这样设计？因为 OpenTelemetry 的 Span 有**父子关系**。当子 Span 创建时，只要当前上下文中有活跃的父 Span，它就会自动成为子 Span，不需要手动指定 parent。

三层分工：

| 层 | 装饰器 | 创建时机 | 记录什么 |
|---|---|---|---|
| **Root** | `@trace_graph` | 整次请求入口（`invoke`/`stream`） | user_id、session_id、用户消息 |
| **Node** | `@trace_node` | 每个 LangGraph 节点执行时 | 输入消息数、输出消息数、用户信息 |
| **Tool** | `@trace_tool` | 每个工具函数调用时 | 工具名、参数、返回值预览 |

---

## 4. 代码走读：一次对话是如何流转的

### 4.1 入口：一条消息进来

用户发 `POST /chat`，消息进入 `main.py` → `chat()` → `graph.invoke()`。

此时 `@trace_graph` 装饰器创建一个 **root span**，名字叫 `graph.invoke`，并把 user_id、session_id、消息内容记录到 span 属性里。

### 4.2 第一站：process_input

```python
@trace_node("process_input")
def process_input(self, state: ChatbotState) -> ChatbotState:
```

这个节点做三件事：
1. 根据 session_id 加载历史消息
2. 如果历史为空，插入系统提示词
3. 把当前用户消息追加进去

`@trace_node` 在进入时记录 `input.message_count`，退出时记录 `output.message_count`，你就能在 Jaeger 里看到"处理前 1 条消息，处理后 3 条消息"。

### 4.3 第二站：reasoning

```python
@trace_node("reasoning")
@retry_on_llm_error(strategy="standard")  # LLM 出错自动重试
def reasoning(self, state: ChatbotState) -> ChatbotState:
    response = self.llm.invoke(state["messages"])
    state["messages"].append(response)
    return state
```

调用 DeepSeek LLM，LLM 决定是要用工具还是直接回复。如果 LLM 说"我要查天气"，就在 `tool_calls` 里留下记录。

### 4.4 岔路口：should_use_tools

这是一个**条件路由函数**，不是节点，不走 `@trace_node`。

```python
def should_use_tools(self, state: ChatbotState):
    last = state["messages"][-1]
    if hasattr(last, 'tool_calls') and last.tool_calls:
        return "tools"
    return "respond"
```

LangGraph 根据返回值决定下一步走哪条边：有工具调用就走 `tool_execution`，没有就走 `generate_response`。

### 4.5 第三站：tool_execution（如果有工具调用）

```python
@trace_tool("search_knowledge_base")    # ← 这个工具也有自己的 span
def search_knowledge_base(query: str, top_k: int = 3):
    ...

@trace_tool("calculate")
def calculate(expression: str):
    ...
```

`@trace_tool` 会记录：
- 工具名
- 调用参数（作为一个 span event，长度截断到 100 字符）
- 返回值预览（前 200 字符）
- 返回值长度

### 4.6 最后一站：generate_response

```python
@trace_node("generate_response")
@retry_on_llm_error(strategy="standard")
def generate_response(self, state: ChatbotState) -> ChatbotState:
    final = self.llm.invoke(state["messages"])
    state["final_response"] = final.content
    return state
```

最终 LLM 生成回复，`final_response` 字段被设置，请求结束。

---

## 5. 装饰器：零侵入的埋点魔法

### 5.1 核心原理

Python 装饰器本质上是一个**函数包装器**：不改变原函数的逻辑，只在它外面包一层额外的行为。

```
原函数：          被装饰后：
process_input     trace_node("process_input") 包裹
  │                    │
  │                    ├── 进入时：创建 span，记录属性
  │                    ├── 执行原函数
  │                    ├── 退出时：设置 span 状态（OK/ERROR）
  │                    └── 异常时：record_exception
  │                    │
  ▼                    ▼
```

### 5.2 三种装饰器对比

```python
# 用于 graph.invoke / graph.stream，整次请求的根 span
@trace_graph(name="graph.invoke")

# 用于 LangGraph 节点，自动找到函数签名里的 state 参数
@trace_node("reasoning")

# 用于工具函数，记录调用参数和返回值
@trace_tool("calculate")
```

### 5.3 智能 state 提取

传统埋点需要手动传 context，装饰器通过**签名自省（introspection）**自动找到：

```python
def _extract_state_from_args(func, args, kwargs):
    sig = inspect.signature(func)        # 拿到函数签名
    bound = sig.bind_partial(*args, ...)  # 绑定实参
    for i, name in enumerate(params):
        if name == "state" and i < len(args):
            return args[i].__dict__        # 自动找到 state
```

所以 `@trace_node` 用在任何节点上都能自动提取 state，不需要业务代码配合。

### 5.4 OTel 优先，自动降级

```python
if TracingConfig.USE_OTEL:
    pass  # 走 OTel 逻辑
elif _langsmith_available:
    return _langsmith_traceable(...)  # 降级到 LangSmith
else:
    return func  # 两个都没有，装饰器就是空操作
```

---

## 6. 错误处理：让机器人更健壮

### 6.1 三层防御

```
第1层：@retry_on_llm_error(strategy="standard")
        LLM 调用失败？指数退避重试 5 次

第2层：@circuit_breaker(failure_threshold=3, recovery_timeout=30)
        连续失败 3 次？熔断 30 秒，暂停工具调用

第3层：@safe_execute(default="服务暂时不可用")
        捕获所有异常，返回降级响应
```

### 6.2 重试策略

| 策略 | 最大次数 | 等待时间公式 |
|---|---|---|
| `fast` | 3 | 0.5 × 2^n 秒，最多 2s |
| `standard` | 5 | 1 × 2^n 秒，最多 10s |
| `slow` | 3 | 5 × 2^n 秒，最多 30s |

### 6.3 熔断器（Circuit Breaker）

```
正常状态 ──► 连续失败 3 次 ──► 熔断打开（30s 内拒绝调用）
    ▲                                    │
    │                                    ▼
    └──────── 30s 后进入 "半开" 状态 ─── 尝试一次
                                            │
                        ┌───────────────────┴───────────────────┐
                        ▼                                       ▼
                   成功 → 恢复正常                          失败 → 继续熔断
```

---

## 7. 配置与启动

### 7.1 环境变量 (.env)

```bash
# LLM
DEEPSEEK_API_KEY=sk-...
DEEPSEEK_MODEL=deepseek-v4-flash

# 追踪开关
USE_OTEL=true               # 开启 OTel（发送给 Jaeger）
LANGSMITH_TRACING=true      # 开启 LangSmith（可选，两者可同时开）

# OpenTelemetry → Jaeger
OTLP_ENDPOINT=http://localhost:4317   # gRPC 端口
OTEL_SERVICE_NAME=langgraph-chatbot  # Jaeger 里的服务名

# LangSmith（可选）
LANGSMITH_API_KEY=lsv2_pt_...
LANGSMITH_PROJECT=demo-trace
```

### 7.2 启动顺序

```bash
# 1. 先启动 Jaeger（或其他 OTLP 接收端）
docker run -d --name jaeger \
  -e COLLECTOR_OTLP_ENABLED=true \
  -p 16686:16686 \
  -p 4317:4317 \
  jaegertracing/all-in-one

# 2. 启动聊天机器人
cd langgraph_trace/src
python main.py
# 或
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 7.3 查看追踪

- **Jaeger UI**：`http://localhost:16686` → 选择 `langgraph-chatbot` 服务 → 点击一条 trace 展开，看到完整的 Span 树
- **LangSmith**：访问你的 LangSmith 项目页面

---

## 8. 常见问题

### Q: 为什么 trace 在 Jaeger 里是分散的 3 条，而不是 1 条？

**原因**：缺少 root span。每个 `@trace_node` 各自创建自己的 root span，互相独立。

**解决**：在 `invoke()` / `stream()` 上加 `@trace_graph(name="graph.invoke")`，它创建根 span，所有节点自动成为子 span。

### Q: 装饰器会影响性能吗？

**几乎不影响**。OTel 的 span 创建是内存操作，不涉及 IO。批量导出（`BatchSpanProcessor`）在后台异步进行，对请求延迟影响在微秒级。

### Q: 可以同时用 Jaeger 和 LangSmith 吗？

**可以**。两者互不冲突，`USE_OTEL=true` 和 `LANGSMITH_TRACING=true` 可以同时开启。LangChain 的回调会自动把 span 抄送一份到 LangSmith。

### Q: 如何给新的工具/节点加追踪？

只需一行装饰器：

```python
# 新工具
@trace_tool("my_new_tool")
def my_new_tool(query: str):
    ...

# 新节点
@trace_node("my_new_node")
def my_new_node(self, state: ChatbotState) -> ChatbotState:
    ...
```

不需要写任何 span、context、flush 的代码。

### Q: 追踪系统可以关闭吗？

可以。将 `.env` 里的 `USE_OTEL=false` 和 `LANGSMITH_TRACING=false` 都设为 false，所有装饰器自动变成空操作（`return func`），零运行时开销。

---

## 项目文件索引

```
langgraph_trace/src/
├── main.py              # FastAPI 入口，追踪初始化
├── middleware.py         # HTTP 级别追踪中间件（可选）
├── .env                 # 所有配置
├── chatbot/
│   ├── state.py         # ChatbotState 数据结构
│   ├── pure_graph.py    # LangGraph 图定义 + 所有节点
│   ├── pure_tools.py    # 4 个工具（带 @trace_tool）
│   ├── error_handling.py # 重试、熔断、降级策略
│   └── session_manager.py # 多会话内存管理
└── tracing/
    ├── config.py        # 环境变量读取
    ├── decorators.py   # @trace_graph / @trace_node / @trace_tool / @traceable
    └── manager.py      # TracingManager 单例，OTel + LangSmith 初始化
```
