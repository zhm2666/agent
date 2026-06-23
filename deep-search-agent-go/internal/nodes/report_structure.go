package nodes

import (
	"fmt"

	"github.com/deepsearch/deep-search-agent/internal/llm"
	"github.com/deepsearch/deep-search-agent/internal/prompts"
	"github.com/deepsearch/deep-search-agent/internal/state"
	"github.com/deepsearch/deep-search-agent/internal/utils"
)

type BaseNode struct {
	llmClient llm.BaseLLM
	nodeName  string
}

func NewBaseNode(llmClient llm.BaseLLM, nodeName string) *BaseNode {
	return &BaseNode{
		llmClient: llmClient,
		nodeName:  nodeName,
	}
}

func (n *BaseNode) LogInfo(message string) {
	fmt.Printf("[%s] %s\n", n.nodeName, message)
}

func (n *BaseNode) LogError(message string) {
	fmt.Printf("[%s] Error: %s\n", n.nodeName, message)
}

type ReportStructureNode struct {
	*BaseNode
	query string
}

func NewReportStructureNode(llmClient llm.BaseLLM, query string) *ReportStructureNode {
	return &ReportStructureNode{
		BaseNode: NewBaseNode(llmClient, "ReportStructureNode"),
		query:    query,
	}
}

func (n *ReportStructureNode) Run() ([]map[string]string, error) {
	n.LogInfo(fmt.Sprintf("Generating report structure for query: %s", n.query))
	
	response, err := n.llmClient.Invoke(prompts.SystemPromptReportStructure, n.query)
	if err != nil {
		return nil, fmt.Errorf("failed to invoke LLM: %w", err)
	}
	
	result, err := n.processOutput(response)
	if err != nil {
		return nil, err
	}
	
	n.LogInfo(fmt.Sprintf("Successfully generated %d paragraph structures", len(result)))
	return result, nil
}

func (n *ReportStructureNode) processOutput(output string) ([]map[string]string, error) {
	cleaned := utils.RemoveReasoningFromOutput(output)
	cleaned = utils.CleanJSONTags(cleaned)
	
	data, err := utils.ExtractCleanResponse(cleaned)
	if err != nil {
		n.LogError(fmt.Sprintf("Failed to parse response: %v", err))
		return nil, err
	}
	
	if _, ok := data["array"]; ok {
		if arr, ok := data["array"].([]interface{}); ok {
			var reportStructure []map[string]string
			for i, item := range arr {
				if m, ok := item.(map[string]interface{}); ok {
					title := getStringFromMap(m, "title")
					if title == "" {
						title = fmt.Sprintf("段落 %d", i+1)
					}
					reportStructure = append(reportStructure, map[string]string{
						"title":   title,
						"content": getStringFromMap(m, "content"),
					})
				}
			}
			return reportStructure, nil
		}
	}
	
	return nil, fmt.Errorf("invalid response format")
}

func (n *ReportStructureNode) MutateState(s *state.State) (*state.State, error) {
	structure, err := n.Run()
	if err != nil {
		return nil, err
	}
	
	s.Query = n.query
	if s.ReportTitle == "" {
		s.ReportTitle = fmt.Sprintf("关于'%s'的深度研究报告", n.query)
	}
	
	for _, para := range structure {
		s.AddParagraph(para["title"], para["content"])
	}
	
	n.LogInfo(fmt.Sprintf("Added %d paragraphs to state", len(structure)))
	return s, nil
}
