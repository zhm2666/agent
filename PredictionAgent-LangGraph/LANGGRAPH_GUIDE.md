# LangGraph 完整使用指南

本文档系统讲解 LangGraph 的核心概念和用法，基于 PredictionAgent-LangGraph 项目为例。

---

## 目录

1. [状态管理](#1-状态管理)
2. [节点的定义与注册](#2-节点的定义与注册)
3. [边的构建](#3-边的构建)
4. [条件边与路由](#4-条件边与路由)
5. [thread_id / user_id / session_id](#5-thread_id--user_id--session_id)
6. [Checkpointer 与状态持久化](#6-checkpointer-与状态持久化)
7. [流式执行 stream](#7-流式执行-stream)
8. [图的编译与调用](#8-图的编译与调用)
9. [实战完整示例](#9-实战完整示例)

---

## 1. 状态管理

### 1.1 为什么用 TypedDict 而不是 dataclass

LangGraph 推荐使用 `typing.TypedDict` 定义状态，原因有两个：

**1. 增量更新语义**：LangGraph 按字段名合并状态，TypedDict 显式声明字段名后，节点返回值只需要包含需要修改的字段，LangGraph 会自动 merge。

```python
# TypedDict 定义
class AgentState(TypedDict):
    user_query: str
    step: str
    result: str
```

```python
# 节点A返回部分字段
def node_a(state: AgentState) -> AgentState:
    return {"step": "node_a_done", "result": "hello"}

# 节点B返回另一部分字段
def node_b(state: AgentState) -> AgentState:
    return {"step": "node_b_done", "extra": "world"}

# LangGraph 会自动合并，state = {"step": "node_b_done", "result": "hello", "extra": "world"}
```

如果用 dataclass，LangGraph 需要自己判断哪些字段要更新，容易出错。

**2. 与 LangGraph Platform / LangSmith 集成更好**：TypedDict 的字段名会被 LangSmith 识别，trace 里能直接看到字段名和值。

### 1.2 状态层级设计

复杂 Agent 的状态通常有多层嵌套：

```python
# 产品识别子状态
class ProductIdentificationState(TypedDict):
    identified: bool
    product_code: str
    product_name: str
    confidence: float
    alternatives: list

# 数据获取子状态
class DataFetchState(TypedDict):
    fetched: bool
    historical_data: list
    statistics: dict

# 主状态
class AgentState(TypedDict):
    user_query: str                    # 用户输入
    prediction_state: PredictionState    # 业务子状态
    reflection: ReflectionState         # 反思子状态
    session_id: str                     # 会话标识
    user_id: str                        # 用户标识
    created_at: str                     # 时间戳
```

这样设计的优点：

- **类型安全**：每个子状态独立定义，编辑器能检查字段
- **增量更新**：节点只更新自己负责的子状态，不影响其他子状态
- **可读性好**：状态结构与业务语义对应

### 1.3 节点返回值的规范

节点必须返回 `dict`，LangGraph 会把这个 dict merge 到当前状态里。

```python
# ✅ 正确：返回需要更新的字段
def product_identification_node(state: AgentState) -> dict:
    return {
        "prediction_state": {
            "step": "product_identification",
            "product_identification": {
                "identified": True,
                "product_code": "P001",
                "product_name": "iPhone 15 Pro",
                "confidence": 0.95,
                "alternatives": [],
            }
        }
    }

# ❌ 错误：返回整个状态（会导致其他字段丢失）
def bad_node(state: AgentState) -> AgentState:
    return {
        "step": "done",
        "user_query": state["user_query"],  # 必须保留之前的状态
        ...
    }
```

### 1.4 状态初始值

在调用 `app.invoke()` 之前，需要传入初始状态：

```python
initial_state: AgentState = {
    "user_query": query,
    "chart_type": "combined",
    "prediction_state": {
        "step": "product_identification",
        "product_identification": {...},
        "data_fetch": {...},
        "analysis": {...},
    },
    "reflection": {
        "enabled": True,
        "reflection_count": 0,
        "max_reflections": 5,
        "records": [],
    },
    "session_id": session_id,
    "user_id": user_id,
    "created_at": datetime.now().isoformat(),
    "is_completed": False,
    "error_message": "",
}
```

> 注意：所有 TypedDict 字段必须有初始值，LangGraph 在第一次执行时使用这些值初始化状态。

---

## 2. 节点的定义与注册

### 2.1 节点的签名

节点就是一个 **接受 state、返回部分状态更新** 的 Python 函数：

```python
def node_name(state: AgentState) -> dict:
    # ... 业务逻辑 ...
    return {"key": "updated_value"}
```

LangGraph 内部会把节点包装成 `PregelNode`，管理状态读写。

### 2.2 注册节点到图

```python
from langgraph.graph import StateGraph

builder = StateGraph(AgentState)

# 注册节点，传入节点函数
builder.add_node("product_identification", product_identification_node)
builder.add_node("data_fetch", data_fetch_node)
builder.add_node("chart_generation", chart_node)
builder.add_node("analysis", analysis_node)
```

### 2.3 注入外部依赖

LangGraph 节点只接收 `state`，但实际开发中经常需要注入 `repository`、`llm_client` 等依赖。有两种方式：

**方式 A：用 `functools.partial`**

```python
from functools import partial

def data_fetch_node(state: AgentState, repository) -> dict:
    ...

app_node = partial(data_fetch_node, repository=my_repository)
builder.add_node("data_fetch", app_node)
```

**方式 B：用 `_wrap` 闭包（PredictionAgent-LangGraph 采用的方式）**

```python
def _wrap(node_fn, **fixed_kwargs):
    """把 repository / mcp_client 固定进去，只让 LangGraph 传 state。"""
    def _inner(state: dict) -> dict:
        kwargs = {"state": state, **fixed_kwargs}
        return node_fn(**kwargs)
    return _inner

builder.add_node("data_fetch", _wrap(data_fetch_node, repository=repository))
```

方式 B 更直观，闭包里固定的参数对 LangGraph 透明。

### 2.4 节点设计原则

| 原则 | 说明 | 示例 |
|------|------|------|
| **单一职责** | 一个节点只做一个业务动作 | `product_identification_node` 只做产品识别 |
| **无副作用** | 相同输入 + 相同状态 = 相同输出 | 不依赖全局变量 |
| **幂等性** | 重复执行不会产生副作用 | 节点可以安全重试 |
| **返回部分状态** | 只返回需要更新的字段 | 返回 `{"step": "done"}`，不返回全量状态 |

---

## 3. 边的构建

边是节点之间的连接关系。LangGraph 有三种边：

### 3.1 普通边（固定的下一个节点）

```python
# A 完成后一定去 B，B 完成后一定去 C
builder.add_edge("A", "B")
builder.add_edge("B", "C")
```

对应流程图：

```
A → B → C
```

### 3.2 起始边（图的入口）

```python
# __start__ 是 LangGraph 的虚拟起点节点
builder.add_edge("__start__", "product_identification")
```

### 3.3 终止边（图的出口）

有两种方式表示结束：

**方式 A：用 END**

```python
from langgraph.graph import END

builder.add_edge("analysis", END)
```

**方式 B：条件边返回 "END"**

```python
# 当条件函数返回 "END" 时，图停止执行
builder.add_conditional_edges("analysis", should_finish, {...})
```

### 3.4 完整线性流程的边

```python
builder.add_edge("__start__", "product_identification")
builder.add_edge("product_identification", "data_fetch")
builder.add_edge("data_fetch", "chart_generation")
builder.add_edge("chart_generation", "analysis")
builder.add_edge("analysis", END)
```

对应流程图：

```
__start__ → product_identification → data_fetch → chart_generation → analysis → END
```

---

## 4. 条件边与路由

### 4.1 什么是条件边

条件边不是固定指向某个节点，而是根据当前状态**动态决定**下一个节点：

```python
builder.add_conditional_edges(
    "analysis",                    # 源节点
    should_retry_or_end,          # 路由函数：接收 state，返回下一个节点名
    {
        "END": END,               # 返回 "END" -> 终止
        "data_fetch": "data_fetch",   # 返回 "data_fetch" -> 回到数据获取
        "analysis": "analysis",       # 返回 "analysis" -> 重试分析
    },
)
```

路由函数的签名：

```python
def route_fn(state: AgentState) -> str:
    # 根据 state 决定下一步
    if validation_passed:
        return "END"
    elif can_retry:
        return current_node
    else:
        return "END"
```

### 4.2 条件边的映射表

条件边的第三个参数是一个 **映射字典**：

```
映射字典的 key = 路由函数的返回值
映射字典的 value = 实际要跳转的节点名（或 END）
```

这意味着你可以让路由函数返回逻辑名，然后在映射表里转换成实际节点：

```python
def should_finish(state):
    if state["step"] == "done":
        return "FINISH"     # 逻辑返回值
    return "CONTINUE"

# 映射表
{
    "FINISH": END,           # "FINISH" -> 结束
    "CONTINUE": "next_node", # "CONTINUE" -> 下一个节点
}
```

这样做的好处是路由函数不直接依赖节点名，后续改图结构时只需改映射表。

### 4.3 多条件分支

一个节点可以有多个条件边，分别指向不同的下游：

```python
# 识别节点：可能进入数据获取，也可能要求用户确认
builder.add_conditional_edges(
    "product_identification",
    confidence_router,
    {
        "high_confidence": "data_fetch",      # 置信度高 -> 直接获取数据
        "low_confidence": "human_review",      # 置信度低 -> 人工审核
        "not_found": END,                       # 未识别 -> 结束
    },
)
```

### 4.4 PredictionAgent-LangGraph 的条件边设计

本项目只在 `analysis` 节点后加了条件边：

```python
builder.add_conditional_edges(
    "analysis",
    should_retry_or_end,
    {
        "END": END,
        "product_identification": "product_identification",
        "data_fetch": "data_fetch",
        "chart_generation": "chart_generation",
        "analysis": "analysis",
    },
)
```

对应的路由函数：

```python
def should_retry_or_end(state: AgentState) -> str:
    reflection = state.get("reflection", {})
    current_validation = reflection.get("current_validation") or {}

    # 验证通过 -> 结束
    if current_validation.get("is_valid", True):
        return "END"

    # 验证失败，检查重试次数
    retry_strategy = reflection.get("retry_strategy", {})
    max_retries = retry_strategy.get("max_retries", 3)
    current_attempts = reflection.get("reflection_count", 0)

    if current_attempts < max_retries:
        return state.get("prediction_state", {}).get("step", "analysis")
    return "END"
```

完整图结构：

```
__start__
    │
    ▼
product_identification
    │
    ▼
data_fetch
    │
    ▼
chart_generation
    │
    ▼
analysis ────► should_retry_or_end ◄──┐
    │                                    │
    │  validation passed                 │
    ▼                                    │ retries available
  END ◄──────────────────────────────────┘
```

---

## 5. thread_id / user_id / session_id

这三个标识符在 LangGraph 里有不同的语义和作用层级。

### 5.1 thread_id — LangGraph Runtime 标识

**定义**：LangGraph checkpointer 用来标识一个"对话线程"的唯一 ID。

**作用**：同一个 `thread_id` 多次调用 LangGraph，checkpointer 会自动把状态**接续**上。

**传参方式**：

```python
config = {
    "configurable": {
        "thread_id": "user-123-chat-1",
        "user_id": "user-001",
    }
}

# 第一次调用（冷启动）
final_state = app.invoke(initial_state, config)

# 第二次调用（同一个 thread_id，状态会从上次继续）
# LangGraph 自动从 checkpointer 里恢复状态
final_state = app.invoke(initial_state, config)
```

**多轮对话示例**：

```python
# 第一次问 iPhone
result1 = agent.analyze(
    query="分析 iPhone 15 Pro 的销量",
    thread_id="user-conversation-001",
)
# result1 里已经有产品识别结果

# 第二次追问趋势（同一个 thread_id）
result2 = agent.analyze(
    query="那相比上个月趋势如何？",
    thread_id="user-conversation-001",
)
# checkpointer 自动加载上一次的状态，在其基础上继续执行
```

**LangGraph 内部如何用 thread_id**：

```
app.invoke(initial_state, config)
                        │
                        ▼
              checkpointer.read(thread_id)
                        │
                        ▼
              ┌─────────────────────┐
              │ 如果有保存的状态    │──► 在保存的状态上继续执行
              │ 如果没有保存的状态  │──► 用 initial_state 初始化
              └─────────────────────┘
                        │
                        ▼
                    图执行
                        │
                        ▼
              checkpointer.write(thread_id, state)
```

### 5.2 user_id — 业务用户标识

**定义**：业务层面的用户标识，用于审计、统计、多租户。

**传参方式**：同样放在 `config["configurable"]` 里：

```python
config = {
    "configurable": {
        "thread_id": "chat-123",        # 图执行的线程
        "user_id": "user-001",           # 业务用户 ID
    }
}
```

**user_id 的特殊用法**：

```python
# LangGraph Platform 支持按 user_id 做权限控制
config = {
    "configurable": {
        "thread_id": "...",
        "user_id": "user-001",
        # 其他 metadata
        "tenant_id": "tenant-abc",
        "role": "analyst",
    }
}

# 在 LangSmith Dashboard 里可以按 user_id 过滤 trace
# 便于统计每个用户的调用量、错误率等
```

> 注意：`config["configurable"]` 里的字段都会**透传到 checkpointer**，但只有 `thread_id` 会影响状态恢复逻辑。其他字段（如 `user_id`）只是元数据。

### 5.3 session_id — 应用层会话标识

**定义**：这是**纯业务概念**，不在 LangGraph 原生 API 里定义，但可以通过两种方式透传。

**方式 A：写入 AgentState（PredictionAgent-LangGraph 采用）**

```python
initial_state: AgentState = {
    "session_id": session_id,   # 直接写进状态
    "user_id": user_id,
    ...
}

# 结果里也会带上
result = agent.analyze(query="...", session_id="my-session")
print(result["state"]["session_id"])  # "my-session"
```

**方式 B：用 configurable metadata**

```python
config = {
    "configurable": {
        "thread_id": "chat-123",
        "session_id": "my-session",   # 也放在 configurable 里
    }
}

# checkpointer 会保存，但 LangGraph 本身不处理
```

### 5.4 三者对比总结

| 属性 | 作用域 | 影响状态恢复 | 存放位置 | 用途 |
|------|--------|------------|---------|------|
| **thread_id** | LangGraph Runtime | ✅ 是 | `config["configurable"]` | 多轮对话续跑、断点恢复 |
| **user_id** | 业务/平台层 | ❌ 否 | `config["configurable"]` | 审计、统计、多租户 |
| **session_id** | 应用层 | ❌ 否 | `AgentState` 或 `config` | 业务追踪、前端关联 |

### 5.5 实际调用示例

```python
from src.agent import PredictionAgent

agent = PredictionAgent()

# 场景1：单次分析
result = agent.analyze(
    query="分析 iPhone 的销量",
    thread_id=None,        # 自动生成随机 ID
    session_id=None,       # 不追踪会话
)

# 场景2：Web 应用，多用户场景
result = agent.analyze(
    query="分析 MacBook",
    thread_id=f"chat-{session_id}",   # 同一个浏览器会话用同一个 thread_id
    user_id=request.user_id,            # 当前登录用户
    session_id=session_id,              # 业务会话 ID
)

# 场景3：多轮对话追问
thread = "user-123-multi-turn-001"

result1 = agent.analyze(
    query="iPhone 销量如何？",
    thread_id=thread,
    user_id="user-001",
)
result2 = agent.analyze(
    query="那比小米呢？",
    thread_id=thread,   # 关键：同一个 thread_id
    user_id="user-001",
)
# LangGraph 自动从 checkpointer 恢复 result1 的状态
```

---

## 6. Checkpointer 与状态持久化

### 6.1 什么是 Checkpointer

Checkpointer 是 LangGraph 的**状态持久化后端**。每次图执行结束后，LangGraph 会自动把状态写入 checkpointer；下次用同一个 `thread_id` 调用时，会自动恢复。

```
invoke(thread_id="123", state)
    │
    ├──► checkpointer.read("123") ──► 恢复状态
    │                                   │
    │◄── 继续执行 ◄──────────────────────┘
    │
    ▼
checkpointer.write("123", final_state)
```

### 6.2 内置 Checkpointer

**MemorySaver**（默认，开发用）

```python
from langgraph.checkpoint.memory import MemorySaver

app = builder.compile(checkpointer=MemorySaver())
# 状态存在内存里，进程重启后丢失
```

**PostgresSaver**（生产推荐）

```python
from langgraph.checkpoint.postgres import PostgresSaver

# 方式1：直接传连接字符串
checkpointer = PostgresSaver.from_conn_string("postgresql://user:pass@localhost/db")

# 方式2：传已有的 psycopg2 连接
import psycopg2
conn = psycopg2.connect("postgresql://...")
checkpointer = PostgresSaver(conn)

checkpointer.setup()  # 首次创建表结构
app = builder.compile(checkpointer=checkpointer)
```

**SqliteSaver**（轻量级生产）

```python
from langgraph.checkpoint.sqlite import SqliteSaver

checkpointer = SqliteSaver.from_conn_string("sqlite:///langgraph.db")
app = builder.compile(checkpointer=checkpointer)
```

### 6.3 自定义 Checkpointer

Checkpointer 接口只有两个方法：`get` 和 `put`。

```python
import json
import redis

class RedisCheckpointer:
    def __init__(self, redis_client):
        self.redis = redis_client

    def get(self, config: dict) -> dict | None:
        thread_id = config["configurable"]["thread_id"]
        data = self.redis.get(f"langgraph:{thread_id}")
        if data:
            return json.loads(data)
        return None

    def put(self, config: dict, state: dict) -> None:
        thread_id = config["configurable"]["thread_id"]
        self.redis.set(f"langgraph:{thread_id}", json.dumps(state))

app = builder.compile(checkpointer=RedisCheckpointer(redis_client))
```

### 6.4 状态恢复与查看

```python
# 查看某个 thread_id 的当前状态
state = app.get_state({"configurable": {"thread_id": "chat-123"}})
print(state.values)  # 包含完整状态

# 查看历史版本（checkpoint）
checkpoints = app.get_state_history({"configurable": {"thread_id": "chat-123"}})
for checkpoint in checkpoints:
    print(checkpoint)
```

---

## 7. 流式执行 stream

### 7.1 为什么要流式执行

普通 `invoke()` 等所有节点全部跑完才返回结果。对于耗时长的分析，用户看不到进度。

流式执行 `stream()` 让每个节点完成后立即产出中间结果，前端可以实时渲染进度条。

### 7.2 基本用法

```python
# invoke：等所有节点跑完才返回
final_state = app.invoke(initial_state, config)

# stream：每个节点完成就 yield
for event in app.stream(initial_state, config):
    # event = {节点名: 该节点的输出状态}
    node_name = list(event.keys())[0]
    print(f"节点 {node_name} 执行完成")
```

### 7.3 前端进度展示

```python
def analyze_with_progress(agent, query):
    for event in agent.stream_analysis(query=query):
        node_name = list(event.keys())[0]
        node_state = event[node_name]

        if node_name == "product_identification":
            id_result = node_state.get("prediction_state", {}).get("product_identification", {})
            yield f"产品已识别: {id_result.get('product_name', 'N/A')}"

        elif node_name == "data_fetch":
            fetch = node_state.get("prediction_state", {}).get("data_fetch", {})
            yield f"数据已获取: {len(fetch.get('historical_data', []))} 条"

        elif node_name == "analysis":
            yield "分析完成，正在生成报告..."
```

### 7.4 stream 的返回值结构

```python
for event in app.stream(initial_state, config):
    # event 格式：{节点名: 该节点返回的部分状态}
    print(event)

# 示例输出：
# {"product_identification": {"prediction_state": {"step": "data_fetch", ...}}}
# {"data_fetch": {"prediction_state": {"step": "chart_generation", ...}}}
# {"chart_generation": {"prediction_state": {"step": "analysis", ...}}}
# {"analysis": {"prediction_state": {"step": "completed", ...}}}
```

---

## 8. 图的编译与调用

### 8.1 编译

```python
from langgraph.graph import StateGraph

builder = StateGraph(AgentState)

# 注册节点和边...
builder.add_node("A", node_a)
builder.add_node("B", node_b)
builder.add_edge("__start__", "A")
builder.add_edge("A", "B")
builder.add_edge("B", END)

# 编译：生成可执行的应用
app = builder.compile(
    checkpointer=MemorySaver(),  # 可选，默认无 checkpointer
)
```

### 8.2 调用方式

```python
# 单次调用
final_state = app.invoke(initial_state, config)

# 流式调用
for event in app.stream(initial_state, config):
    ...

# 异步调用（需要 Python 3.10+）
async def run():
    async for event in app.astream(initial_state, config):
        print(event)
```

### 8.3 config 的完整结构

```python
config = {
    "configurable": {
        "thread_id": "chat-001",     # 必须：checkpointer 标识
        "user_id": "user-001",        # 可选：元数据
        "session_id": "sess-abc",       # 可选：业务标识
        "recursion_limit": 100,        # 可选：最大执行步数，默认 25
    },
    "metadata": {
        # 自定义元数据，LangSmith 会记录
        "tenant": "enterprise",
        "environment": "production",
    }
}
```

---

## 9. 实战完整示例

以下是从零构建一个完整 Agent 的代码：

```python
from typing import TypedDict
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph


# ===== 1. 定义状态 =====
class AgentState(TypedDict):
    user_query: str
    step: str
    product_code: str
    product_name: str
    confidence: float
    data: dict
    result: str
    session_id: str
    user_id: str


# ===== 2. 定义节点 =====
def product_identification(state: AgentState) -> dict:
    """识别用户要分析的产品。"""
    # ... LLM 调用逻辑 ...
    return {
        "step": "data_fetch",
        "product_code": "P001",
        "product_name": "iPhone 15 Pro",
        "confidence": 0.95,
    }


def data_fetch(state: AgentState) -> dict:
    """获取产品数据。"""
    # ... 数据库查询逻辑 ...
    return {
        "step": "analysis",
        "data": {"historical": [...], "predictions": [...]},
    }


def analysis(state: AgentState) -> dict:
    """生成分析报告。"""
    # ... LLM 分析逻辑 ...
    return {
        "step": "completed",
        "result": "iPhone 销量呈上升趋势...",
    }


# ===== 3. 定义路由函数 =====
def should_continue(state: AgentState) -> str:
    if state.get("step") == "completed":
        return "END"
    step_map = {
        "product_identification": "data_fetch",
        "data_fetch": "analysis",
        "analysis": "END",
    }
    return step_map.get(state.get("step", ""), "END")


# ===== 4. 构建图 =====
builder = StateGraph(AgentState)

builder.add_node("product_identification", product_identification)
builder.add_node("data_fetch", data_fetch)
builder.add_node("analysis", analysis)

builder.add_edge("__start__", "product_identification")
builder.add_conditional_edges(
    "product_identification",
    should_continue,
    {"data_fetch": "data_fetch", "END": END},
)
builder.add_conditional_edges(
    "data_fetch",
    should_continue,
    {"analysis": "analysis", "END": END},
)
builder.add_edge("analysis", END)

app = builder.compile(checkpointer=MemorySaver())


# ===== 5. 调用 =====
config = {
    "configurable": {
        "thread_id": "user-123-analysis-001",
        "user_id": "user-001",
    }
}

initial_state: AgentState = {
    "user_query": "分析 iPhone 15 Pro 的销量预测",
    "step": "product_identification",
    "product_code": "",
    "product_name": "",
    "confidence": 0.0,
    "data": {},
    "result": "",
    "session_id": "sess-abc",
    "user_id": "user-001",
}

final_state = app.invoke(initial_state, config)
print(final_state["result"])


# ===== 6. 多轮追问 =====
# 用同一个 thread_id，LangGraph 自动续上状态
followup_state = app.invoke(
    {"step": "product_identification", "user_query": "那小米呢？", ...},
    config  # 同一个 thread_id="user-123-analysis-001"
)
```

---

## 附录：LangGraph 常用 API 速查

| API | 说明 |
|-----|------|
| `StateGraph(TypedDict)` | 创建图构建器 |
| `builder.add_node(name, fn)` | 注册节点 |
| `builder.add_edge(from_node, to_node)` | 普通边 |
| `builder.add_edge("__start__", node)` | 起始边 |
| `builder.add_conditional_edges(source, routing_fn, mapping)` | 条件边 |
| `builder.compile(checkpointer=...)` | 编译生成可执行 app |
| `app.invoke(state, config)` | 单次执行 |
| `app.stream(state, config)` | 流式执行 |
| `app.get_state(config)` | 读取当前状态 |
| `app.get_state_history(config)` | 读取状态历史 |
| `app.update_state(config, partial_state)` | 手动更新状态 |
| `MemorySaver()` | 内存 checkpointer |
| `PostgresSaver.from_conn_string(uri)` | PostgreSQL checkpointer |
| `SqliteSaver.from_conn_string(uri)` | SQLite checkpointer |

---

*文档基于 LangGraph >= 0.2.0，生成时间：2026-06-25*
