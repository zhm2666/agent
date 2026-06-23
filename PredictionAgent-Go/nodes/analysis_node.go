package nodes

import (
	"context"
	"encoding/json"
	"fmt"
	"strings"

	"prediction-agent/llm"
	"prediction-agent/prompts"
)

// AnalysisNode 分析节点
type AnalysisNode struct {
	*BaseNode
	LLMClient llm.LLMProvider
}

// AnalysisResult 分析结果
type AnalysisResult struct {
	Analyzed        bool     `json:"analyzed"`
	AnalysisResult  string   `json:"analysis_result"`
	KeyInsights     []string `json:"key_insights"`
	Recommendations []string `json:"recommendations"`
}

// NewAnalysisNode 创建分析节点
func NewAnalysisNode(llmClient llm.LLMProvider) *AnalysisNode {
	return &AnalysisNode{
		BaseNode:   NewBaseNode(llmClient, "Analysis"),
		LLMClient: llmClient,
	}
}

// Run 执行分析
func (n *AnalysisNode) Run(ctx context.Context, inputData map[string]any) AnalysisResult {
	productName, _ := inputData["product_name"].(string)
	productCode, _ := inputData["product_code"].(string)
	userQuery, _ := inputData["user_query"].(string)
	chartURL, _ := inputData["chart_url"].(string)
	statistics := n.getMapFromMap(inputData, "statistics")
	futurePredictions := n.getSliceFromMapAny(inputData, "future_predictions")
	historicalData := n.getSliceFromMapAny(inputData, "historical_data")

	n.LogInfo(fmt.Sprintf("正在分析产品: %s", productName))

	// 构建分析上下文
	analysisContext := n.buildAnalysisContext(
		productName, productCode, userQuery,
		historicalData, futurePredictions, statistics,
	)

	contextJSON, _ := json.MarshalIndent(analysisContext, "", "  ")

	systemPrompt := fmt.Sprintf(prompts.SystemPromptDataAnalysis, chartURL, string(contextJSON))
	userPrompt := ""

	resp, err := n.LLMClient.Invoke(ctx, systemPrompt, userPrompt)
	if err != nil {
		n.LogError(fmt.Sprintf("分析失败: %v", err))
		return AnalysisResult{
			Analyzed:       false,
			AnalysisResult: fmt.Sprintf("分析过程中出错: %v", err),
			KeyInsights:    []string{},
			Recommendations: []string{},
		}
	}

	keyInsights := n.extractInsights(resp)
	recommendations := n.extractRecommendations(resp)

	n.LogInfo("分析完成")

	return AnalysisResult{
		Analyzed:        true,
		AnalysisResult:  resp,
		KeyInsights:     keyInsights,
		Recommendations: recommendations,
	}
}

// buildAnalysisContext 构建分析上下文
func (n *AnalysisNode) buildAnalysisContext(
	productName, productCode, userQuery string,
	historicalData, futurePredictions []any,
	statistics map[string]any,
) map[string]any {
	// 截取最近30天的历史数据
	recentHistorical := historicalData
	if len(historicalData) > 30 {
		recentHistorical = historicalData[len(historicalData)-30:]
	}

	return map[string]any{
		"product": map[string]any{
			"name": productName,
			"code": productCode,
		},
		"user_query": userQuery,
		"data_summary": map[string]any{
			"historical_period":     fmt.Sprintf("最近%d天", len(historicalData)),
			"data_points":           len(historicalData),
			"future_predictions_days": len(futurePredictions),
		},
		"historical_data":     recentHistorical,
		"future_predictions": futurePredictions,
		"statistics":         statistics,
	}
}

// extractInsights 提取关键洞察
func (n *AnalysisNode) extractInsights(text string) []string {
	insights := []string{}
	keywords := []string{"洞察", "发现", "关键", "重点", "关键洞察", "值得注意的是"}

	lines := strings.Split(text, "\n")
	for _, line := range lines {
		line = strings.TrimSpace(line)
		if line == "" {
			continue
		}
		for _, keyword := range keywords {
			if strings.Contains(line, keyword) {
				insights = append(insights, line)
				break
			}
		}
	}

	if len(insights) > 5 {
		insights = insights[:5]
	}

	return insights
}

// extractRecommendations 提取建议
func (n *AnalysisNode) extractRecommendations(text string) []string {
	recommendations := []string{}
	keywords := []string{"建议", "措施", "行动", "方案", "优化", "应该"}

	lines := strings.Split(text, "\n")
	for _, line := range lines {
		line = strings.TrimSpace(line)
		if line == "" {
			continue
		}
		for _, keyword := range keywords {
			if strings.Contains(line, keyword) {
				recommendations = append(recommendations, line)
				break
			}
		}
	}

	if len(recommendations) > 5 {
		recommendations = recommendations[:5]
	}

	return recommendations
}

func (n *AnalysisNode) getMapFromMap(m map[string]any, key string) map[string]any {
	if val, ok := m[key].(map[string]any); ok {
		return val
	}
	return map[string]any{}
}

func (n *AnalysisNode) getSliceFromMapAny(m map[string]any, key string) []any {
	if val, ok := m[key].([]any); ok {
		return val
	}
	return []any{}
}
