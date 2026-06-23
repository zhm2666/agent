package agent

import (
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"time"

	"github.com/deepsearch/deep-search-agent/internal/config"
	"github.com/deepsearch/deep-search-agent/internal/llm"
	"github.com/deepsearch/deep-search-agent/internal/nodes"
	"github.com/deepsearch/deep-search-agent/internal/search"
	"github.com/deepsearch/deep-search-agent/internal/state"
	"github.com/deepsearch/deep-search-agent/internal/utils"
)

type DeepSearchAgent struct {
	config            *config.Config
	llmClient         llm.BaseLLM
	firstSearchNode   *nodes.FirstSearchNode
	reflectionNode    *nodes.ReflectionNode
	firstSummaryNode  *nodes.FirstSummaryNode
	reflectionSummaryNode *nodes.ReflectionSummaryNode
	formattingNode    *nodes.ReportFormattingNode
	state             *state.State
}

func NewDeepSearchAgent(cfg *config.Config) (*DeepSearchAgent, error) {
	var apiKey string
	var modelName string
	
	switch cfg.DefaultLLMProvider {
	case "deepseek":
		apiKey = cfg.DeepSeekAPIKey
		modelName = cfg.DeepSeekModel
	case "openai":
		apiKey = cfg.OpenAIAPIKey
		modelName = cfg.OpenAIModel
	default:
		return nil, fmt.Errorf("unsupported LLM provider: %s", cfg.DefaultLLMProvider)
	}
	
	llmClient, err := llm.CreateLLM(cfg.DefaultLLMProvider, apiKey, modelName)
	if err != nil {
		return nil, fmt.Errorf("failed to create LLM client: %w", err)
	}
	
	if err := os.MkdirAll(cfg.OutputDir, 0755); err != nil {
		return nil, fmt.Errorf("failed to create output directory: %w", err)
	}
	
	agent := &DeepSearchAgent{
		config:            cfg,
		llmClient:         llmClient,
		firstSearchNode:   nodes.NewFirstSearchNode(llmClient),
		reflectionNode:    nodes.NewReflectionNode(llmClient),
		firstSummaryNode:  nodes.NewFirstSummaryNode(llmClient),
		reflectionSummaryNode: nodes.NewReflectionSummaryNode(llmClient),
		formattingNode:    nodes.NewReportFormattingNode(llmClient),
		state:             state.NewState(),
	}
	
	fmt.Printf("Deep Search Agent initialized\n")
	fmt.Printf("Using LLM: %s\n", cfg.GetLLMProvider())
	
	return agent, nil
}

func CreateAgent(cfg *config.Config) (*DeepSearchAgent, error) {
	return NewDeepSearchAgent(cfg)
}

func (a *DeepSearchAgent) Research(query string, saveReport bool) (string, error) {
	fmt.Printf("\n%s\n", strings.Repeat("=", 60))
	fmt.Printf("Starting deep research: %s\n", query)
	fmt.Printf("%s\n", strings.Repeat("=", 60))
	
	var err error
	
	a.state, err = a.generateReportStructure(query)
	if err != nil {
		return "", fmt.Errorf("failed to generate report structure: %w", err)
	}
	
	err = a.processParagraphs()
	if err != nil {
		return "", fmt.Errorf("failed to process paragraphs: %w", err)
	}
	
	finalReport, err := a.generateFinalReport()
	if err != nil {
		return "", fmt.Errorf("failed to generate final report: %w", err)
	}
	
	a.state.FinalReport = finalReport
	a.state.MarkCompleted()
	
	if saveReport {
		if err := a.saveReport(finalReport); err != nil {
			fmt.Printf("Warning: failed to save report: %v\n", err)
		}
	}
	
	fmt.Printf("\n%s\n", strings.Repeat("=", 60))
	fmt.Printf("Deep research completed!\n")
	fmt.Printf("%s\n", strings.Repeat("=", 60))
	
	return finalReport, nil
}

func (a *DeepSearchAgent) generateReportStructure(query string) (*state.State, error) {
	fmt.Printf("\n[Step 1] Generating report structure...\n")
	
	structureNode := nodes.NewReportStructureNode(a.llmClient, query)
	
	s := state.NewState()
	s.Query = query
	s.ReportTitle = fmt.Sprintf("关于'%s'的深度研究报告", query)
	
	structure, err := structureNode.Run()
	if err != nil {
		fmt.Printf("Warning: failed to generate structure with LLM, using default\n")
		defaultStructure := []map[string]string{
			{"title": "概述", "content": fmt.Sprintf("对'%s'的总体概述和背景介绍", query)},
			{"title": "详细分析", "content": fmt.Sprintf("深入分析'%s'的相关内容", query)},
		}
		structure = defaultStructure
	}
	
	for _, para := range structure {
		idx := s.AddParagraph(para["title"], para["content"])
		fmt.Printf("  %d. %s\n", idx+1, para["title"])
	}
	
	fmt.Printf("Report structure generated with %d paragraphs\n", len(structure))
	return s, nil
}

