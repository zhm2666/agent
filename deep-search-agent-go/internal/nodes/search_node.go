package nodes

import (
	"encoding/json"
	"fmt"

	"github.com/deepsearch/deep-search-agent/internal/llm"
	"github.com/deepsearch/deep-search-agent/internal/prompts"
	"github.com/deepsearch/deep-search-agent/internal/utils"
)

type FirstSearchNode struct {
	*BaseNode
}

func NewFirstSearchNode(llmClient llm.BaseLLM) *FirstSearchNode {
	return &FirstSearchNode{
		BaseNode: NewBaseNode(llmClient, "FirstSearchNode"),
	}
}

func (n *FirstSearchNode) Run(inputData map[string]interface{}) (map[string]string, error) {
	title, _ := inputData["title"].(string)
	content, _ := inputData["content"].(string)
	
	n.LogInfo("Generating first search query")
	
	message := fmt.Sprintf(`{"title": "%s", "content": "%s"}`, title, content)
	
	response, err := n.llmClient.Invoke(prompts.SystemPromptFirstSearch, message)
	if err != nil {
		return nil, fmt.Errorf("failed to invoke LLM: %w", err)
	}
	
	result, err := n.processOutput(response)
	if err != nil {
		return nil, err
	}
	
	n.LogInfo(fmt.Sprintf("Generated search query: %s", result["search_query"]))
	return result, nil
}

func (n *FirstSearchNode) processOutput(output string) (map[string]string, error) {
	cleaned := utils.RemoveReasoningFromOutput(output)
	cleaned = utils.CleanJSONTags(cleaned)
	
	data, err := utils.ExtractCleanResponse(cleaned)
	if err != nil {
		n.LogError(fmt.Sprintf("Failed to parse response: %v", err))
		return map[string]string{
			"search_query": "相关主题研究",
			"reasoning":    "由于解析失败，使用默认搜索查询",
		}, nil
	}
	
	searchQuery := getStringFromMap(data, "search_query")
	reasoning := getStringFromMap(data, "reasoning")
	
	if searchQuery == "" {
		searchQuery = "相关主题研究"
		reasoning = "由于解析失败，使用默认搜索查询"
	}
	
	return map[string]string{
		"search_query": searchQuery,
		"reasoning":    reasoning,
	}, nil
}

type ReflectionNode struct {
	*BaseNode
}

func NewReflectionNode(llmClient llm.BaseLLM) *ReflectionNode {
	return &ReflectionNode{
		BaseNode: NewBaseNode(llmClient, "ReflectionNode"),
	}
}

func (n *ReflectionNode) Run(inputData map[string]interface{}) (map[string]string, error) {
	title, _ := inputData["title"].(string)
	content, _ := inputData["content"].(string)
	latestState, _ := inputData["paragraph_latest_state"].(string)
	
	n.LogInfo("Generating reflection search query")
	
	message := fmt.Sprintf(`{"title": "%s", "content": "%s", "paragraph_latest_state": "%s"}`, 
		title, content, latestState)
	
	response, err := n.llmClient.Invoke(prompts.SystemPromptReflection, message)
	if err != nil {
		return nil, fmt.Errorf("failed to invoke LLM: %w", err)
	}
	
	result, err := n.processOutput(response)
	if err != nil {
		return nil, err
	}
	
	n.LogInfo(fmt.Sprintf("Generated reflection query: %s", result["search_query"]))
	return result, nil
}

func (n *ReflectionNode) processOutput(output string) (map[string]string, error) {
	cleaned := utils.RemoveReasoningFromOutput(output)
	cleaned = utils.CleanJSONTags(cleaned)
	
	data, err := utils.ExtractCleanResponse(cleaned)
	if err != nil {
		n.LogError(fmt.Sprintf("Failed to parse response: %v", err))
		return map[string]string{
			"search_query": "深度研究补充信息",
			"reasoning":    "由于解析失败，使用默认反思搜索查询",
		}, nil
	}
	
	searchQuery := getStringFromMap(data, "search_query")
	reasoning := getStringFromMap(data, "reasoning")
	
	if searchQuery == "" {
		searchQuery = "深度研究补充信息"
		reasoning = "由于解析失败，使用默认反思搜索查询"
	}
	
	return map[string]string{
		"search_query": searchQuery,
		"reasoning":    reasoning,
	}, nil
}

func getStringFromMap(m map[string]interface{}, key string) string {
	if v, ok := m[key].(string); ok {
		return v
	}
	if v, ok := m[key].(float64); ok {
		return fmt.Sprintf("%v", v)
	}
	if v, ok := m[key].(bool); ok {
		return fmt.Sprintf("%v", v)
	}
	if v, ok := m[key].(map[string]interface{}); ok {
		data, _ := json.Marshal(v)
		return string(data)
	}
	return ""
}
