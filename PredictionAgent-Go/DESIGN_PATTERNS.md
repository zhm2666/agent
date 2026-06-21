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

**位置**: `logging/logger.go` (Go) / `src/logging_factory.py` (Python)

**意图**: 集中管理日志实例的创建，统一日志配置，所有模块共享同一套日志系统。

**Go 实现**:

```go
// 单例模式 + 工厂模式
var (
    _globalLogger *zap.Logger
    _once         sync.Once
)

func Init() error {
    var err error
    _once.Do(func() {
        // 初始化逻辑只执行一次
        _globalLogger, err = config.Build()
    })
    return err
}

func GetLogger(name string) *zap.Logger {
    if _globalLogger == nil {
        Init()
    }
    return _globalLogger.Named(name)
}
```

**Python 实现**:

```python
_log_initialized = False

def setup_logging(log_level=logging.DEBUG, ...):
    global _log_initialized
    if _log_initialized:
        return logging.getLogger("PredictionAgent")

    # 配置日志...
    _log_initialized = True

def get_logger(name: str) -> logging.Logger:
    if not _log_initialized:
        setup_logging()
    return logging.getLogger(f"PredictionAgent.{name}")
```

**优势**:
- 集中配置，避免重复初始化
- 保证日志系统全局唯一
- 支持模块级别日志命名空间

---

## 2. 策略模式 (Strategy Pattern)

### 2.1 LLM 提供者策略

**位置**: `llm/base.go`, `llm/deepseek.go`, `llm/openai.go`

**意图**: 定义一系列算法（LLM providers），它们可以相互替换，让客户端独立于具体实现。

**接口定义**:

```go
// LLMProvider 定义LLM提供者接口
type LLMProvider interface {
    Invoke(ctx context.Context, systemPrompt, userPrompt string, opts ...Option) (string, error)
    GetModelInfo() map[string]string
}
```

**具体策略实现**:

```go
// DeepSeek 策略
type DeepSeekLLM struct {
    apiKey    string
    modelName string
    client    *openai.Client
}

func (l *DeepSeekLLM) Invoke(...) (string, error) {
    // DeepSeek 特定实现
}

// OpenAI 策略
type OpenAILLM struct {
    apiKey    string
    modelName string
    client    *openai.Client
}

func (l *OpenAILLM) Invoke(...) (string, error) {
    // OpenAI 特定实现
}
```

**使用方式**:

```go
// 根据配置选择策略
var llmClient llm.LLMProvider
switch config.DefaultLLMProvider {
case "deepseek":
    llmClient = llm.NewDeepSeekLLM(apiKey, modelName)
case "openai":
    llmClient = llm.NewOpenAILLM(apiKey, modelName)
}
```

**优势**:
- 可以随时切换 LLM 提供商
- 新增 LLM 提供商无需修改现有代码
- 客户端代码与具体实现解耦

---

## 3. 模板方法模式 (Template Method Pattern)

### 3.1 Agent 分析流程

**位置**: `agent/agent.go`

**意图**: 定义算法骨架（分析流程），将具体步骤延迟到子类实现。

```go
func (a *PredictionAgent) Analyze(ctx context.Context, req AnalyzeRequest) AnalyzeResponse {
    // 固定的算法骨架
    a.stepProductIdentification(ctx, req.Query, req.ProductCode)
    if !a.agentState.PredictionState.ProductIdentification.Identified {
        return a.buildErrorResponse("无法识别产品")
    }

    a.stepDataFetch(req.UseMockData)
    a.stepChartGeneration()
    a.stepAnalysis(ctx)

    a.agentState.MarkCompleted()
    return a.buildSuccessResponse()
}
```

**流程图**:

```
┌─────────────────────────────────────────┐
│            Analyze()                    │
│  ┌───────────────────────────────────┐  │
│  │  1. stepProductIdentification()   │──┼──► 识别产品
│  │  2. stepDataFetch()              │──┼──► 获取数据
│  │  3. stepChartGeneration()        │──┼──► 生成图表
│  │  4. stepAnalysis()               │──┼──► 分析结果
│  └───────────────────────────────────┘  │
└─────────────────────────────────────────┘
```

**优势**:
- 算法结构稳定
- 具体步骤可扩展（重写各 step 方法）
- 符合开闭原则

---

## 4. 状态模式 (State Pattern)

### 4.1 Agent 状态管理

**位置**: `state/state.go`

