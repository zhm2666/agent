package search

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"time"
)

type SearchResult struct {
	Title   string   `json:"title"`
	URL     string   `json:"url"`
	Content string   `json:"content"`
	Score   *float64 `json:"score,omitempty"`
}

type TavilySearch struct {
	apiKey string
	client *http.Client
}

func NewTavilySearch(apiKey string) *TavilySearch {
	if apiKey == "" {
		apiKey = "your-tavily-api-key"
	}
	
	return &TavilySearch{
		apiKey: apiKey,
		client: &http.Client{
			Timeout: 120 * time.Second,
		},
	}
}

type tavilyRequest struct {
	Query               string `json:"query"`
	MaxResults          int    `json:"max_results"`
	IncludeRawContent   bool   `json:"include_raw_content"`
	SearchDepth         string `json:"search_depth"`
}

type tavilyResponse struct {
	Results []tavilyResult `json:"results"`
}

type tavilyResult struct {
	Title         string   `json:"title"`
	URL           string   `json:"url"`
	Content       string   `json:"content"`
	Score         float64  `json:"score"`
}

func (t *TavilySearch) Search(query string, maxResults int, timeout int) ([]SearchResult, error) {
	if maxResults <= 0 {
		maxResults = 5
	}
	
	requestBody := tavilyRequest{
		Query:               query,
		MaxResults:          maxResults,
		IncludeRawContent:   true,
		SearchDepth:         "advanced",
	}
	
	jsonData, err := json.Marshal(requestBody)
	if err != nil {
		return nil, fmt.Errorf("failed to marshal request: %w", err)
	}
	
	url := "https://api.tavily.com/search"
	req, err := http.NewRequest("POST", url, bytes.NewBuffer(jsonData))
	if err != nil {
		return nil, fmt.Errorf("failed to create request: %w", err)
	}
	
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("X-API-KEY", t.apiKey)
	
	resp, err := t.client.Do(req)
	if err != nil {
		return nil, fmt.Errorf("failed to send request: %w", err)
	}
	defer resp.Body.Close()
	
	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("failed to read response: %w", err)
	}
	
	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("Tavily API request failed with status %d: %s", resp.StatusCode, string(body))
	}
	
	var result tavilyResponse
	if err := json.Unmarshal(body, &result); err != nil {
		return nil, fmt.Errorf("failed to parse response: %w", err)
	}
	
	results := make([]SearchResult, 0, len(result.Results))
	for _, r := range result.Results {
		score := r.Score
		results = append(results, SearchResult{
			Title:   r.Title,
			URL:     r.URL,
			Content: r.Content,
			Score:   &score,
		})
	}
	
	return results, nil
}

func (s *SearchResult) ToMap() map[string]interface{} {
	m := map[string]interface{}{
		"title":   s.Title,
		"url":     s.URL,
		"content": s.Content,
	}
	if s.Score != nil {
		m["score"] = *s.Score
	}
	return m
}

func Search(query string, apiKey string, maxResults int, timeout int) ([]map[string]interface{}, error) {
	client := NewTavilySearch(apiKey)
	results, err := client.Search(query, maxResults, timeout)
	if err != nil {
		return nil, err
	}
	
	maps := make([]map[string]interface{}, 0, len(results))
	for _, r := range results {
		maps = append(maps, r.ToMap())
	}
	
	return maps, nil
}

func TestSearch(query, apiKey string, maxResults int) {
	fmt.Printf("\n=== Testing Tavily Search ===\n")
	fmt.Printf("Query: %s\n", query)
	fmt.Printf("Max Results: %d\n", maxResults)
	
	results, err := Search(query, apiKey, maxResults, 240)
	if err != nil {
		fmt.Printf("Search error: %v\n", err)
		return
	}
	
	if len(results) == 0 {
		fmt.Println("No results found")
		return
	}
	
	fmt.Printf("\nFound %d results:\n", len(results))
	for i, r := range results {
		fmt.Printf("\nResult %d:\n", i+1)
		fmt.Printf("Title: %s\n", r["title"])
		fmt.Printf("URL: %s\n", r["url"])
		content := r["content"].(string)
		if len(content) > 200 {
			content = content[:200] + "..."
		}
		fmt.Printf("Content: %s\n", content)
		if score, ok := r["score"].(float64); ok {
			fmt.Printf("Score: %.4f\n", score)
		}
	}
}
