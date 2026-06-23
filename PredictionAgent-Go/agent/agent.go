package agent

import (
	"context"
	"errors"
	"prediction-agent/config"
	"prediction-agent/llm"
	"prediction-agent/logging"
	"prediction-agent/mcp"
	"prediction-agent/nodes"
	"prediction-agent/state"

	"go.uber.org/zap"
)

// PredictionAgent 预测分析Agent
type PredictionAgent struct {
	config               *config.Config
	logger               *zap.Logger
	llmClient           llm.LLMProvider
	mcpClient           *mcp.MCPChartClient
	agentState          *state.State
	mcpMode             string
	
	// Nodes
	productIDNode        *nodes.ProductIdentificationNode
	dataFetchNode       *nodes.DataFetchNode
	chartNode           *nodes.ChartNode
	analysisNode        *nodes.AnalysisNode
}

// NewPredictionAgent 创建Agent实例
func NewPredictionAgent(cfg *config.Config) (*PredictionAgent, error) {
	// 初始化日志
	if err := logging.Init(); err != nil {
		return nil, err
	}

	logger := logging.GetLogger("agent")

	agent := &PredictionAgent{
		config:    cfg,
		logger:    logger,
		agentState: state.NewState(),
		mcpMode:   "local",
	}

	// 初始化LLM客户端
	if err := agent.initLLM(); err != nil {
		logger.Warn("LLM initialization failed", zap.Error(err))
	}

	// 初始化MCP客户端
	agent.mcpClient = mcp.NewMCPChartClient(agent.mcpMode, "http://localhost:8000")

	// 初始化Nodes
	agent.initNodes()

	logger.Info("Prediction Agent initialized",
		zap.String("llm_provider", cfg.DefaultLLMProvider),
		zap.String("mcp_mode", agent.mcpMode),
	)

	return agent, nil
}

// initLLM 初始化LLM客户端
func (a *PredictionAgent) initLLM() error {
	var llmClient llm.LLMProvider

	switch a.config.DefaultLLMProvider {
	case "deepseek":
		if a.config.DeepSeekAPIKey == "" {
			return errors.New("DeepSeek API key not provided")
		}
		llmClient = llm.NewDeepSeekLLM(a.config.DeepSeekAPIKey, a.config.DeepSeekModel)
	case "openai":
		if a.config.OpenAIAPIKey == "" {
			return errors.New("OpenAI API key not provided")
		}
		llmClient = llm.NewOpenAILLM(a.config.OpenAIAPIKey, a.config.OpenAIModel)
	default:
		return errors.New("unsupported LLM provider: " + a.config.DefaultLLMProvider)
	}

	a.llmClient = llmClient
	a.logger.Info("LLM client initialized", zap.Any("model_info", llmClient.GetModelInfo()))
	return nil
}

// initNodes 初始化处理节点
func (a *PredictionAgent) initNodes() {
	a.productIDNode = nodes.NewProductIdentificationNode(a.llmClient)
	a.dataFetchNode = nodes.NewDataFetchNode(a.llmClient)
	a.chartNode = nodes.NewChartNode(a.llmClient, a.mcpClient)
	a.analysisNode = nodes.NewAnalysisNode(a.llmClient)
	
	a.logger.Info("Nodes initialized",
		zap.String("product_identification", a.productIDNode.NodeName),
		zap.String("data_fetch", a.dataFetchNode.NodeName),
		zap.String("chart", a.chartNode.NodeName),
		zap.String("analysis", a.analysisNode.NodeName),
	)
}

// AnalyzeRequest 分析请求
type AnalyzeRequest struct {
	Query       string
	ChartType   string
	UseMockData bool
	ProductCode string
}

// AnalyzeResponse 分析响应
type AnalyzeResponse struct {
	Success  bool              `json:"success"`
	Product  map[string]any    `json:"product"`
	Data     map[string]any    `json:"data"`
	Chart    map[string]any    `json:"chart"`
	Analysis map[string]any    `json:"analysis"`
	Error    string            `json:"error,omitempty"`
	State    map[string]any    `json:"state"`
}

// Analyze 执行预测分析
func (a *PredictionAgent) Analyze(ctx context.Context, req AnalyzeRequest) AnalyzeResponse {
	a.logger.Info("Starting prediction analysis",
		zap.String("query", req.Query),
		zap.String("chart_type", req.ChartType),
	)

	// 重置状态
	a.agentState = state.NewState()
	a.agentState.UserQuery = req.Query
	a.agentState.ChartType = req.ChartType

	// Step 1: 产品识别
	a.stepProductIdentification(ctx, req.Query, req.ProductCode)

	if !a.agentState.PredictionState.ProductIdentification.Identified {
		a.logger.Error("Product identification failed")
		return a.buildErrorResponse("无法识别产品，请提供更具体的产品信息")
	}

	// Step 2: 数据获取
	a.stepDataFetch(ctx, req.UseMockData)

	// Step 3: 图表生成
	a.stepChartGeneration(ctx)

	// Step 4: 分析
	a.stepAnalysis(ctx)

	a.agentState.MarkCompleted()
	a.logger.Info("Prediction analysis completed")

	return a.buildSuccessResponse()
}