**意图**: 让对象内部状态改变时改变其行为，看起来像是改变了其类。

**状态定义**:

```go
type PredictionState struct {
    Step                    string                      `json:"step"`
    ProductIdentification   ProductIdentificationState `json:"product_identification"`
    DataFetch               DataFetchState              `json:"data_fetch"`
    ChartGeneration         ChartState                  `json:"chart_generation"`
    Analysis                AnalysisState               `json:"analysis"`
}

type State struct {
    UserQuery       string          `json:"user_query"`
    PredictionState PredictionState `json:"prediction_state"`
    IsCompleted    bool            `json:"is_completed"`
    ErrorMessage   string          `json:"error_message"`
}
```

**状态转换**:

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
            │ chart_generation  │
            └────────┬──────────┘
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

```go
func (s *State) GetProgress() float64 {
    stepWeights := map[string]float64{
        "initial":                0,
        "product_identification":  20,
        "data_fetch":             40,
        "chart_generation":       60,
        "analysis":               80,
        "completed":              100,
        "error":                  0,
    }
    return stepWeights[s.PredictionState.Step]
}
```

---

## 5. 单例模式 (Singleton Pattern)

### 5.1 日志全局单例

**位置**: `logging/logger.go`

**意图**: 确保一个类只有一个实例，并提供一个全局访问点。

```go
var (
    _globalLogger *zap.Logger
    _once         sync.Once  // 保证只初始化一次
)

func Init() error {
    var err error
    _once.Do(func() {
        _globalLogger, err = config.Build()
    })
    return err
}
```

**Python 实现**:

```python
_log_initialized = False

def setup_logging(...):
    global _log_initialized
    if _log_initialized:
        return
    # 初始化逻辑...
    _log_initialized = True
```

---

## 6. 适配器模式 (Adapter Pattern)

### 6.1 MCP 客户端适配

**位置**: `mcp/client.go`

**意图**: 将不同接口的 MCP 服务（本地/远程）适配成统一接口。

```go
type MCPChartClient struct {
    Mode      string  // "local" 或 "remote"
    ServerURL string  // 远程服务器地址
}

func (c *MCPChartClient) PlotSalesForecast(...) MCPChartResult {
    if c.Mode == "remote" {
        return c.callRemote(...)   // HTTP 调用
    }
    return c.callLocal(...)        // 本地调用
}
```

**适配器接口统一**:

```go
func (c *MCPChartClient) PlotSalesForecast(...) MCPChartResult {
    // 统一的调用入口
    // 内部适配不同模式
}
```

---

## 7. 门面模式 (Facade Pattern)

### 7.1 Agent 门面

**位置**: `agent/agent.go`

**意图**: 为复杂子系统提供一个统一的高层接口，让子系统更易使用。

```go
type PredictionAgent struct {
    config       *config.Config
    logger       *zap.Logger
    llmClient    llm.LLMProvider
    mcpClient    *mcp.MCPChartClient
    agentState   *state.State
}

// 简单统一的接口，隐藏内部复杂逻辑
resp := predAgent.Analyze(ctx, req)
```

**门面隐藏的复杂性**:

```
┌─────────────────────────────────────────┐
│        PredictionAgent (Facade)        │
├─────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────────┐  │
│  │   LLM 模块  │  │    MCP 模块     │  │
│  │  - DeepSeek │  │  - Local 调用   │  │
│  │  - OpenAI   │  │  - Remote 调用  │  │
│  └─────────────┘  └─────────────────┘  │
│  ┌─────────────┐  ┌─────────────────┐  │
│  │   状态模块  │  │    配置模块     │  │
│  │  - State    │  │  - 环境变量     │  │
│  │  - Context  │  │  - 默认值        │  │
│  └─────────────┘  └─────────────────┘  │
└─────────────────────────────────────────┘
```

**客户端使用**:

```go
// 无需了解内部实现细节
agent, _ := agent.NewPredictionAgent(cfg)
result := agent.Analyze(ctx, AnalyzeRequest{
    Query: "预测下季度销售额",
})
```

---

## 8. Builder 模式

### 8.1 LLM 调用选项

**位置**: `llm/base.go`

**意图**: 优雅地构建具有可选参数的复杂对象。

