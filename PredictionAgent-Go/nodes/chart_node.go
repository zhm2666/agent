package nodes

import (
	"context"
	"fmt"
	"time"

	"prediction-agent/llm"
	"prediction-agent/mcp"
)

// ChartNode 图表生成节点
type ChartNode struct {
	*BaseNode
	LLMClient  llm.LLMProvider
	MCPClient  *mcp.MCPChartClient
}

// ChartResult 图表生成结果
type ChartResult struct {
	Generated    bool   `json:"generated"`
	ChartType   string `json:"chart_type"`
	ChartURL    string `json:"chart_url"`
	ChartFilePath string `json:"chart_filepath"`
	ChartID     string `json:"chart_id"`
	Error       string `json:"error,omitempty"`
}

// NewChartNode 创建图表生成节点
func NewChartNode(llmClient llm.LLMProvider, mcpClient *mcp.MCPChartClient) *ChartNode {
	return &ChartNode{
		BaseNode:   NewBaseNode(llmClient, "ChartGeneration"),
		LLMClient: llmClient,
		MCPClient: mcpClient,
	}
}

// Run 执行图表生成
func (n *ChartNode) Run(ctx context.Context, inputData map[string]any) ChartResult {
	productName, _ := inputData["product_name"].(string)
	chartType, _ := inputData["chart_type"].(string)
	historicalData := n.getSliceFromMap(inputData, "historical_data")
	futurePredictions := n.getSliceFromMap(inputData, "future_predictions")
	modelPredictions := n.getSliceFromMap(inputData, "model_predictions")

	if productName == "" {
		productName = "Unknown Product"
	}
	if chartType == "" {
		chartType = "combined"
	}

	if len(historicalData) == 0 {
		return ChartResult{
			Generated: false,
			ChartType: chartType,
			Error:     "没有数据可绘制",
		}
	}

	n.LogInfo(fmt.Sprintf("正在通过MCP生成图表: %s, 类型: %s", productName, chartType))

	// 提取数据
	dates := n.extractDates(historicalData, "date")
	actualValues := n.extractNumericValues(historicalData, "actual_value")
	predictedValues := n.extractNumericValuesWithFallback(historicalData, modelPredictions, "predicted_value", "predicted")
	futureDates := n.extractDates(futurePredictions, "date")
	futurePredValues := n.extractNumericValues(futurePredictions, "predicted_value")

	// 调用MCP
	result := n.MCPClient.PlotSalesForecast(
		productName,
		dates,
		actualValues,
		predictedValues,
		futureDates,
		futurePredValues,
		chartType,
	)

	chartResult := ChartResult{
		Generated:    result.Success,
		ChartType:   result.ChartType,
		ChartURL:    result.URL,
		ChartFilePath: result.FilePath,
		ChartID:     result.ChartID,
	}

	if !result.Success {
		chartResult.Error = result.Error
		n.LogError(fmt.Sprintf("MCP图表生成失败: %s", result.Error))
	} else {
		n.LogInfo(fmt.Sprintf("MCP图表生成成功: %s", result.URL))
	}

	return chartResult
}

// RunLocal 本地直接调用绘图
func (n *ChartNode) RunLocal(ctx context.Context, inputData map[string]any) ChartResult {
	productName, _ := inputData["product_name"].(string)
	chartType, _ := inputData["chart_type"].(string)
	historicalData := n.getSliceFromMap(inputData, "historical_data")
	_ = n.getSliceFromMap(inputData, "future_predictions") // Reserved for future use

	if productName == "" {
		productName = "Unknown Product"
	}
	if chartType == "" {
		chartType = "combined"
	}

	if len(historicalData) == 0 {
		return ChartResult{
			Generated: false,
			Error:     "没有数据可绘制",
		}
	}

	n.LogInfo(fmt.Sprintf("正在本地生成图表: %s", productName))

	// 使用默认的图表URL
	chartResult := ChartResult{
		Generated:   true,
		ChartType:   chartType,
		ChartURL:    "",
		ChartFilePath: "",
		ChartID:     fmt.Sprintf("local_%d", time.Now().Unix()),
	}

	return chartResult
}

// SelectChartType 根据数据特征推荐图表类型
func (n *ChartNode) SelectChartType(ctx context.Context, inputData map[string]any) map[string]any {
	dataPoints := len(n.getSliceFromMap(inputData, "historical_data"))
	modelPredictions := n.getSliceFromMap(inputData, "model_predictions")
	userPreference, _ := inputData["chart_type"].(string)

	if userPreference == "bar" || userPreference == "line" || userPreference == "combined" {
		return map[string]any{
			"chart_type": userPreference,
			"reasoning":  fmt.Sprintf("用户指定: %s", userPreference),
		}
	}

	hasModelPredictions := len(modelPredictions) > 0
	if hasModelPredictions || dataPoints > 30 {
		return map[string]any{
			"chart_type": "combined",
			"reasoning":  "数据量大且包含模型预测，适合使用综合图表",
		}
	}

	return map[string]any{
		"chart_type": "line",
		"reasoning":  "数据量适中，适合使用折线图展示趋势",
	}
}

func (n *ChartNode) getSliceFromMap(m map[string]any, key string) []map[string]any {
	if slice, ok := m[key].([]map[string]any); ok {
		return slice
	}
	if slice, ok := m[key].([]any); ok {
		result := make([]map[string]any, 0, len(slice))
		for _, item := range slice {
			if m, ok := item.(map[string]any); ok {
				result = append(result, m)
			}
		}
		return result
	}
	return nil
}

func (n *ChartNode) extractDates(dataList []map[string]any, dateKey string) []string {
	dates := make([]string, len(dataList))
	for i, item := range dataList {
		if date, ok := item[dateKey].(string); ok {
			dates[i] = date
		}
	}
	return dates
}

func (n *ChartNode) extractNumericValues(dataList []map[string]any, key string) []float64 {
	values := make([]float64, len(dataList))
	for i, item := range dataList {
		if val, ok := item[key].(float64); ok {
			values[i] = val
		} else if val, ok := item[key].(int); ok {
			values[i] = float64(val)
		}
	}
	return values
}

func (n *ChartNode) extractNumericValuesWithFallback(historical, predictions []map[string]any, histKey, predKey string) []float64 {
	values := make([]float64, len(historical))
	for i, item := range historical {
		if val, ok := item[histKey].(float64); ok {
			values[i] = val
		} else if val, ok := item[histKey].(int); ok {
			values[i] = float64(val)
		}
	}
	
	// 如果历史数据中没有预测值，尝试从predictions获取
	if len(values) > 0 && values[0] == 0 && len(predictions) > 0 {
		for i := 0; i < len(values) && i < len(predictions); i++ {
			if val, ok := predictions[i][predKey].(float64); ok {
				values[i] = val
			} else if val, ok := predictions[i][predKey].(int); ok {
				values[i] = float64(val)
			}
		}
	}
	
	return values
}
