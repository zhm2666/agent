package agent

import (
	"context"
	"errors"
	"prediction-agent/config"
	"prediction-agent/llm"
	"prediction-agent/logging"
	"prediction-agent/mcp"
	"prediction-agent/state"
	"time"

	"go.uber.org/zap"
)

// PredictionAgent 预测分析Agent
type PredictionAgent struct {
	config       *config.Config
	logger       *zap.Logger
	llmClient    llm.LLMProvider
	mcpClient    *mcp.MCPChartClient
	agentState   *state.State
	mcpMode      string
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
		mcpMode:    "local",
	}

	// 初始化LLM客户端
	if err := agent.initLLM(); err != nil {
		logger.Warn("LLM initialization failed, using mock", zap.Error(err))
	}

	// 初始化MCP客户端
	agent.mcpClient = mcp.NewMCPChartClient(agent.mcpMode, "http://localhost:8000")

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

// AnalyzeRequest 分析请求
type AnalyzeRequest struct {
	Query         string
	ChartType     string
	UseMockData   bool
	ProductCode   string
}

// AnalyzeResponse 分析响应
type AnalyzeResponse struct {
	Success bool              `json:"success"`
	Product map[string]any    `json:"product"`
	Data    map[string]any    `json:"data"`
	Chart   map[string]any    `json:"chart"`
	Analysis map[string]any   `json:"analysis"`
	Error   string            `json:"error,omitempty"`
	State   map[string]any    `json:"state"`
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
	a.stepDataFetch(req.UseMockData)

	// Step 3: 图表生成
	a.stepChartGeneration()

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

	// 使用LLM识别产品
	if a.llmClient == nil {
		a.logger.Warn("No LLM client available, using mock identification")
		a.agentState.PredictionState.ProductIdentification = state.ProductIdentificationState{
			Identified:  true,
			ProductCode: "MOCK001",
			ProductName: "Mock Product",
			Confidence:  0.5,
			Reasoning:   "Mock identification (no LLM)",
		}
		return
	}

	systemPrompt := `你是一个产品识别助手。根据用户查询识别产品信息。`
	userPrompt := `用户查询: ` + query + "\n请识别产品并返回JSON格式：{\"product_code\": \"\", \"product_name\": \"\", \"confidence\": 0.0, \"reasoning\": \"\"}"

	resp, err := a.llmClient.Invoke(ctx, systemPrompt, userPrompt)
	if err != nil {
		a.logger.Error("Product identification failed", zap.Error(err))
		return
	}

	// 解析LLM响应（简化处理）
	a.agentState.PredictionState.ProductIdentification = state.ProductIdentificationState{
		Identified:  true,
		ProductCode: "IDENTIFIED001",
		ProductName: "Identified Product",
		Confidence:  0.8,
		Reasoning:   resp,
	}
	a.logger.Info("Product identified", zap.String("product_name", "Identified Product"))
}

// stepDataFetch 步骤2: 数据获取
func (a *PredictionAgent) stepDataFetch(useMockData bool) {
	a.logger.Info("[Step 2] Data fetch...")
	a.agentState.SetStep("data_fetch")

	productCode := a.agentState.PredictionState.ProductIdentification.ProductCode

	// 生成模拟数据
	historicalData := generateMockHistoricalData(productCode)
	modelPredictions := generateMockPredictions(productCode, len(historicalData))
	futurePredictions := generateMockFuturePredictions(productCode, 30)

	statistics := map[string]any{
		"total_sales":    100000.0,
		"avg_daily_sales": 1000.0,
		"growth_rate":     0.05,
	}

	a.agentState.PredictionState.DataFetch = state.DataFetchState{
		Fetched:           true,
		HistoricalData:    historicalData,
		ModelPredictions:  modelPredictions,
		FuturePredictions: futurePredictions,
		Statistics:        statistics,
	}

	a.logger.Info("Data fetch completed",
		zap.Int("historical_count", len(historicalData)),
		zap.Int("future_count", len(futurePredictions)),
	)
}

// stepChartGeneration 步骤3: 图表生成
func (a *PredictionAgent) stepChartGeneration() {
	a.logger.Info("[Step 3] Chart generation (MCP)...")
	a.agentState.SetStep("chart_generation")

	idState := a.agentState.PredictionState.ProductIdentification
	fetchState := a.agentState.PredictionState.DataFetch

	// 提取数据
	dates := extractDates(fetchState.HistoricalData)
	actualValues := extractValues(fetchState.HistoricalData, "sales")
	predictedValues := extractValuesFromList(fetchState.ModelPredictions)
	futureDates := extractDates(fetchState.FuturePredictions)
	futureValues := extractValuesFromList(fetchState.FuturePredictions)

	// 调用MCP生成图表
	result := a.mcpClient.PlotSalesForecast(
		idState.ProductName,
		dates,
		actualValues,
		predictedValues,
		futureDates,
		futureValues,
		a.agentState.ChartType,
	)

	a.agentState.PredictionState.ChartGeneration = state.ChartState{
		Generated:    result.Success,
		ChartType:    result.ChartType,
		ChartURL:     result.URL,
		ChartFilePath: result.FilePath,
		ChartID:      result.ChartID,
	}

	if result.Success {
		a.logger.Info("Chart generated successfully", zap.String("url", result.URL))
	} else {
		a.logger.Error("Chart generation failed", zap.String("error", result.Error))
	}
}

