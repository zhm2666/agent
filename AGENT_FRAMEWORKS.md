# 主流 AI Agent 框架详解

> 更新时间: 2026年6月

---

## 目录

1. [Agent 核心概念](#1-agent-核心概念)
2. [ReAct 架构模式](#2-react-架构模式)
3. [主流 Agent 框架](#3-主流-agent-框架)
   - [3.1 LangChain / LangGraph](#31-langchain--langgraph)
   - [3.2 CrewAI](#32-crewai)
   - [3.3 AutoGPT](#33-autogpt)
   - [3.4 Microsoft AutoGen](#34-microsoft-autogen)
   - [3.5 MetaGPT](#35-metagpt)
   - [3.6 OpenHands](#36-openhands)
4. [框架对比选型](#4-框架对比选型)
5. [Agent 架构模式总结](#5-agent-架构模式总结)

---

## 1. Agent 核心概念

### 1.1 什么是 AI Agent

AI Agent（人工智能代理）是一种能够自主感知环境、做出决策并执行行动的智能系统。与传统 LLM 的简单问答不同，Agent 具有以下核心能力：

```
┌─────────────────────────────────────────────────────────┐
│                    AI Agent 核心能力                      │
├─────────────────────────────────────────────────────────┤
│                                                         │
│   ┌─────────┐    ┌─────────┐    ┌─────────┐            │
│   │ 感知    │───▶│ 思考    │───▶│ 行动    │            │
│   │ Perceive│    │ Reason  │    │ Act     │            │
│   └─────────┘    └─────────┘    └─────────┘            │
│        │              │              │                 │
│        └──────────────┴──────────────┘                 │
│                    反馈循环                              │
│                    (Observation)                        │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### 1.2 Agent vs 传统 LLM

| 特性 | 传统 LLM | AI Agent |
|------|----------|----------|
| 交互方式 | 单一问答 | 多轮循环 |
| 工具使用 | 无 | 有（Tool Use） |
| 记忆能力 | 无状态 | 有状态（Memory） |
| 规划能力 | 无 | 有（Planning） |
| 自主性 | 低 | 高 |
| 适用场景 | 问答、生成 | 复杂任务自动化 |

---

## 2. ReAct 架构模式

### 2.1 什么是 ReAct

**ReAct = Reason + Act**

ReAct 是一种让 LLM 进行推理和行动的架构模式，由普林斯顿大学和 Google 在 2023 年提出。它让 Agent 能够：

- **Reason**: 显式推理，理解当前状态
- **Act**: 决定并执行行动
- **Observe**: 观察行动结果

### 2.2 ReAct 工作流程

```
┌─────────────────────────────────────────────────────────────┐
│                     ReAct 循环                              │
│                                                             │
│    ┌──────────┐                                             │
│    │  思考    │  Thought: 我需要做什么？                     │
│    └────┬─────┘                                             │
│         │                                                   │
│         ▼                                                   │
│    ┌──────────┐                                             │
│    │  行动    │  Action: 调用搜索工具                         │
│    └────┬─────┘                                             │
│         │                                                   │
│         ▼                                                   │
│    ┌──────────┐                                             │
│    │  观察    │  Observation: 获取到搜索结果                  │
│    └────┬─────┘                                             │
│         │                                                   │
│         │     ┌─────────────────────────┐                   │
│         └───▶ │  继续循环或结束？       │                   │
│               └─────────────────────────┘                   │
└─────────────────────────────────────────────────────────────┘
```

### 2.3 ReAct 实现代码

#### Python 实现（基础版）

```python
from typing import List, Dict, Any, Callable
import json

class ReActAgent:
    """ReAct 模式 Agent 实现"""

    def __init__(
        self,
        llm: Callable,
        tools: Dict[str, Callable],
        max_iterations: int = 10
    ):
        self.llm = llm
        self.tools = tools
        self.max_iterations = max_iterations

    def run(self, query: str) -> str:
        """执行 ReAct 循环"""

        # 提示模板
        prompt_template = """你是一个智能助手，使用 ReAct 模式解决问题。

可用工具:
{tools}

请按照以下格式回复:
Thought: <你的思考>
Action: <工具名称> [参数 JSON]
Observation: <工具返回结果>

开始执行任务: {query}

如果任务完成，请回复:
Final Answer: <最终答案>
"""

        # 构建工具描述
        tools_desc = "\n".join([
            f"- {name}: {func.__doc__ or '无描述'}"
            for name, func in self.tools.items()
        ])

        messages = []
        current_query = query
        iterations = 0

        while iterations < self.max_iterations:
            iterations += 1

            # 生成思考和行动
            prompt = prompt_template.format(
                tools=tools_desc,
                query=current_query
            )

            response = self.llm(prompt)

            # 解析响应
            if "Final Answer:" in response:
                return response.split("Final Answer:")[1].strip()

            # 提取 Action
            if "Action:" in response:
                action_line = response.split("Action:")[1].split("\n")[0].strip()

                # 解析工具和参数
                parts = action_line.split(" ", 1)
                tool_name = parts[0]
                tool_args = json.loads(parts[1]) if len(parts) > 1 else {}

                # 执行工具
                if tool_name in self.tools:
                    result = self.tools[tool_name](**tool_args)
                    current_query = f"Observation: {result}\n请继续。"
                else:
                    current_query = f"Error: 工具 {tool_name} 不存在，请重试。"

        return "达到最大迭代次数，任务未完成"

# 使用示例
def search(query: str) -> str:
    """搜索信息"""
    return f"搜索结果: 关于 '{query}' 的信息..."

def calculator(expression: str) -> str:
    """计算数学表达式"""
    try:
        result = eval(expression)
        return str(result)
    except:
        return "计算错误"

# 创建 Agent
agent = ReActAgent(
    llm=lambda prompt: "基于 LLM 的响应",  # 实际使用时接入 LLM API
    tools={
        "search": search,
        "calculator": calculator
    }
)

# 执行
result = agent.run("计算 123 * 456 的结果，然后搜索这个结果的含义")
```

#### LangChain ReAct 实现

```python
from langchain.agents import AgentType, initialize_agent
from langchain.llms import OpenAI
from langchain.tools import Tool

# 定义工具
def search(query: str) -> str:
    """搜索网页信息"""
    return f"搜索结果: {query} 相关内容..."

search_tool = Tool(
    name="Search",
    func=search,
    description="用于搜索信息的工具"
)

calculator_tool = Tool(
    name="Calculator",
    func=lambda x: str(eval(x)),
    description="用于数学计算，如: 123 * 456"
)

# 初始化 Agent
llm = OpenAI(temperature=0)
agent = initialize_agent(
    tools=[search_tool, calculator_tool],
    llm=llm,
    agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,  # ReAct 模式
    verbose=True
)

# 执行
result = agent.run("计算 100 + 200 等于多少？")
```

#### LangGraph ReAct 实现（更推荐）

```python
from langgraph.prebuilt import create_react_agent
from langchain_openai import ChatOpenAI

# 创建 LLM
llm = ChatOpenAI(model="gpt-4")

# 定义工具
tools = [
    # ... 工具列表
]

# 创建 ReAct Agent
agent = create_react_agent(llm, tools)

# 执行
result = agent.invoke({
    "messages": [("user", "帮我搜索北京天气，然后告诉我该穿什么衣服")]
})
```

### 2.4 ReAct 提示词模板

```python
REACT_PROMPT = """你是一个智能助手，使用 ReAct (Reasoning + Acting) 模式完成任务。

## 工作流程
1. Thought: 分析当前情况，思考下一步该做什么
2. Action: 选择并执行一个工具
3. Observation: 观察工具返回的结果
4. 重复直到任务完成

## 可用工具
{tools}

## 输出格式
每一步都必须严格按照以下格式输出:

Thought: <你的推理过程>
Action: <工具名称> <参数 JSON>
Observation: <等待工具执行结果>

...

Thought: 我已经得到足够的信息，可以给出最终答案了
Final Answer: <最终答案>

## 开始任务
{input}

{agent_scratchpad}"""
```

---

## 3. 主流 Agent 框架

### 3.1 LangChain / LangGraph

#### 3.1.1 概述

| 指标 | 数据 |
|------|------|
| GitHub Stars | 135,000+ |
| 主要语言 | Python, JavaScript |
| 定位 | 生产级复杂工作流 |
| 学习曲线 | 中高 |

**LangChain** 是最成熟的 LLM 应用框架，**LangGraph** 是其专门为有状态、多代理应用设计的扩展库。

#### 3.1.2 核心特性

```
LangChain / LangGraph 特性
├── 🔗 丰富的集成生态 (100+ 预置工具)
├── 📊 图状工作流 (状态机、循环、人机交互)
├── 🔍 LangSmith 可观测性
├── 💾 记忆系统 (ChatMemory)
├── 🔄 RAG 支持
└── 🏢 企业级 (SOC 2 认证)
```

#### 3.1.3 代码示例

**基础 Agent:**

```python
from langchain.agents import load_tools, initialize_agent, AgentType
from langchain.llms import OpenAI
from langchain.memory import ConversationBufferMemory

# 1. 初始化 LLM
llm = OpenAI(temperature=0)

# 2. 加载工具
tools = load_tools(["serpapi", "llm-math"], llm=llm)

# 3. 创建记忆
memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)

# 4. 初始化 Agent
agent = initialize_agent(
    tools,
    llm,
    agent=AgentType.CONVERSATIONAL_REACT_DESCRIPTION,
    memory=memory,
    verbose=True
)

# 5. 执行
result = agent.run("帮我分析一下苹果公司最近的股价走势")
```

**LangGraph 状态机 Agent:**

```python
from langgraph.graph import StateGraph, END
from typing import TypedDict, Annotated
import operator

# 定义状态
class AgentState(TypedDict):
    messages: Annotated[list, operator.add]
    current_step: str
    query: str
    result: str

# 定义节点
def analyze_node(state: AgentState) -> AgentState:
    """分析阶段"""
    return {"current_step": "analyzed", "result": "分析完成"}

def execute_node(state: AgentState) -> AgentState:
    """执行阶段"""
    return {"current_step": "executed", "result": "执行完成"}

def should_continue(state: AgentState) -> str:
    """判断是否继续"""
    if state["current_step"] == "analyzed":
        return "execute"
    return END

# 构建图
graph = StateGraph(AgentState)

graph.add_node("analyze", analyze_node)
graph.add_node("execute", execute_node)

graph.add_edge("__start__", "analyze")
graph.add_conditional_edges("analyze", should_continue)
graph.add_edge("execute", END)

# 编译
app = graph.compile()

# 执行
result = app.invoke({"messages": [], "current_step": "start", "query": "分析数据", "result": ""})
```

**LangGraph MCP 集成:**

```python
from langgraph.prebuilt import create_react_agent
from langchain_mcp_tools import MCPToolPool

# 连接 MCP 服务器
mcp_pool = MCPToolPool("http://localhost:8000")

# 获取 MCP 工具
mcp_tools = mcp_pool.get_tools()

# 创建 Agent
agent = create_react_agent(llm, mcp_tools)

# 执行
result = agent.invoke({
    "messages": [("user", "生成一张销售预测图表")]
})
```

---

### 3.2 CrewAI

#### 3.2.1 概述

| 指标 | 数据 |
|------|------|
| GitHub Stars | 50,000+ |
| 主要语言 | Python |
| 定位 | 多 Agent 协作 |
| 企业采用 | DocuSign, PwC |

**CrewAI** 是多 Agent 协作领域的首选框架，通过"角色"和"团队"的概念简化多 Agent 编排。

#### 3.2.2 核心概念

```
CrewAI 架构
┌─────────────────────────────────────────────────────────┐
│                      Crew (团队)                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │
│  │  Agent 1    │  │  Agent 2    │  │  Agent 3    │    │
│  │  Researcher │  │  Analyst    │  │  Writer     │    │
│  │  (研究员)   │  │  (分析师)   │  │  (作家)     │    │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘    │
│         │                │                │             │
│         └────────────────┴────────────────┘             │
│                      │                                  │
│              Process (流程)                              │
│         Sequential / Hierarchical / Parallel             │
└─────────────────────────────────────────────────────────┘
```

#### 3.2.3 代码示例

```python
from crewai import Agent, Task, Crew, Process

# 1. 定义 Agent
researcher = Agent(
    role="高级市场研究员",
    goal="收集并分析市场数据，提供洞察",
    backstory="""你是一名资深市场分析师，拥有10年行业研究经验。
    擅长从海量数据中提取关键信息。""",
    verbose=True,
    allow_delegation=False
)

analyst = Agent(
    role="数据分析师",
    goal="基于研究数据生成深度分析",
    backstory="""你专精于数据分析和可视化，
    能够从复杂数据中找出规律和趋势。""",
    verbose=True
)

writer = Agent(
    role="报告撰写专家",
    goal="将分析结果转化为清晰的报告",
    backstory="""你是一名专业的商业报告撰写人，
    擅长用简洁清晰的语言传达复杂信息。""",
    verbose=True
)

# 2. 定义任务
research_task = Task(
    description="收集最近一个季度手机市场的销售数据",
    agent=researcher,
    expected_output="包含销量、品牌份额、趋势的完整报告"
)

analysis_task = Task(
    description="分析研究员收集的数据，找出关键趋势",
    agent=analyst,
    expected_output="包含数据可视化和趋势分析的文档"
)

writing_task = Task(
    description="基于分析结果撰写市场分析报告",
    agent=writer,
    expected_output="一份完整的市场分析报告"
)

# 3. 创建 Crew
crew = Crew(
    agents=[researcher, analyst, writer],
    tasks=[research_task, analysis_task, writing_task],
    process=Process.sequential,  # 顺序执行
    verbose=2
)

# 4. 启动
result = crew.kickoff()

print(result)
```

**Hierarchical Process (层级流程):**

```python
from crewai import Crew, Process

# 团队经理 Agent
manager = Agent(
    role="项目经理",
    goal="协调团队，高效完成任务",
    backstory="经验丰富的项目经理，擅长资源协调和进度把控"
)

# 创建层级 Crew
crew = Crew(
    agents=[manager, researcher, analyst, writer],
    tasks=[research_task, analysis_task, writing_task],
    process=Process.hierarchical,  # 层级流程
    manager_agent=manager  # 指定管理器
)

result = crew.kickoff()
```

---

### 3.3 AutoGPT

#### 3.3.1 概述

| 指标 | 数据 |
|------|------|
| GitHub Stars | 184,000+ |
| 主要语言 | Python |
| 定位 | 自主Agent平台 |
| 特点 | 插件生态、无代码平台 |

**AutoGPT** 是 2023 年的爆款框架，开创了"自主 Agent"概念。2026年已演化为成熟的平台。

#### 3.3.2 核心特性

- **自主执行**: 目标导向的自主任务执行
- **插件系统**: 丰富的预置插件
- **云平台**: AutoGPT Platform 提供托管服务
- **视觉工作流**: 无代码流程构建器

#### 3.3.3 代码示例

```python
# AutoGPT SDK (简化版)
from autogpt import Agent, Plugin

# 定义 Agent
agent = Agent(
    ai_name="ProjectManager",
    ai_role="项目管理者",
    ai_goals=[
        "调研市场竞争格局",
        "制定产品策略",
        "生成执行报告"
    ],
    plugins=[
        Plugin.SEARCH,
        Plugin.WRITE,
        Plugin.BROWSE
    ]
)

# 自主执行
agent.start()

# 使用 LangChain 风格的 Agent
from autogpt.agent import LangChainAgent

agent = LangChainAgent(
    model="gpt-4",
    tools=[search_tool, write_tool],
    goals=["完成市场分析报告"]
)

for step in agent.run():
    print(f"Step {step.number}: {step.thought}")
    if step.is_complete:
        print(f"Result: {step.result}")
```

---

### 3.4 Microsoft AutoGen

#### 3.4.1 概述

| 指标 | 数据 |
|------|------|
| GitHub Stars | 57,500+ |
| 主要语言 | Python |
| 定位 | 多Agent对话 |
| Azure集成 | 深度 |

**AutoGen** 是微软主导的多Agent框架，擅长处理Agent间的复杂对话和协作。

#### 3.4.2 核心概念

```
AutoGen 架构
┌────────────────────────────────────────────────────┐
│                   GroupChat                        │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌───────┐│
│  │ Agent 1 │◀▶│ Agent 2 │◀▶│ Agent 3 │◀▶│  ...  ││
│  └─────────┘  └─────────┘  └─────────┘  └───────┘│
│                                                    │
│            消息传递 / 群聊管理                       │
└────────────────────────────────────────────────────┘
```

#### 3.4.3 代码示例

```python
from autogen import ConversableAgent, GroupChat, GroupChatManager

# 1. 定义 Agent
assistant = ConversableAgent(
    name="assistant",
    system_message="你是一个有帮助的AI助手。",
    llm_config={"model": "gpt-4"}
)

critic = ConversableAgent(
    name="critic",
    system_message="""你是一个专业的批评者。
    你的职责是审查其他Agent的建议，指出问题。""",
    llm_config={"model": "gpt-4"}
)

# 2. 创建群聊
group_chat = GroupChat(
    agents=[assistant, critic],
    messages=[],
    max_round=5
)

# 3. 创建管理器
manager = GroupChatManager(
    groupchat=group_chat,
    llm_config={"model": "gpt-4"}
)

# 4. 启动对话
assistant.initiate_chat(
    manager,
    message="我们需要制定一个新的产品策略，请提出建议。"
)
```

**对话式 Agent:**

```python
from autogen import ConversableAgent

# 用户代理
user_proxy = ConversableAgent(
    name="user",
    human_input_mode="NEVER",  # 或 "ALWAYS" 允许人工输入
    max_consecutive_auto_reply=10
)

# 助手代理
assistant = ConversableAgent(
    name="assistant",
    system_message="你是一个数据分析专家。",
    llm_config={"model": "gpt-4"}
)

# 开始对话
chat_result = user_proxy.initiate_chat(
    assistant,
    message="分析一下这份销售数据: 1月100, 2月150, 3月120"
)
```

---

### 3.5 MetaGPT

#### 3.5.1 概述

| 指标 | 数据 |
|------|------|
| GitHub Stars | 67,500+ |
| 主要语言 | Python |
| 定位 | 软件开发Agent |
| 特点 | SOP驱动 |

**MetaGPT** 创新性地将软件工程的标准操作程序(SOP)引入Agent协作。

#### 3.5.2 核心概念

```
MetaGPT SOP 流程
┌─────────────────────────────────────────────────────┐
│                      用户需求                         │
└───────────────────────┬───────────────────────────────┘
                        ▼
┌─────────────────────────────────────────────────────┐
│                   SOP Pipeline                      │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐ │
│  │Product  │─▶│Architect│─▶│ Engineer│─▶│  QA     │ │
│  │Manager  │  │         │  │         │  │         │ │
│  │  (PM)   │  │         │  │         │  │         │ │
│  └─────────┘  └─────────┘  └─────────┘  └─────────┘ │
│      │                                              │
│      ▼                                              │
│  ┌─────────────────────────────────────────────┐   │
│  │         Structured Output                    │   │
│  │  PRD → Design → Code → Tests → Review      │   │
│  └─────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────┘
```

#### 3.5.3 代码示例

```python
from metagpt.software_company import SoftwareCompany
from metagpt.roles import ProjectManager, Architect, Engineer, QAEvaluator

# 1. 创建软件公司
company = SoftwareCompany()

# 2. 招聘角色
company.hire([
    ProjectManager(),
    Architect(),
    Engineer(),
    QAEvaluator()
])

# 3. 启动项目
company.start_project(
    idea="开发一个待办事项管理应用，支持移动端和Web端"
)

# 4. 运行
company.run(n_round=10)
```

**简化用法:**

```python
from metagpt import MetaGPT

# 一行启动
result = MetaGPT().run(
    idea="创建一个简单的REST API服务",
    repo_path="./my_api_project"
)

# 查看生成结果
print(result)
```

---

### 3.6 OpenHands

#### 3.6.1 概述

| 指标 | 数据 |
|------|------|
| GitHub Stars | 72,100+ |
| 主要语言 | Python |
| 定位 | 通用Agent |
| 特点 | 可扩展、浏览器自动化 |

**OpenHands** 是一个强大的通用Agent框架，擅长浏览器自动化和复杂任务执行。

#### 3.6.2 代码示例

```python
from openhands.agent import Agent
from openhands.tools import Browser, FileEditor, Terminal

# 1. 创建 Agent
agent = Agent(
    tools=[
        Browser(use_api=False),  # 浏览器自动化
        FileEditor(),             # 文件编辑
        Terminal()                # 终端命令
    ],
    model="gpt-4"
)

# 2. 执行任务
result = agent.run("""
    1. 打开浏览器访问 https://example.com
    2. 截取页面截图
    3. 填写表单并提交
    4. 将结果保存到 result.txt
""")

# 3. 获取结果
print(result.output)
print(result.observations)
```

---

## 4. 框架对比选型

### 4.1 横向对比

| 框架 | 多Agent | 状态管理 | 学习曲线 | 生产级 | 工具生态 |
|------|--------|----------|----------|--------|----------|
| **LangChain** | ✅ 有限 | ⚠️ 手动 | 中等 | ✅ | ✅ 丰富 |
| **LangGraph** | ✅ 高级 | ✅ 原生 | 较高 | ✅ | ✅ 丰富 |
| **CrewAI** | ✅ 核心 | ✅ 原生 | 低 | ✅ | ⚠️ 一般 |
| **AutoGPT** | ✅ 协作 | ⚠️ 有限 | 低 | ⚠️ | ✅ 丰富 |
| **AutoGen** | ✅ 核心 | ⚠️ 有限 | 中等 | ✅ | ⚠️ 一般 |
| **MetaGPT** | ✅ SOP | ✅ 原生 | 中等 | ✅ | ⚠️ 垂直 |

### 4.2 选型指南

```
┌─────────────────────────────────────────────────────────────┐
│                      Agent 框架选型                           │
└─────────────────────────────────────────────────────────────┘

你的团队画像:
│
├─▶ Python 团队，追求最大灵活性
│   └─▶ 选择 LangGraph ← 复杂图拓扑的首选
│
├─▶ 需要模拟人类团队协作
│   └─▶ 选择 CrewAI ← 直观的角色扮演模型
│
├─▶ 需要嵌入现有产品
│   ├─▶ 选择 LangChain / LangGraph ← 最广泛的集成生态
│   └─▶ 选择 AutoGen ← 微软生态
│
├─▶ 独立自主Agent（非嵌入产品）
│   └─▶ 选择 AutoGPT ← 自主任务执行
│
├─▶ 软件开发自动化
│   └─▶ 选择 MetaGPT ← SOP驱动
│
├─▶ 浏览器自动化/通用任务
│   └─▶ 选择 OpenHands ← 强大的自动化能力
│
└─▶ 企业级/Azure环境
    └─▶ 选择 AutoGen ← 深度Azure集成
```

### 4.3 场景推荐

| 场景 | 推荐框架 | 原因 |
|------|----------|------|
| RAG + 对话 | LangChain | 最成熟的RAG生态 |
| 多Agent协作 | CrewAI | 角色模型直观 |
| 复杂状态机 | LangGraph | 原生图状态 |
| 自主探索 | AutoGPT | 目标驱动 |
| 对话式协作 | AutoGen | 群聊机制 |
| 软件开发 | MetaGPT | SOP流程 |
| 浏览器自动化 | OpenHands | Action模型 |

---

## 5. Agent 架构模式总结

### 5.1 常见 Agent 模式

```
┌─────────────────────────────────────────────────────────────┐
│                    Agent 架构模式                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────┐   ┌─────────────────┐                │
│  │  ReAct          │   │  Plan-Execute   │                │
│  │  ─────────     │   │  ────────────   │                │
│  │  Thought        │   │  Planner        │                │
│  │    ↓            │   │    ↓            │                │
│  │  Action         │   │  Executor       │                │
│  │    ↓            │   │    ↓            │                │
│  │  Observation    │   │  Feedback       │                │
│  │    ↓            │   │                 │                │
│  │  (循环)         │   │  (循环)         │                │
│  └─────────────────┘   └─────────────────┘                │
│                                                             │
│  ┌─────────────────┐   ┌─────────────────┐                │
│  │  Tool Use       │   │  Memory         │                │
│  │  ────────────   │   │  ─────────────   │                │
│  │                 │   │  Short-term     │                │
│  │  ┌───────────┐  │   │  ┌───────────┐  │                │
│  │  │  LLM      │  │   │  │  Long-term│  │                │
│  │  │  + Tools  │  │   │  │  ┌─────┐  │  │                │
│  │  └───────────┘  │   │  │  │ DB  │  │  │                │
│  │                 │   │  │  └─────┘  │  │                │
│  └─────────────────┘   └─────────────────┘                │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 5.2 Agent 系统架构

```
┌────────────────────────────────────────────────────────────────┐
│                      完整 Agent 系统架构                          │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│    ┌──────────────────────────────────────────────────────┐     │
│    │                    User Interface                     │     │
│    └──────────────────────────────────────────────────────┘     │
│                              │                                  │
│                              ▼                                  │
│    ┌──────────────────────────────────────────────────────┐     │
│    │                   Orchestration Layer                  │     │
│    │  ┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐      │     │
│    │  │ Planner│  │Memory │  │ Tools  │  │ Safety │      │     │
│    │  └────────┘  └────────┘  └────────┘  └────────┘      │     │
│    └──────────────────────────────────────────────────────┘     │
│                              │                                  │
│                              ▼                                  │
│    ┌──────────────────────────────────────────────────────┐     │
│    │                     Core Agent                         │     │
│    │  ┌─────────────────────────────────────────────────┐  │     │
│    │  │              LLM (大脑)                          │  │     │
│    │  │  ┌─────────┐ ┌─────────┐ ┌─────────┐            │  │     │
│    │  │  │ ReAct   │ │ Plan   │ │ Reflect │            │  │     │
│    │  │  └─────────┘ └─────────┘ └─────────┘            │  │     │
│    │  └─────────────────────────────────────────────────┘  │     │
│    └──────────────────────────────────────────────────────┘     │
│                              │                                  │
│                              ▼                                  │
│    ┌──────────────────────────────────────────────────────┐     │
│    │                    External Systems                     │     │
│    │  ┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐       │     │
│    │  │ Database│ │ Search │  │ APIs   │  │ Files  │       │     │
│    │  └────────┘  └────────┘  └────────┘  └────────┘       │     │
│    └──────────────────────────────────────────────────────┘     │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

### 5.3 本项目架构

```
PredictionAgent 架构
┌─────────────────────────────────────────────────────────────┐
│                    PredictionAgent (Go/Python)              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────────────────────────────────────────┐    │
│  │                 Facade / Agent                       │    │
│  │   Template Method: Analyze()                        │    │
│  │   ├── ProductIdentification (Strategy)              │    │
│  │   ├── DataFetch (State)                            │    │
│  │   ├── ChartGeneration (Adapter/MCP)                 │    │
│  │   └── Analysis (Strategy)                          │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              Supporting Modules                      │    │
│  │   ├── Logging (Factory + Singleton)                │    │
│  │   ├── State Management (State Pattern)              │    │
│  │   ├── LLM Providers (Strategy Pattern)             │    │
│  │   └── MCP Client (Adapter Pattern)                 │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 附录 A: 快速入门命令

```bash
# LangChain
pip install langchain langchain-openai

# LangGraph
pip install langgraph

# CrewAI
pip install crewai

# AutoGPT
pip install autogpt

# AutoGen
pip install pyautogen

# MetaGPT
pip install metagpt

# OpenHands
pip install openhands
```

## 附录 B: 参考资源

| 资源 | 链接 |
|------|------|
| LangChain 文档 | https://python.langchain.com |
| LangGraph 文档 | https://langchain-ai.github.io/langgraph/ |
| CrewAI 文档 | https://docs.crewai.com |
| AutoGPT 平台 | https://platform.agpt.co |
| AutoGen 文档 | https://microsoft.github.io/autogen/ |
| MetaGPT 文档 | https://docs.deepwisdom.ai/main/guide/get_started/introduction.html |
| OpenHands 文档 | https://openhands.ai/ |

---

*文档生成时间: 2026-06-21*
