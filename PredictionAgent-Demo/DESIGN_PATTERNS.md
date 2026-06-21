# Prediction Agent 设计模式文档

本文档详细说明 PredictionAgent 项目中使用的设计模式。

---

## 目录

1. [工厂模式 (Factory Pattern)](#1-工厂模式-factory-pattern)
2. [策略模式 (Strategy Pattern)](#2-策略模式-strategy-pattern)
3. [模板方法模式 (Template Method Pattern)](#3-模板方法模式-template-method-pattern)
4. [状态模式 (State Pattern)](#4-状态模式-state-pattern)
5. [单例模式 (Singleton Pattern)](#5-单例模式-singleton-pattern)
6. [适配器模式 (Adapter Pattern)](#6-适配器模式-adapter-pattern)
7. [门面模式 (Facade Pattern)](#7-门面模式-facade-pattern)
8. [Builder 模式](#8-builder-模式)
9. [设计模式应用总结](#9-设计模式应用总结)

---

## 1. 工厂模式 (Factory Pattern)

### 1.1 日志工厂

**位置**: `src/logging_factory.py`

**意图**: 集中管理日志实例的创建，统一日志配置，所有模块共享同一套日志系统。

**实现**:

```python
# 全局初始化标志
_log_initialized = False

def setup_logging(
    log_level: int = logging.DEBUG,
    console_level: int = logging.INFO,
    max_bytes: int = 10 * 1024 * 1024,
    backup_count: int = 5
) -> logging.Logger:
    """
    初始化日志配置（全局只调用一次）
    """
    global _log_initialized

    if _log_initialized:
        return logging.getLogger("PredictionAgent")

    _ensure_log_dir()

    # 日志格式
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    formatter = logging.Formatter(log_format)

    # 文件日志处理器（带轮转）
    file_handler = RotatingFileHandler(
        os.path.join(_LOG_ROOT_DIR, "app.log"),
        encoding="utf-8",
        maxBytes=max_bytes,
        backupCount=backup_count
    )

    # 错误日志单独文件
    error_handler = RotatingFileHandler(
        os.path.join(_LOG_ROOT_DIR, "error.log"),
        encoding="utf-8"
    )

    # 配置根日志记录器
    root_logger = logging.getLogger("PredictionAgent")
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(error_handler)

    _log_initialized = True
    return root_logger

def get_logger(name: str) -> logging.Logger:
    """获取指定名称的日志记录器"""
    if not _log_initialized:
        setup_logging()
    return logging.getLogger(f"PredictionAgent.{name}")
```

**优势**:
- 集中配置，避免重复初始化
- 保证日志系统全局唯一
- 支持模块级别日志命名空间
- 同时输出到控制台和文件

---

## 2. 策略模式 (Strategy Pattern)

### 2.1 LLM 提供者策略

**位置**: `src/llms/base.py`, `src/llms/deepseek.py`, `src/llms/openai_llm.py`

**意图**: 定义一系列算法（LLM providers），它们可以相互替换，让客户端独立于具体实现。

**接口定义**:

```python
class BaseLLM(ABC):
    """LLM基类"""

    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None):
        self.api_key = api_key
        self.model_name = model_name

    @abstractmethod
    def invoke(self, system_prompt: str, user_prompt: str, **kwargs) -> str:
        """调用LLM生成回复"""
        pass

    @abstractmethod
    def get_model_info(self) -> Dict[str, Any]:
        """获取当前模型信息"""
        pass
```

**具体策略实现**:

```python
class DeepSeekLLM(BaseLLM):
    """DeepSeek LLM实现"""

    def invoke(self, system_prompt: str, user_prompt: str, **kwargs) -> str:
        # DeepSeek 特定实现
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
        )
        return response.choices[0].message.content

    def get_model_info(self) -> Dict[str, Any]:
        return {"provider": "deepseek", "model": self.model_name}


class OpenAILLM(BaseLLM):
    """OpenAI LLM实现"""

    def invoke(self, system_prompt: str, user_prompt: str, **kwargs) -> str:
        # OpenAI 特定实现
        pass

    def get_model_info(self) -> Dict[str, Any]:
        return {"provider": "openai", "model": self.model_name}
```

**使用方式**:

```python
# Agent 中根据配置选择策略
def _initialize_llm(self) -> BaseLLM:
    if self.config.default_llm_provider == "deepseek":
        return DeepSeekLLM(api_key=..., model_name=...)
    elif self.config.default_llm_provider == "openai":
        return OpenAILLM(api_key=..., model_name=...)
```

**优势**:
- 可以随时切换 LLM 提供商
- 新增 LLM 提供商只需实现 BaseLLM 接口
- 客户端代码与具体实现解耦

---

## 3. 模板方法模式 (Template Method Pattern)

### 3.1 Agent 分析流程

**位置**: `src/agent_mcp.py`

**意图**: 定义算法骨架（分析流程），将具体步骤延迟到子类或组合对象实现。

```python
def analyze(
    self,
    query: str,
    chart_type: str = "combined",
    use_mock_data: bool = False,
    product_code: Optional[str] = None
) -> Dict[str, Any]:
    """执行预测分析 - 模板方法"""

    self.state = State()
    self.state.user_query = query

    try:
        # Step 1: 产品识别
        self._step_product_identification(query, product_code)

        if not self.state.prediction_state.product_identification.identified:
            raise ValueError("无法识别产品")

        # Step 2: 数据获取
        self._step_data_fetch(use_mock_data)

        # Step 3: 图表生成
        self._step_chart_generation()

        # Step 4: 分析
        self._step_analysis()

        self.state.mark_completed()
        return self._build_response()

    except Exception as e:
        self.state.mark_error(str(e))
        return {"success": False, "error": str(e)}
```

**流程图**:

```
┌─────────────────────────────────────────┐
│              analyze()                    │
│  ┌───────────────────────────────────┐  │
│  │  1. _step_product_identification │──┼──► Node实现
│  │  2. _step_data_fetch            │──┼──► Node实现
│  │  3. _step_chart_generation     │──┼──► MCP调用
│  │  4. _step_analysis             │──┼──► Node实现
│  └───────────────────────────────────┘  │
│                 │                          │
│         ┌───────┴───────┐                  │
│         ▼               ▼                  │
│   ┌──────────┐   ┌──────────┐            │
│   │ Success  │   │  Error   │            │
│   └──────────┘   └──────────┘            │
└─────────────────────────────────────────┘
```

**优势**:
- 算法结构稳定，易于维护
- 具体步骤可扩展（通过组合不同Node）
- 异常处理统一在模板方法中

---

## 4. 状态模式 (State Pattern)

### 4.1 Agent 状态管理

**位置**: `src/state/state.py`

**意图**: 让对象内部状态改变时改变其行为，看起来像是改变了其类。

**状态定义**:

```python
@dataclass
class PredictionState:
    """单个预测分析的状态"""
    step: str = "initial"
    product_identification: ProductIdentificationState = field(default_factory=ProductIdentificationState)
    data_fetch: DataFetchState = field(default_factory=DataFetchState)
    chart_generation: ChartState = field(default_factory=ChartState)
    analysis: AnalysisState = field(default_factory=AnalysisState)

@dataclass
class State:
    """整个Agent的状态"""
    user_query: str = ""
    chart_type: str = "combined"
    prediction_state: PredictionState = field(default_factory=PredictionState)
    is_completed: bool = False
    error_message: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def set_step(self, step: str):
        """设置当前步骤"""
        self.prediction_state.step = step
        self.update_timestamp()

    def mark_completed(self):
        """标记为完成"""
        self.is_completed = True
        self.prediction_state.step = "completed"

    def mark_error(self, error_message: str):
        """标记错误"""
        self.error_message = error_message
        self.prediction_state.step = "error"
```

**状态转换图**:

```
                    ┌──────────┐
                    │ initial  │
                    └────┬─────┘
                         │
                         ▼
              ┌──────────────────────┐
              │product_identification│
              └──────────┬───────────┘
                         │
                         ▼
              ┌──────────────────┐
              │    data_fetch    │
              └────────┬─────────┘
                       │
                       ▼
            ┌────────────────────┐
            │ chart_generation   │
            └────────┬───────────┘
                     │
                     ▼
              ┌────────────┐
              │  analysis  │
              └─────┬──────┘
                    │
          ┌─────────┴─────────┐
          ▼                   ▼
   ┌────────────┐      ┌───────────┐
   │ completed  │      │   error   │
   └────────────┘      └───────────┘
```

**进度计算**:

```python
def get_progress(self) -> float:
    step_weights = {
        "initial": 0,
        "product_identification": 20,
        "data_fetch": 40,
        "chart_generation": 60,
        "analysis": 80,
        "completed": 100,
        "error": 0
    }
    return step_weights.get(self.prediction_state.step, 0)
```

---

## 5. 单例模式 (Singleton Pattern)

### 5.1 日志全局单例

**位置**: `src/logging_factory.py`

**意图**: 确保一个类只有一个实例，并提供一个全局访问点。

```python
_log_initialized = False  # 全局标志

def setup_logging(...):
    global _log_initialized
    if _log_initialized:
        return logging.getLogger("PredictionAgent")
    # 初始化逻辑...
    _log_initialized = True
```

### 5.2 线程本地存储 (Thread-Local Singleton)

**位置**: `src/state/context.py`

```python
from threading import local

_thread_local = local()

def get_current_context() -> Optional[AgentContext]:
    """获取当前上下文"""
    return getattr(_thread_local, 'context', None)

def set_current_context(context: AgentContext):
    """设置当前上下文"""
    _thread_local.context = context

def clear_current_context():
    """清除当前上下文"""
    if hasattr(_thread_local, 'context'):
        del _thread_local.context
```

---

## 6. 适配器模式 (Adapter Pattern)

### 6.1 MCP 客户端适配

**位置**: `src/mcp/client.py`

**意图**: 将不同接口的 MCP 服务（本地/远程）适配成统一接口。

```python
class MCPChartClient:
    """
    MCP图表客户端
    支持本地子进程模式和远程HTTP模式
    """

    def __init__(
        self,
        mode: str = "local",  # local 或 remote
        server_url: str = "http://localhost:8000",
        mcp_server_path: Optional[str] = None
    ):
        self.mode = mode
        self.server_url = server_url

    def plot_sales_forecast(self, ...) -> MCPChartResult:
        """统一的调用入口"""
        if self.mode == "remote":
            return self._call_remote(...)   # HTTP 调用
        else:
            return self._call_local(...)    # 本地调用

    def _call_local(self, ...) -> MCPChartResult:
        """本地模式：直接调用服务"""
        from .chart_mcp_server import ChartMCPService
        service = ChartMCPService(output_dir="output/charts")
        result = service.plot_sales_forecast(...)
        return MCPChartResult(success=result.get("success", False), ...)

    def _call_remote(self, ...) -> MCPChartResult:
        """远程模式：HTTP API调用"""
        response = requests.post(f"{self.server_url}/tools/call", json={...})
        return MCPChartResult(success=response.ok, ...)
```

**适配器优势**:
- 统一接口，调用方无需关心具体实现
- 可动态切换调用模式
- 便于扩展新的调用方式

---

## 7. 门面模式 (Facade Pattern)

### 7.1 Agent 门面

**位置**: `src/agent_mcp.py`

**意图**: 为复杂子系统提供一个统一的高层接口，让子系统更易使用。

```python
class PredictionAgent:
    """预测分析Agent主类 - MCP集成版"""

    def __init__(self, config: Optional[Config] = None):
        # 初始化所有子系统
        self.llm_client = self._initialize_llm()      # LLM模块
        self._initialize_database()                     # 数据库模块
        self._initialize_mcp_client()                  # MCP模块
        self._initialize_nodes()                       # 节点模块
        self.state = State()

    def analyze(self, query: str, ...) -> Dict[str, Any]:
        """简单统一的接口，隐藏内部复杂逻辑"""
        # 内部调用多个子系统完成分析
        pass
```

**门面隐藏的复杂性**:

```
┌─────────────────────────────────────────┐
│        PredictionAgent (Facade)          │
├─────────────────────────────────────────┤
│                                         │
│  ┌─────────────┐  ┌─────────────────┐  │
│  │   LLM 模块  │  │    MCP 模块     │  │
│  │  - DeepSeek │  │  - Local 调用   │  │
│  │  - OpenAI   │  │  - Remote 调用  │  │
│  └─────────────┘  └─────────────────┘  │
│                                         │
│  ┌─────────────┐  ┌─────────────────┐  │
│  │   状态模块  │  │    配置模块     │  │
│  │  - State    │  │  - 环境变量     │  │
│  │  - Context  │  │  - 默认值        │  │
│  └─────────────┘  └─────────────────┘  │
│                                         │
│  ┌─────────────┐  ┌─────────────────┐  │
│  │   节点模块  │  │    日志模块     │  │
│  │  - Product  │  │  - Factory      │  │
│  │  - DataFetch│  │  - Singleton    │  │
│  │  - Chart    │  └─────────────────┘  │
│  │  - Analysis │                        │
│  └─────────────┘                        │
└─────────────────────────────────────────┘
```

**客户端使用**:

```python
# 无需了解内部实现细节
agent = PredictionAgent()
result = agent.analyze(query="预测下季度销售额")
```

---

## 8. Builder 模式

### 8.1 LLM 调用选项构建

**位置**: `src/llms/base.py`

**意图**: 优雅地构建具有可选参数的复杂对象。

```python
class LLMOptions:
    """LLM调用选项"""
    def __init__(self):
        self.temperature: float = 0.7
        self.max_tokens: int = 2048
        self.top_p: float = 1.0
        self.stream: bool = False

class BaseLLM(ABC):
    def invoke(
        self,
        system_prompt: str,
        user_prompt: str,
        **kwargs
    ) -> str:
        """调用LLM，支持可选参数"""
        options = LLMOptions()
        if 'temperature' in kwargs:
            options.temperature = kwargs['temperature']
        if 'max_tokens' in kwargs:
            options.max_tokens = kwargs['max_tokens']
        # 使用options构建请求
        pass
```

### 8.2 响应构建器

```python
def _build_response(self) -> Dict[str, Any]:
    """构建响应 - Builder模式"""
    id_state = self.state.prediction_state.product_identification
    fetch_state = self.state.prediction_state.data_fetch
    chart_state = self.state.prediction_state.chart_generation
    analysis_state = self.state.prediction_state.analysis

    return {
        "success": True,
        "product": {
            "code": id_state.product_code,
            "name": id_state.product_name,
            "confidence": id_state.confidence
        },
        "data": {
            "historical_data": fetch_state.historical_data,
            "future_predictions": fetch_state.future_predictions,
            "statistics": fetch_state.statistics
        },
        "chart": {
            "url": chart_state.chart_url,
            "type": chart_state.chart_type,
            "via_mcp": True
        },
        "analysis": {
            "result": analysis_state.analysis_result,
            "key_insights": analysis_state.key_insights,
            "recommendations": analysis_state.recommendations
        }
    }
```

---

## 9. 设计模式应用总结

### 9.1 模式与组件映射

| 设计模式 | 组件位置 | 作用 |
|---------|---------|------|
| 工厂模式 | `src/logging_factory.py` | 统一创建日志实例 |
| 单例模式 | `src/logging_factory.py`, `src/state/context.py` | 确保日志和上下文唯一 |
| 策略模式 | `src/llms/*` | 支持多 LLM 提供商 |
| 模板方法 | `src/agent_mcp.py` | 定义分析流程骨架 |
| 状态模式 | `src/state/state.py` | 管理 Agent 状态流转 |
| 适配器模式 | `src/mcp/client.py` | 适配本地/远程 MCP 调用 |
| 门面模式 | `src/agent_mcp.py` | 简化复杂子系统调用 |
| Builder 模式 | `src/llms/base.py`, `src/agent_mcp.py` | 构建可选参数和响应 |

### 9.2 架构图

```
┌────────────────────────────────────────────────────────────┐
│                        Client                               │
│                  agent.analyze(query)                       │
└─────────────────────────┬────────────────────────────────────┘
                          │
                          ▼
┌────────────────────────────────────────────────────────────┐
│                     Facade Layer                           │
│                   PredictionAgent                            │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              Template Method: analyze()              │   │
│  │  1. ProductIdentification → Strategy (Node)        │   │
│  │  2. DataFetch              → State Transition      │   │
│  │  3. ChartGeneration        → Adapter (MCP)         │   │
│  │  4. Analysis               → Strategy (Node)       │   │
│  └─────────────────────────────────────────────────────┘   │
└────────────────┬──────────────────────┬────────────────────┘
                 │                      │
    ┌────────────┴───┐    ┌─────────────┴──────────┐
// │  State Module   │    │   SubSystem Module       │
// │  state.py       │    │                          │
// │  ────────────   │    │  ┌─────────────────┐  │
// │  - State        │    │  │ LLM Module      │  │
// │  - Prediction   │    │  │ - Strategy      │  │
// │    State        │    │  │ - DeepSeek      │  │
// │  - Context       │    │  │ - OpenAI        │  │
// │    (Singleton)   │    │  └─────────────────┘  │
// └────────────────┘    │  ┌─────────────────┐  │
//                       │  │ MCP Module      │  │
//                       │  │ - Adapter      │  │
//                       │  │ - Local        │  │
//                       │  │ - Remote       │  │
//                       │  └─────────────────┘  │
//                       │  ┌─────────────────┐  │
//                       │  │ Nodes Module    │  │
//                       │  │ - Product      │  │
//                       │  │ - DataFetch    │  │
//                       │  │ - Chart        │  │
//                       │  │ - Analysis     │  │
//                       │  └─────────────────┘  │
//                       │  ┌─────────────────┐  │
//                       │  │ Logging Module  │  │
//                       │  │ - Factory      │  │
//                       │  │ - Singleton    │  │
//                       │  └─────────────────┘  │
//                       └─────────────────────────┘
```

### 9.3 设计原则遵循

| 原则 | 遵循情况 |
|------|---------|
| 单一职责原则 (SRP) | 每个模块职责单一：日志、状态、LLM、MCP、Nodes |
| 开闭原则 (OCP) | 策略模式使新增 LLM 无需修改客户端 |
| 里氏替换原则 (LSP) | BaseLLM 接口可被任意实现替换 |
| 依赖倒置原则 (DIP) | Agent 依赖抽象 LLMProvider，而非具体实现 |
| 接口隔离原则 (ISP) | LLM 接口精简，只暴露必要方法 |
| 合成复用原则 (CRP) | Agent 通过组合使用各模块 |

---

## 附录：代码示例

### A. 完整使用示例 (Python)

```python
from src.agent_mcp import PredictionAgent, create_agent
from src.logging_factory import setup_logging

# 1. 初始化日志（全局只需一次）
setup_logging()

# 2. 创建 Agent（门面模式）
agent = create_agent()

# 3. 执行分析（模板方法 + 策略 + 状态）
result = agent.analyze(
    query="预测下季度手机销量",
    chart_type="combined",
    use_mock_data=True
)

# 4. 获取结果
if result["success"]:
    print(f"产品: {result['product']['name']}")
    print(f"图表: {result['chart']['url']}")
```

### B. 日志使用示例

```python
from src.logging_factory import get_logger

# 获取模块日志
logger = get_logger(__name__)
logger.info("Agent started")
logger.debug("Debug info")
logger.warning("Warning message")
logger.error("Error occurred", exc_info=True)
```

---

*文档生成时间: 2026-06-21*