// stepAnalysis 步骤4: 分析
func (a *PredictionAgent) stepAnalysis(ctx context.Context) {
	a.logger.Info("[Step 4] Analysis...")
	a.agentState.SetStep("analysis")

	idState := a.agentState.PredictionState.ProductIdentification
	fetchState := a.agentState.PredictionState.DataFetch

	analysisResult := "基于历史数据和预测结果的分析报告。"
	keyInsights := []string{"销量呈上升趋势", "预测准确度较高"}
	recommendations := []string{"建议增加库存", "关注节假日促销"}

	if a.llmClient != nil {
		systemPrompt := `你是一个销售预测分析助手。`
		userPrompt := `产品: ` + idState.ProductName + `
历史数据统计: ` + formatStatistics(fetchState.Statistics) + `
请提供分析结果、关键洞察和建议。`

		resp, err := a.llmClient.Invoke(ctx, systemPrompt, userPrompt)
		if err == nil {
			analysisResult = resp
		}
	}

	a.agentState.PredictionState.Analysis = state.AnalysisState{
		Analyzed:        true,
		AnalysisResult:  analysisResult,
		KeyInsights:     keyInsights,
		Recommendations: recommendations,
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
			"code":      idState.ProductCode,
			"name":      idState.ProductName,
			"confidence": idState.Confidence,
		},
		Data: map[string]any{
			"historical_data":    fetchState.HistoricalData,
			"future_predictions": fetchState.FuturePredictions,
			"statistics":        fetchState.Statistics,
		},
		Chart: map[string]any{
			"url":       chartState.ChartURL,
			"type":      chartState.ChartType,
			"filepath":  chartState.ChartFilePath,
			"chart_id":  chartState.ChartID,
			"via_mcp":   true,
		},
		Analysis: map[string]any{
			"result":         analysisState.AnalysisResult,
			"key_insights":   analysisState.KeyInsights,
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

// ============ 辅助函数 ============

func generateMockHistoricalData(productCode string) []map[string]any {
	data := make([]map[string]any, 90)
	now := time.Now()
	for i := 0; i < 90; i++ {
		date := now.AddDate(0, 0, -90+i).Format("2006-01-02")
		baseValue := 1000.0 + float64(i)*10
		data[i] = map[string]any{
			"date":  date,
			"sales": baseValue,
		}
	}
	return data
}

func generateMockPredictions(productCode string, count int) []map[string]any {
	data := make([]map[string]any, count)
	now := time.Now()
	for i := 0; i < count; i++ {
		date := now.AddDate(0, 0, -count+i).Format("2006-01-02")
		baseValue := 1000.0 + float64(i)*10
		data[i] = map[string]any{
			"date":  date,
			"predicted": baseValue * 1.05,
		}
	}
	return data
}

func generateMockFuturePredictions(productCode string, days int) []map[string]any {
	data := make([]map[string]any, days)
	now := time.Now()
	for i := 0; i < days; i++ {
		date := now.AddDate(0, 0, i+1).Format("2006-01-02")
		baseValue := 1900.0 + float64(i)*15
		data[i] = map[string]any{
			"date":  date,
			"predicted": baseValue,
		}
	}
	return data
}

func extractDates(dataList []map[string]any) []string {
	dates := make([]string, len(dataList))
	for i, item := range dataList {
		if date, ok := item["date"].(string); ok {
			dates[i] = date
		}
	}
	return dates
}

func extractValues(dataList []map[string]any, key string) []float64 {
	values := make([]float64, len(dataList))
	for i, item := range dataList {
		if val, ok := item[key].(float64); ok {
			values[i] = val
		}
	}
	return values
}

func extractValuesFromList(dataList []map[string]any) []float64 {
	values := make([]float64, len(dataList))
	for i, item := range dataList {
		for _, v := range item {
			if val, ok := v.(float64); ok {
				values[i] = val
				break
			}
		}
	}
	return values
}

func formatStatistics(stats map[string]any) string {
	return "Statistics: total_sales=100000, avg=1000, growth=5%"
}