// stepProductIdentification 步骤1: 产品识别
func (a *PredictionAgent) stepProductIdentification(ctx context.Context, query, productCode string) {
	a.logger.Info("[Step 1] Product identification...")
	a.agentState.SetStep("product_identification")

	// 如果提供了产品代码，直接使用
	if productCode != "" {
		a.agentState.PredictionState.ProductIdentification = state.ProductIdentificationState{
			Identified:  true,
			ProductCode: productCode,
			ProductName: "Product " + productCode,
			Confidence:  1.0,
			Reasoning:   "Direct product code provided",
		}
		a.logger.Info("Product identified by code", zap.String("product_code", productCode))
		return
	}

	// 使用节点进行产品识别
	if a.productIDNode == nil {
		a.logger.Warn("Product ID node not available, using mock")
		a.agentState.PredictionState.ProductIdentification = state.ProductIdentificationState{
			Identified:  true,
			ProductCode: "MOCK001",
			ProductName: "Mock Product",
			Confidence:  0.5,
			Reasoning:   "Mock identification (no node)",
		}
		return
	}

	result := a.productIDNode.Run(ctx, map[string]any{
		"user_query": query,
	})

	a.agentState.PredictionState.ProductIdentification = state.ProductIdentificationState{
		Identified:  result.Identified,
		ProductCode: result.ProductCode,
		ProductName: result.ProductName,
		Confidence:  result.Confidence,
		Reasoning:   result.Reasoning,
	}

	if result.Identified {
		a.logger.Info("Product identified", 
			zap.String("product_name", result.ProductName),
			zap.Float64("confidence", result.Confidence),
		)
	}
}

// stepDataFetch 步骤2: 数据获取
func (a *PredictionAgent) stepDataFetch(ctx context.Context, useMockData bool) {
	a.logger.Info("[Step 2] Data fetch...")
	a.agentState.SetStep("data_fetch")

	productCode := a.agentState.PredictionState.ProductIdentification.ProductCode
	productName := a.agentState.PredictionState.ProductIdentification.ProductName

	if a.dataFetchNode == nil {
		a.logger.Warn("Data fetch node not available, using mock data")
		a.useMockDataFetch(productCode, productName)
		return
	}

	result := a.dataFetchNode.Run(ctx, map[string]any{
		"product_code": productCode,
		"product_name": productName,
		"history_days": 90,
		"future_days": 30,
	})

	a.agentState.PredictionState.DataFetch = state.DataFetchState{
		Fetched:          result.Fetched,
		HistoricalData:   result.HistoricalData,
		ModelPredictions: result.ModelPredictions,
		FuturePredictions: result.FuturePredictions,
		Statistics:      result.Statistics,
	}

	if result.Fetched {
		a.logger.Info("Data fetch completed",
			zap.Int("historical_count", len(result.HistoricalData)),
			zap.Int("future_count", len(result.FuturePredictions)),
		)
	} else {
		a.logger.Error("Data fetch failed", zap.String("error", result.ErrorMessage))
	}
}

// useMockDataFetch 使用模拟数据
func (a *PredictionAgent) useMockDataFetch(productCode, productName string) {
	result := a.dataFetchNode.FetchMockData(productCode, productName, 90, 30)
	
	a.agentState.PredictionState.DataFetch = state.DataFetchState{
		Fetched:          result.Fetched,
		HistoricalData:   result.HistoricalData,
		ModelPredictions: result.ModelPredictions,
		FuturePredictions: result.FuturePredictions,
		Statistics:      result.Statistics,
	}
}

