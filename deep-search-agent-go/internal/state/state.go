package state

import (
	"encoding/json"
	"fmt"
	"os"
	"time"
)

type Search struct {
	Query     string   `json:"query"`
	URL       string   `json:"url"`
	Title     string   `json:"title"`
	Content   string   `json:"content"`
	Score     *float64 `json:"score,omitempty"`
	Timestamp string   `json:"timestamp"`
}

type Research struct {
	SearchHistory      []Search `json:"search_history"`
	LatestSummary      string   `json:"latest_summary"`
	ReflectionIter     int      `json:"reflection_iteration"`
	IsCompleted        bool     `json:"is_completed"`
}

type Paragraph struct {
	Title   string   `json:"title"`
	Content string   `json:"content"`
	Research Research `json:"research"`
	Order   int      `json:"order"`
}

type State struct {
	Query        string       `json:"query"`
	ReportTitle  string       `json:"report_title"`
	Paragraphs   []Paragraph  `json:"paragraphs"`
	FinalReport  string       `json:"final_report"`
	IsCompleted  bool         `json:"is_completed"`
	CreatedAt    string       `json:"created_at"`
	UpdatedAt    string       `json:"updated_at"`
}

func NewState() *State {
	now := time.Now().Format(time.RFC3339)
	return &State{
		Paragraphs: make([]Paragraph, 0),
		CreatedAt:  now,
		UpdatedAt:  now,
	}
}

func (s *State) AddParagraph(title, content string) int {
	order := len(s.Paragraphs)
	paragraph := Paragraph{
		Title:   title,
		Content: content,
		Research: Research{
			SearchHistory: make([]Search, 0),
		},
		Order: order,
	}
	s.Paragraphs = append(s.Paragraphs, paragraph)
	s.UpdateTimestamp()
	return order
}

func (s *State) GetParagraph(index int) *Paragraph {
	if index >= 0 && index < len(s.Paragraphs) {
		return &s.Paragraphs[index]
	}
	return nil
}

func (s *Paragraph) IsCompleted() bool {
	return s.Research.IsCompleted && s.Research.LatestSummary != ""
}

func (s *State) GetCompletedCount() int {
	count := 0
	for _, p := range s.Paragraphs {
		if p.IsCompleted() {
			count++
		}
	}
	return count
}

func (s *State) GetTotalCount() int {
	return len(s.Paragraphs)
}

func (s *State) IsAllCompleted() bool {
	if len(s.Paragraphs) == 0 {
		return false
	}
	for _, p := range s.Paragraphs {
		if !p.IsCompleted() {
			return false
		}
	}
	return true
}

func (s *State) MarkCompleted() {
	s.IsCompleted = true
	s.UpdateTimestamp()
}

func (s *State) UpdateTimestamp() {
	s.UpdatedAt = time.Now().Format(time.RFC3339)
}

func (s *State) GetProgressSummary() map[string]interface{} {
	completed := s.GetCompletedCount()
	total := s.GetTotalCount()
	
	percentage := 0.0
	if total > 0 {
		percentage = float64(completed) / float64(total) * 100
	}
	
	return map[string]interface{}{
		"total_paragraphs":      total,
		"completed_paragraphs": completed,
		"progress_percentage":  percentage,
		"is_completed":          s.IsCompleted,
		"created_at":            s.CreatedAt,
		"updated_at":            s.UpdatedAt,
	}
}

func (s *State) ToJSON() (string, error) {
	data, err := json.MarshalIndent(s, "", "  ")
	if err != nil {
		return "", fmt.Errorf("failed to marshal state: %w", err)
	}
	return string(data), nil
}

func (s *State) SaveToFile(filepath string) error {
	data, err := json.MarshalIndent(s, "", "  ")
	if err != nil {
		return fmt.Errorf("failed to marshal state: %w", err)
	}
	
	if err := os.MkdirAll(filepath[:len(filepath)-len("/state.json")], 0755); err != nil {
		dir := filepath[:len(filepath)-len("/state.json")]
		if err := os.MkdirAll(dir, 0755); err != nil {
			return fmt.Errorf("failed to create directory: %w", err)
		}
	}
	
	if err := os.WriteFile(filepath, data, 0644); err != nil {
		return fmt.Errorf("failed to write state file: %w", err)
	}
	
	return nil
}

func LoadFromFile(filepath string) (*State, error) {
	data, err := os.ReadFile(filepath)
	if err != nil {
		return nil, fmt.Errorf("failed to read state file: %w", err)
	}
	
	var state State
	if err := json.Unmarshal(data, &state); err != nil {
		return nil, fmt.Errorf("failed to unmarshal state: %w", err)
	}
	
	return &state, nil
}

func LoadFromJSON(jsonStr string) (*State, error) {
	var state State
	if err := json.Unmarshal([]byte(jsonStr), &state); err != nil {
		return nil, fmt.Errorf("failed to unmarshal state: %w", err)
	}
	return &state, nil
}

func (r *Research) AddSearch(query string, results []map[string]interface{}) {
	for _, result := range results {
		search := Search{
			Query:     query,
			URL:       getStringValue(result, "url"),
			Title:     getStringValue(result, "title"),
			Content:   getStringValue(result, "content"),
			Timestamp: time.Now().Format(time.RFC3339),
		}
		if score, ok := result["score"].(float64); ok {
			search.Score = &score
		}
		r.SearchHistory = append(r.SearchHistory, search)
	}
}

func (r *Research) IncrementReflection() {
	r.ReflectionIter++
}

func (r *Research) MarkCompleted() {
	r.IsCompleted = true
}

func (s *Paragraph) MarkResearchCompleted() {
	s.Research.IsCompleted = true
}

func getStringValue(m map[string]interface{}, key string) string {
	if v, ok := m[key].(string); ok {
		return v
	}
	return ""
}