```go
type Option func(*options)

type options struct {
    temperature float64
    maxTokens   int
}

func WithTemperature(t float64) Option {
    return func(o *options) {
        o.temperature = t
    }
}

func WithMaxTokens(tokens int) Option {
    return func(o *options) {
        o.maxTokens = tokens
    }
}

// 使用方式
resp, err := llm.Invoke(ctx, system, user,
    WithTemperature(0.8),
    WithMaxTokens(1024),
)
```

---

## 9. 设计模式应用总结

### 9.1 模式与组件映射

| 设计模式 | 组件位置 | 作用 |
|---------|---------|------|
| 工厂模式 | `logging/logger.go` | 统一创建日志实例 |
| 单例模式 | `logging/logger.go` | 确保日志系统唯一实例 |
| 策略模式 | `llm/*` | 支持多 LLM 提供商 |
| 模板方法 | `agent/agent.go` | 定义分析流程骨架 |
| 状态模式 | `state/state.go` | 管理 Agent 状态流转 |
| 适配器模式 | `mcp/client.go` | 适配本地/远程 MCP 调用 |
| 门面模式 | `agent/agent.go` | 简化复杂子系统调用 |
| Builder 模式 | `llm/base.go` | 构建可选参数 |

### 9.2 架构图

```
┌────────────────────────────────────────────────────────────┐
│                        Client                               │
│                  agent.Analyze(req)                         │
└─────────────────────────┬────────────────────────────────────┘
                          │
                          ▼
┌────────────────────────────────────────────────────────────┐
│                     Facade Layer                           │
│                   PredictionAgent                           │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              Template Method: Analyze()              │   │
│  │  1. ProductIdentification → Strategy                │   │
│  │  2. DataFetch              → State Transition      │   │
│  │  3. ChartGeneration        → Adapter (MCP)         │   │
│  │  4. Analysis               → Strategy              │   │
│  └─────────────────────────────────────────────────────┘   │
└────────────────┬──────────────────────┬────────────────────┘
                 │                      │
    ┌────────────┴───┐    ┌─────────────┴──────────┐
    │  State Module  │    │   SubSystem Module     │
// │  state.go      │    │                        │
// │  ────────────  │    │  ┌─────────────────┐  │
// │  - Singleton   │    │  │ LLM Module      │  │
// │  - State       │    │  │ - Strategy      │  │
// │    Pattern     │    │  └─────────────────┘  │
// │                │    │  ┌─────────────────┐  │
// │                │    │  │ MCP Module      │  │
// │                │    │  │ - Adapter      │  │
// │                │    │  └─────────────────┘  │
// └────────────────┘    │  ┌─────────────────┐  │
//                       │  │ Logging Module  │  │
//                       │  │ - Factory      │  │
//                       │  │ - Singleton    │  │
//                       │  └─────────────────┘  │
//                       └─────────────────────────┘
```

### 9.3 设计原则遵循

| 原则 | 遵循情况 |
|------|---------|
| 单一职责原则 (SRP) | 每个模块职责单一：日志、状态、LLM、MCP |
| 开闭原则 (OCP) | 策略模式使新增 LLM 无需修改客户端 |
| 里氏替换原则 (LSP) | LLMProvider 接口可被任意实现替换 |
| 依赖倒置原则 (DIP) | Agent 依赖抽象 LLMProvider，而非具体实现 |
| 接口隔离原则 (ISP) | LLM 接口精简，只暴露必要方法 |
| 合成复用原则 (CRP) | Agent 通过组合使用各模块 |

---

## 附录：代码示例

### A. 完整使用示例 (Go)

```go
package main

import (
    "context"
    "prediction-agent/agent"
    "prediction-agent/config"
)

func main() {
    // 1. 加载配置
    cfg := config.LoadConfig()

    // 2. 创建 Agent（门面模式）
    predAgent, _ := agent.NewPredictionAgent(cfg)

    // 3. 执行分析（模板方法 + 策略 + 状态）
    ctx := context.Background()
    resp := predAgent.Analyze(ctx, agent.AnalyzeRequest{
        Query:       "预测下季度手机销量",
        ChartType:   "combined",
        UseMockData: true,
    })

    // 4. 获取结果
    if resp.Success {
        println(resp.Product["name"])
    }
}
```

### B. 日志使用示例

```go
// 获取模块日志
logger := logging.GetLogger("agent")
logger.Info("Agent started")
logger.Debug("Debug info", zap.String("key", "value"))
logger.Error("Error occurred", zap.Error(err))
```

---

*文档生成时间: 2026-06-21*