// stepChartGeneration 步骤3: 图表生成
func (a *PredictionAgent) stepChartGeneration(ctx context.Context) {
	a.logger.Info("[Step 3] Chart generation (MCP)...")
	a.agentState.SetStep("chart_generation")

	if a.chartNode == nil {
		a.logger.Warn("Chart node not available, using mock")
		a.agentState.PredictionState.ChartGeneration = state.ChartState{
			Generated: true,
			ChartType: "combined",
			ChartURL:  "",
		}
		return
	}

	idState := a.agentState.PredictionState.ProductIdentification
	fetchState := a.agentState.PredictionState.DataFetch

	result := a.chartNode.Run(ctx, map[string]any{
		"product_name":      idState.ProductName,
		"chart_type":       a.agentState.ChartType,
		"historical_data":   fetchState.HistoricalData,
		"future_predictions": fetchState.FuturePredictions,
		"model_predictions": fetchState.ModelPredictions,
	})

	a.agentState.PredictionState.ChartGeneration = state.ChartState{
		Generated:    result.Generated,
		ChartType:   result.ChartType,
		ChartURL:    result.ChartURL,
		ChartFilePath: result.ChartFilePath,
		ChartID:     result.ChartID,
	}

	if result.Generated {
		a.logger.Info("Chart generated successfully", zap.String("url", result.ChartURL))
	} else {
		a.logger.Error("Chart generation failed", zap.String("error", result.Error))
	}
}

// stepAnalysis 步骤4: 分析
func (a *PredictionAgent) stepAnalysis(ctx context.Context) {
	a.logger.Info("[Step 4] Analysis...")
	a.agentState.SetStep("analysis")

	if a.analysisNode == nil {
		a.logger.Warn("Analysis node not available, using mock")
		a.agentState.PredictionState.Analysis = state.AnalysisState{
			Analyzed:        true,
			AnalysisResult:  "基于历史数据和预测结果的分析报告。",
			KeyInsights:    []string{"销量呈上升趋势", "预测准确度较高"},
			Recommendations: []string{"建议增加库存", "关注节假日促销"},
		}
		return
	}

	idState := a.agentState.PredictionState.ProductIdentification
	fetchState := a.agentState.PredictionState.DataFetch
	chartState := a.agentState.PredictionState.ChartGeneration

	result := a.analysisNode.Run(ctx, map[string]any{
		"product_name":       idState.ProductName,
		"product_code":       idState.ProductCode,
		"user_query":        a.agentState.UserQuery,
		"historical_data":    fetchState.HistoricalData,
		"future_predictions": fetchState.FuturePredictions,
		"statistics":        fetchState.Statistics,
		"chart_url":         chartState.ChartURL,
	})

	a.agentState.PredictionState.Analysis = state.AnalysisState{
		Analyzed:        result.Analyzed,
		AnalysisResult:  result.AnalysisResult,
		KeyInsights:    result.KeyInsights,
		Recommendations: result.Recommendations,
	}

	a.logger.Info("Analysis completed")
}

// buildSuccessResponse 构建成功响应
func (a *PredictionAgent) buildSuccessResponse() AnalyzeResponse {
	idState := a.agentState.PredictionState.ProductIdentification
	fetchState := a.agentState.PredictionState.DataFetch
	chartState := a.agentState.PredictionState.ChartGeneration
	analysisState := a.agentState.PredictionState.Analysis

	return AnalyzeResponse{
		Success: true,
		Product: map[string]any{
			"code":       idState.ProductCode,
			"name":       idState.ProductName,
			"confidence": idState.Confidence,
		},
		Data: map[string]any{
			"historical_data":    fetchState.HistoricalData,
			"future_predictions": fetchState.FuturePredictions,
			"statistics":        fetchState.Statistics,
		},
		Chart: map[string]any{
			"url":      chartState.ChartURL,
			"type":     chartState.ChartType,
			"filepath":  chartState.ChartFilePath,
			"chart_id": chartState.ChartID,
			"via_mcp":  true,
		},
		Analysis: map[string]any{
			"result":          analysisState.AnalysisResult,
			"key_insights":    analysisState.KeyInsights,
			"recommendations": analysisState.Recommendations,
		},
		State: a.agentState.ToMap(),
	}
}

// buildErrorResponse 构建错误响应
func (a *PredictionAgent) buildErrorResponse(errMsg string) AnalyzeResponse {
	a.agentState.MarkError(errMsg)
	return AnalyzeResponse{
		Success: false,
		Error:   errMsg,
		State:   a.agentState.ToMap(),
	}
}

// GetProgress 获取进度
func (a *PredictionAgent) GetProgress() map[string]any {
	return map[string]any{
		"step":         a.agentState.PredictionState.Step,
		"progress":     a.agentState.GetProgress(),
		"is_completed": a.agentState.IsCompleted,
	}
}

// SaveState 保存状态
func (a *PredictionAgent) SaveState(filepath string) error {
	return a.agentState.SaveToFile(filepath)
}

// LoadState 加载状态
func (a *PredictionAgent) LoadState(filepath string) error {
	loadedState, err := state.LoadFromFile(filepath)
	if err != nil {
		return err
	}
	a.agentState = loadedState
	return nil
}

// GetState 获取当前状态
func (a *PredictionAgent) GetState() *state.State {
	return a.agentState
}
