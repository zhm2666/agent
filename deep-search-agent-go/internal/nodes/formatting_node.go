package nodes

import (
	"encoding/json"
	"fmt"

	"github.com/deepsearch/deep-search-agent/internal/llm"
	"github.com/deepsearch/deep-search-agent/internal/prompts"
	"github.com/deepsearch/deep-search-agent/internal/utils"
)

type ReportFormattingNode struct {
	*BaseNode
}

func NewReportFormattingNode(llmClient llm.BaseLLM) *ReportFormattingNode {
	return &ReportFormattingNode{
		BaseNode: NewBaseNode(llmClient, "ReportFormattingNode"),
	}
}

func (n *ReportFormattingNode) Run(inputData []map[string]interface{}) (string, error) {
	n.LogInfo("Formatting final report")
	
	jsonData, err := json.Marshal(inputData)
	if err != nil {
		return "", fmt.Errorf("failed to marshal input data: %w", err)
	}
	
	response, err := n.llmClient.Invoke(prompts.SystemPromptReportFormatting, string(jsonData))
	if err != nil {
		return "", fmt.Errorf("failed to invoke LLM: %w", err)
	}
	
	result, err := n.processOutput(response)
	if err != nil {
		return "", err
	}
	
	n.LogInfo("Successfully formatted final report")
	return result, nil
}

func (n *ReportFormattingNode) processOutput(output string) (string, error) {
	cleaned := utils.RemoveReasoningFromOutput(output)
	cleaned = utils.CleanMarkdownTags(cleaned)
	
	if cleaned == "" {
		return "# 报告生成失败\n\n无法生成有效的报告内容。", nil
	}
	
	return cleaned, nil
}

func (n *ReportFormattingNode) FormatReportManually(inputData []map[string]interface{}, reportTitle string) string {
	n.LogInfo("Using manual formatting method")
	
	report := fmt.Sprintf("# %s\n\n---\n\n", reportTitle)
	
	for i, para := range inputData {
		title := getStringFromMap(para, "title")
		content := getStringFromMap(para, "paragraph_latest_state")
		
		if title == "" {
			title = fmt.Sprintf("段落 %d", i+1)
		}
		
		if content != "" {
			report += fmt.Sprintf("## %s\n\n%s\n\n---\n\n", title, content)
		}
	}
	
	if len(inputData) > 1 {
		report += "## 结论\n\n本报告通过深度搜索和研究，对相关主题进行了全面分析。\n"
		report += "以上各个方面的内容为理解该主题提供了重要参考。\n\n"
	}
	
	return report
}