func (a *DeepSearchAgent) processParagraphs() error {
	total := len(a.state.Paragraphs)
	
	for i := 0; i < total; i++ {
		fmt.Printf("\n[Step 2.%d] Processing paragraph: %s\n", i+1, a.state.Paragraphs[i].Title)
		fmt.Printf("%s\n", strings.Repeat("-", 50))
		
		if err := a.initialSearchAndSummary(i); err != nil {
			fmt.Printf("Warning: failed initial search for paragraph %d: %v\n", i, err)
		}
		
		if err := a.reflectionLoop(i); err != nil {
			fmt.Printf("Warning: reflection loop failed for paragraph %d: %v\n", i, err)
		}
		
		a.state.Paragraphs[i].MarkResearchCompleted()
		
		progress := float64(i+1) / float64(total) * 100
		fmt.Printf("Paragraph completed (%.1f%%)\n", progress)
	}
	
	return nil
}

func (a *DeepSearchAgent) initialSearchAndSummary(paragraphIndex int) error {
	paragraph := &a.state.Paragraphs[paragraphIndex]
	
	fmt.Printf("  - Generating search query...\n")
	searchInput := map[string]interface{}{
		"title":   paragraph.Title,
		"content": paragraph.Content,
	}
	
	searchOutput, err := a.firstSearchNode.Run(searchInput)
	if err != nil {
		return fmt.Errorf("failed to generate search query: %w", err)
	}
	
	searchQuery := searchOutput["search_query"]
	reasoning := searchOutput["reasoning"]
	fmt.Printf("  - Search query: %s\n", searchQuery)
	fmt.Printf("  - Reasoning: %s\n", reasoning)
	
	fmt.Printf("  - Executing web search...\n")
	searchResults, err := search.Search(searchQuery, a.config.TavilyAPIKey, a.config.MaxSearchResults, a.config.SearchTimeout)
	if err != nil {
		fmt.Printf("  - Search failed: %v\n", err)
		searchResults = []map[string]interface{}{}
	}
	
	if len(searchResults) > 0 {
		fmt.Printf("  - Found %d search results\n", len(searchResults))
		for j, r := range searchResults {
			title := ""
			if t, ok := r["title"].(string); ok {
				title = t
			}
			if len(title) > 50 {
				title = title[:50] + "..."
			}
			fmt.Printf("    %d. %s...\n", j+1, title)
		}
	} else {
		fmt.Printf("  - No search results found\n")
	}
	
	paragraph.Research.AddSearch(searchQuery, searchResults)
	
	fmt.Printf("  - Generating initial summary...\n")
	formattedResults := utils.FormatSearchResultsForPrompt(searchResults, a.config.MaxContentLength)
	
	summaryInput := map[string]interface{}{
		"title":        paragraph.Title,
		"content":      paragraph.Content,
		"search_query": searchQuery,
		"search_results": formattedResults,
	}
	
	summary, err := a.firstSummaryNode.Run(summaryInput)
	if err != nil {
		paragraph.Research.LatestSummary = fmt.Sprintf("关于%s的初步研究内容。搜索查询: %s", paragraph.Title, searchQuery)
	} else {
		paragraph.Research.LatestSummary = summary
	}
	
	fmt.Printf("  - Initial summary completed\n")
	return nil
}

