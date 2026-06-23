package nodes

import (
	"fmt"

	"github.com/deepsearch/deep-search-agent/internal/llm"
	"github.com/deepsearch/deep-search-agent/internal/prompts"
	"github.com/deepsearch/deep-search-agent/internal/state"
	"github.com/deepsearch/deep-search-agent/internal/utils"
)

type FirstSummaryNode struct {
	*BaseNode
}

func NewFirstSummaryNode(llmClient llm.BaseLLM) *FirstSummaryNode {
	return &FirstSummaryNode{
		BaseNode: NewBaseNode(llmClient, "FirstSummaryNode"),
	}
}

func (n *FirstSummaryNode) Run(inputData map[string]interface{}) (string, error) {
	n.LogInfo("Generating first paragraph summary")
	
	searchResults := inputData["search_results"]
	resultsStr := ""
	
	if results, ok := searchResults.([]string); ok {
		for i, r := range results {
			resultsStr += fmt.Sprintf("[%d] %s\n\n", i+1, r)
		}
	}
	
	message := fmt.Sprintf(`{
		"title": "%s",
		"content": "%s",
		"search_query": "%s",
		"search_results": [%s]
	}`,
		inputData["title"],
		inputData["content"],
		inputData["search_query"],
		formatSearchResultsString(resultsStr))
	
	response, err := n.llmClient.Invoke(prompts.SystemPromptFirstSummary, message)
	if err != nil {
		return "", fmt.Errorf("failed to invoke LLM: %w", err)
	}
	
	result, err := n.processOutput(response)
	if err != nil {
		return "", err
	}
	
	n.LogInfo("Successfully generated first paragraph summary")
	return result, nil
}

func (n *FirstSummaryNode) processOutput(output string) (string, error) {
	cleaned := utils.RemoveReasoningFromOutput(output)
	cleaned = utils.CleanJSONTags(cleaned)
	
	data, err := utils.ExtractCleanResponse(cleaned)
	if err != nil {
		return cleaned, nil
	}
	
	if content := getStringFromMap(data, "paragraph_latest_state"); content != "" {
		return content, nil
	}
	
	return cleaned, nil
}

func (n *FirstSummaryNode) MutateState(inputData map[string]interface{}, s *state.State, paragraphIndex int) (*state.State, error) {
	summary, err := n.Run(inputData)
	if err != nil {
		return nil, err
	}
	
	if paragraphIndex >= 0 && paragraphIndex < len(s.Paragraphs) {
		s.Paragraphs[paragraphIndex].Research.LatestSummary = summary
		n.LogInfo(fmt.Sprintf("Updated paragraph %d with first summary", paragraphIndex))
	} else {
		return nil, fmt.Errorf("paragraph index %d out of range", paragraphIndex)
	}
	
	s.UpdateTimestamp()
	return s, nil
}

type ReflectionSummaryNode struct {
	*BaseNode
}

func NewReflectionSummaryNode(llmClient llm.BaseLLM) *ReflectionSummaryNode {
	return &ReflectionSummaryNode{
		BaseNode: NewBaseNode(llmClient, "ReflectionSummaryNode"),
	}
}

func (n *ReflectionSummaryNode) Run(inputData map[string]interface{}) (string, error) {
	n.LogInfo("Generating reflection summary")
	
	searchResults := inputData["search_results"]
	resultsStr := ""
	
	if results, ok := searchResults.([]string); ok {
		for i, r := range results {
			resultsStr += fmt.Sprintf("[%d] %s\n\n", i+1, r)
		}
	}
	
	message := fmt.Sprintf(`{
		"title": "%s",
		"content": "%s",
		"search_query": "%s",
		"search_results": [%s],
		"paragraph_latest_state": "%s"
	}`,
		inputData["title"],
		inputData["content"],
		inputData["search_query"],
		formatSearchResultsString(resultsStr),
		inputData["paragraph_latest_state"])
	
	response, err := n.llmClient.Invoke(prompts.SystemPromptReflectionSummary, message)
	if err != nil {
		return "", fmt.Errorf("failed to invoke LLM: %w", err)
	}
	
	result, err := n.processOutput(response)
	if err != nil {
		return "", err
	}
	
	n.LogInfo("Successfully generated reflection summary")
	return result, nil
}

func (n *ReflectionSummaryNode) processOutput(output string) (string, error) {
	cleaned := utils.RemoveReasoningFromOutput(output)
	cleaned = utils.CleanJSONTags(cleaned)
	
	data, err := utils.ExtractCleanResponse(cleaned)
	if err != nil {
		return cleaned, nil
	}
	
	if content := getStringFromMap(data, "updated_paragraph_latest_state"); content != "" {
		return content, nil
	}
	
	return cleaned, nil
}

func (n *ReflectionSummaryNode) MutateState(inputData map[string]interface{}, s *state.State, paragraphIndex int) (*state.State, error) {
	summary, err := n.Run(inputData)
	if err != nil {
		return nil, err
	}
	
	if paragraphIndex >= 0 && paragraphIndex < len(s.Paragraphs) {
		s.Paragraphs[paragraphIndex].Research.LatestSummary = summary
		s.Paragraphs[paragraphIndex].Research.IncrementReflection()
		n.LogInfo(fmt.Sprintf("Updated paragraph %d with reflection summary", paragraphIndex))
	} else {
		return nil, fmt.Errorf("paragraph index %d out of range", paragraphIndex)
	}
	
	s.UpdateTimestamp()
	return s, nil
}

func formatSearchResultsString(results string) string {
	results = fmt.Sprintf(`"%s"`, results)
	return results
}
