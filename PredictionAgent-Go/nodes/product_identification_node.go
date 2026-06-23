package nodes

import (
	"context"
	"encoding/json"
	"fmt"
	"strings"

	"prediction-agent/llm"
	"prediction-agent/prompts"
)

// ProductIdentificationNode 产品识别节点
type ProductIdentificationNode struct {
	*BaseNode
	LLMClient llm.LLMProvider
}

// ProductIdentificationResult 产品识别结果
type ProductIdentificationResult struct {
	Identified    bool              `json:"identified"`
	ProductCode   string            `json:"product_code"`
	ProductName   string            `json:"product_name"`
	Confidence    float64           `json:"confidence"`
	Reasoning    string            `json:"reasoning"`
	Alternatives []map[string]any  `json:"alternatives"`
}

// NewProductIdentificationNode 创建产品识别节点
func NewProductIdentificationNode(llmClient llm.LLMProvider) *ProductIdentificationNode {
	return &ProductIdentificationNode{
		BaseNode:   NewBaseNode(llmClient, "ProductIdentification"),
		LLMClient: llmClient,
	}
}

// Run 执行产品识别
func (n *ProductIdentificationNode) Run(ctx context.Context, inputData map[string]any) ProductIdentificationResult {
	userQuery, _ := inputData["user_query"].(string)

	if userQuery == "" {
		return ProductIdentificationResult{
			Identified:  false,
			ProductCode: "",
			ProductName: "",
			Confidence:  0.0,
			Reasoning:  "用户问题为空",
		}
	}

	n.LogInfo(fmt.Sprintf("正在识别产品: %s", userQuery))

	systemPrompt := prompts.SystemPromptProductIdentification
	userPrompt := fmt.Sprintf("用户问题: %s\n\n请识别产品并返回JSON格式。", userQuery)

	resp, err := n.LLMClient.Invoke(ctx, systemPrompt, userPrompt)
	if err != nil {
		n.LogError(fmt.Sprintf("产品识别失败: %v", err))
		return ProductIdentificationResult{
			Identified:  false,
			ProductCode: "",
			ProductName: "",
			Confidence:  0.0,
			Reasoning:  fmt.Sprintf("识别过程出错: %v", err),
		}
	}

	result := n.parseResponse(resp)
	n.LogInfo(fmt.Sprintf("产品识别结果: %s, 置信度: %.2f", result.ProductName, result.Confidence))
	return result
}

// parseResponse 解析LLM响应
func (n *ProductIdentificationNode) parseResponse(response string) ProductIdentificationResult {
	cleaned := strings.TrimSpace(response)
	
	// 移除代码块标记
	cleaned = strings.TrimPrefix(cleaned, "```json")
	cleaned = strings.TrimPrefix(cleaned, "```")
	cleaned = strings.TrimSuffix(cleaned, "```")
	cleaned = strings.TrimSpace(cleaned)

	var data map[string]any
	if err := json.Unmarshal([]byte(cleaned), &data); err != nil {
		n.LogError(fmt.Sprintf("响应解析失败: %v", err))
		return ProductIdentificationResult{
			Identified: false,
			Reasoning:  "响应解析失败",
		}
	}

	result := ProductIdentificationResult{
		Identified:    getBoolFromMap(data, "identified", false),
		ProductCode:   getStringFromMap(data, "product_code"),
		ProductName:   getStringFromMap(data, "product_name"),
		Confidence:    getFloatFromMap(data, "confidence", 0),
		Reasoning:    getStringFromMap(data, "reasoning"),
		Alternatives:  []map[string]any{},
	}

	if altList, ok := data["alternatives"].([]interface{}); ok {
		for _, alt := range altList {
			if altMap, ok := alt.(map[string]any); ok {
				result.Alternatives = append(result.Alternatives, altMap)
			}
		}
	}

	return result
}

// getBoolFromMap 安全获取bool值
func getBoolFromMap(m map[string]any, key string, defaultVal bool) bool {
	if val, ok := m[key].(bool); ok {
		return val
	}
	return defaultVal
}

// getStringFromMap 安全获取string值
func getStringFromMap(m map[string]any, key string) string {
	if val, ok := m[key].(string); ok {
		return val
	}
	return ""
}

// getFloatFromMap 安全获取float64值
func getFloatFromMap(m map[string]any, key string, defaultVal float64) float64 {
	if val, ok := m[key].(float64); ok {
		return val
	}
	if val, ok := m[key].(int); ok {
		return float64(val)
	}
	return defaultVal
}