func (a *DeepSearchAgent) reflectionLoop(paragraphIndex int) error {
	paragraph := &a.state.Paragraphs[paragraphIndex]
	
	for i := 0; i < a.config.MaxReflections; i++ {
		fmt.Printf("  - Reflection %d/%d...\n", i+1, a.config.MaxReflections)
		
		reflectionInput := map[string]interface{}{
			"title":                   paragraph.Title,
			"content":                 paragraph.Content,
			"paragraph_latest_state":  paragraph.Research.LatestSummary,
		}
		
		reflectionOutput, err := a.reflectionNode.Run(reflectionInput)
		if err != nil {
			fmt.Printf("    Warning: failed to generate reflection query: %v\n", err)
			continue
		}
		
		searchQuery := reflectionOutput["search_query"]
		reasoning := reflectionOutput["reasoning"]
		fmt.Printf("    Reflection query: %s\n", searchQuery)
		fmt.Printf("    Reflection reasoning: %s\n", reasoning)
		
		fmt.Printf("    Executing reflection search...\n")
		searchResults, err := search.Search(searchQuery, a.config.TavilyAPIKey, a.config.MaxSearchResults, a.config.SearchTimeout)
		if err != nil {
			fmt.Printf("    Warning: reflection search failed: %v\n", err)
			searchResults = []map[string]interface{}{}
		}
		
		if len(searchResults) > 0 {
			fmt.Printf("    Found %d reflection search results\n", len(searchResults))
		}
		
		paragraph.Research.AddSearch(searchQuery, searchResults)
		
		formattedResults := utils.FormatSearchResultsForPrompt(searchResults, a.config.MaxContentLength)
		
		reflectionSummaryInput := map[string]interface{}{
			"title":                   paragraph.Title,
			"content":                 paragraph.Content,
			"search_query":            searchQuery,
			"search_results":          formattedResults,
			"paragraph_latest_state":  paragraph.Research.LatestSummary,
		}
		
		summary, err := a.reflectionSummaryNode.Run(reflectionSummaryInput)
		if err != nil {
			fmt.Printf("    Warning: failed to generate reflection summary: %v\n", err)
		} else {
			paragraph.Research.LatestSummary = summary
		}
		
		fmt.Printf("    Reflection %d completed\n", i+1)
	}
	
	return nil
}

func (a *DeepSearchAgent) generateFinalReport() (string, error) {
	fmt.Printf("\n[Step 3] Generating final report...\n")
	
	reportData := make([]map[string]interface{}, 0, len(a.state.Paragraphs))
	for _, para := range a.state.Paragraphs {
		reportData = append(reportData, map[string]interface{}{
			"title":                    para.Title,
			"paragraph_latest_state":   para.Research.LatestSummary,
		})
	}
	
	finalReport, err := a.formattingNode.Run(reportData)
	if err != nil {
		fmt.Printf("Warning: LLM formatting failed, using manual method: %v\n", err)
		finalReport = a.formattingNode.FormatReportManually(reportData, a.state.ReportTitle)
	}
	
	fmt.Printf("Final report generated\n")
	return finalReport, nil
}

func (a *DeepSearchAgent) saveReport(report string) error {
	timestamp := time.Now().Format("20060102_150405")
	
	querySafe := a.state.Query
	for _, r := range []string{"/", "\\", ":", "*", "?", "\"", "<", ">", "|"} {
		querySafe = strings.ReplaceAll(querySafe, r, "")
	}
	querySafe = strings.ReplaceAll(querySafe, " ", "_")
	if len(querySafe) > 30 {
		querySafe = querySafe[:30]
	}
	
	filename := fmt.Sprintf("deep_search_report_%s_%s.md", querySafe, timestamp)
	filePath := filepath.Join(a.config.OutputDir, filename)
	
	if err := os.WriteFile(filePath, []byte(report), 0644); err != nil {
		return fmt.Errorf("failed to write report: %w", err)
	}
	
	fmt.Printf("Report saved to: %s\n", filePath)
	
	if a.config.SaveIntermediateState {
		stateFilename := fmt.Sprintf("state_%s_%s.json", querySafe, timestamp)
		stateFilepath := filepath.Join(a.config.OutputDir, stateFilename)
		
		if err := a.state.SaveToFile(stateFilepath); err != nil {
			fmt.Printf("Warning: failed to save state: %v\n", err)
		} else {
			fmt.Printf("State saved to: %s\n", stateFilepath)
		}
	}
	
	return nil
}

func (a *DeepSearchAgent) GetProgressSummary() map[string]interface{} {
	return a.state.GetProgressSummary()
}

func (a *DeepSearchAgent) LoadState(filepath string) error {
	loadedState, err := state.LoadFromFile(filepath)
	if err != nil {
		return fmt.Errorf("failed to load state: %w", err)
	}
	a.state = loadedState
	fmt.Printf("State loaded from %s\n", filepath)
	return nil
}

func (a *DeepSearchAgent) SaveState(filepath string) error {
	if err := a.state.SaveToFile(filepath); err != nil {
		return fmt.Errorf("failed to save state: %w", err)
	}
	fmt.Printf("State saved to %s\n", filepath)
	return nil
}

func (a *DeepSearchAgent) GetState() *state.State {
	return a.state
}
