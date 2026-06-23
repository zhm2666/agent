package nodes

import (
	"context"
	"fmt"
	"math/rand"
	"time"

	"prediction-agent/llm"
)

// DataFetchNode 数据获取节点
type DataFetchNode struct {
	*BaseNode
	LLMClient llm.LLMProvider
}

// DataFetchResult 数据获取结果
type DataFetchResult struct {
	Fetched          bool              `json:"fetched"`
	HistoricalData   []map[string]any `json:"historical_data"`
	ModelPredictions []map[string]any `json:"model_predictions"`
	FuturePredictions []map[string]any `json:"future_predictions"`
	Statistics       map[string]any   `json:"statistics"`
	ErrorMessage    string            `json:"error_message"`
}

// NewDataFetchNode 创建数据获取节点
func NewDataFetchNode(llmClient llm.LLMProvider) *DataFetchNode {
	return &DataFetchNode{
		BaseNode:   NewBaseNode(llmClient, "DataFetch"),
		LLMClient: llmClient,
	}
}

// Run 执行数据获取
func (n *DataFetchNode) Run(ctx context.Context, inputData map[string]any) DataFetchResult {
	productCode, _ := inputData["product_code"].(string)
	productName, _ := inputData["product_name"].(string)
	historyDays := 90
	futureDays := 30

	if h, ok := inputData["history_days"].(int); ok {
		historyDays = h
	}
	if f, ok := inputData["future_days"].(int); ok {
		futureDays = f
	}

	if productCode == "" {
		return DataFetchResult{
			Fetched:         false,
			HistoricalData:  []map[string]any{},
			ErrorMessage:    "产品代码为空",
		}
	}

	n.LogInfo(fmt.Sprintf("正在获取产品 %s 的数据...", productCode))

	result := n.FetchMockData(productCode, productName, historyDays, futureDays)
	n.LogInfo(fmt.Sprintf("数据获取成功: 历史数据 %d 条, 未来预测 %d 条", 
		len(result.HistoricalData), len(result.FuturePredictions)))

	return result
}

// FetchMockData 生成模拟数据
func (n *DataFetchNode) FetchMockData(productCode, productName string, historyDays, futureDays int) DataFetchResult {
	rand.Seed(time.Now().UnixNano())
	
	historicalData := make([]map[string]any, 0, historyDays)
	futurePredictions := make([]map[string]any, 0, futureDays)
	
	baseValue := float64(rand.Intn(120) + 80)
	trend := 0.3
	
	now := time.Now()
	
	// 生成历史数据
	for i := 0; i < historyDays; i++ {
		d := now.AddDate(0, 0, -historyDays+i)
		
		// 模拟周季节性
		weekdayFactor := 1.2
		if d.Weekday() == 0 || d.Weekday() == 6 {
			weekdayFactor = 0.8
		}
		
		// 模拟随机波动
		noise := 0.9 + rand.Float64()*0.2
		actual := int((baseValue + float64(i)*trend) * weekdayFactor * noise)
		
		// 模拟模型预测
		predicted := float64(actual) * (0.95 + rand.Float64()*0.1)
		
		historicalData = append(historicalData, map[string]any{
			"date":           d.Format("2006-01-02"),
			"actual_value":   actual,
			"predicted_value": predicted,
		})
	}
	
	// 生成未来预测
	for i := 1; i <= futureDays; i++ {
		d := now.AddDate(0, 0, i)
		
		weekdayFactor := 1.2
		if d.Weekday() == 0 || d.Weekday() == 6 {
			weekdayFactor = 0.8
		}
		
		predicted := int((baseValue + float64(historyDays+i)*trend) * weekdayFactor)
		confidence := 0.95 - float64(i)*0.01
		if confidence < 0.7 {
			confidence = 0.7
		}
		
		futurePredictions = append(futurePredictions, map[string]any{
			"date":            d.Format("2006-01-02"),
			"predicted_value": predicted,
			"confidence":      confidence,
		})
	}
	
	// 计算统计信息
	actualValues := make([]float64, 0)
	for _, d := range historicalData {
		if v, ok := d["actual_value"].(int); ok {
			actualValues = append(actualValues, float64(v))
		}
	}
	
	avgDaily := 0.0
	if len(actualValues) > 0 {
		sum := 0.0
		for _, v := range actualValues {
			sum += v
		}
		avgDaily = sum / float64(len(actualValues))
	}
	
	mid := len(actualValues) / 2
	firstHalfAvg := sum(actualValues[:mid])
	secondHalfAvg := sum(actualValues[mid:])
	
	trendChange := 0.0
	if firstHalfAvg > 0 {
		trendChange = ((secondHalfAvg - firstHalfAvg) / firstHalfAvg) * 100
	}
	
	trendDirection := "stable"
	if trendChange > 5 {
		trendDirection = "up"
	} else if trendChange < -5 {
		trendDirection = "down"
	}
	
	statistics := map[string]any{
		"product_code":          productCode,
		"period_days":           historyDays,
		"avg_daily_sales":      avgDaily,
		"trend_change_percent":  trendChange,
		"trend_direction":       trendDirection,
	}
	
	return DataFetchResult{
		Fetched:           true,
		HistoricalData:   historicalData,
		ModelPredictions: []map[string]any{},
		FuturePredictions: futurePredictions,
		Statistics:       statistics,
		ErrorMessage:     "",
	}
}

func sum(values []float64) float64 {
	s := 0.0
	for _, v := range values {
		s += v
	}
	if len(values) > 0 {
		return s / float64(len(values))
	}
	return 0
}
