package state

import (
	"encoding/json"
	"os"
	"time"
)

// ProductIdentificationState 产品识别状态
type ProductIdentificationState struct {
	Identified   bool              `json:"identified"`
	ProductCode  string            `json:"product_code"`
	ProductName  string            `json:"product_name"`
	Confidence   float64           `json:"confidence"`
	Reasoning    string            `json:"reasoning"`
	Alternatives []map[string]any  `json:"alternatives"`
}

// DataFetchState 数据获取状态
type DataFetchState struct {
	Fetched            bool           `json:"fetched"`
	HistoricalData     []map[string]any `json:"historical_data"`
	ModelPredictions   []map[string]any `json:"model_predictions"`
	FuturePredictions  []map[string]any `json:"future_predictions"`
	Statistics         map[string]any  `json:"statistics"`
	ErrorMessage       string          `json:"error_message"`
}

// ChartState 图表生成状态
type ChartState struct {
	Generated    bool   `json:"generated"`
	ChartType   string `json:"chart_type"`
	ChartURL    string `json:"chart_url"`
	ChartFilePath string `json:"chart_filepath"`
	ChartID     string `json:"chart_id"`
}

// AnalysisState 分析状态
type AnalysisState struct {
	Analyzed       bool     `json:"analyzed"`
	AnalysisResult string   `json:"analysis_result"`
	KeyInsights   []string `json:"key_insights"`
	Recommendations []string `json:"recommendations"`
}

// PredictionState 单个预测分析的状态
type PredictionState struct {
	Step                    string                      `json:"step"`
	ProductIdentification   ProductIdentificationState `json:"product_identification"`
	DataFetch               DataFetchState              `json:"data_fetch"`
	ChartGeneration         ChartState                  `json:"chart_generation"`
	Analysis                AnalysisState               `json:"analysis"`
}

// State Agent状态
type State struct {
	UserQuery       string          `json:"user_query"`
	ChartType       string          `json:"chart_type"`
	PredictionState PredictionState `json:"prediction_state"`
	IsCompleted    bool            `json:"is_completed"`
	ErrorMessage   string          `json:"error_message"`
	CreatedAt       string          `json:"created_at"`
	UpdatedAt       string          `json:"updated_at"`
}

// NewState 创建新状态
func NewState() *State {
	now := time.Now().Format(time.RFC3339)
	return &State{
		ChartType: "combined",
		PredictionState: PredictionState{
			Step: "initial",
		},
		CreatedAt: now,
		UpdatedAt: now,
	}
}

// UpdateTimestamp 更新时间戳
func (s *State) UpdateTimestamp() {
	s.UpdatedAt = time.Now().Format(time.RFC3339)
}

// SetStep 设置当前步骤
func (s *State) SetStep(step string) {
	s.PredictionState.Step = step
	s.UpdateTimestamp()
}

// MarkCompleted 标记为完成
func (s *State) MarkCompleted() {
	s.IsCompleted = true
	s.PredictionState.Step = "completed"
	s.UpdateTimestamp()
}

// MarkError 标记错误
func (s *State) MarkError(errMsg string) {
	s.ErrorMessage = errMsg
	s.PredictionState.Step = "error"
	s.UpdateTimestamp()
}

// GetProgress 获取进度
func (s *State) GetProgress() float64 {
	stepWeights := map[string]float64{
		"initial":                0,
		"product_identification":  20,
		"data_fetch":             40,
		"chart_generation":       60,
		"analysis":               80,
		"completed":              100,
		"error":                  0,
	}
	if weight, ok := stepWeights[s.PredictionState.Step]; ok {
		return weight
	}
	return 0
}

// ToMap 转换为map
func (s *State) ToMap() map[string]any {
	data, _ := json.Marshal(s)
	var result map[string]any
	json.Unmarshal(data, &result)
	return result
}

// ToJSON 转换为JSON
func (s *State) ToJSON() string {
	data, _ := json.MarshalIndent(s, "", "  ")
	return string(data)
}

// FromMap 从map创建
func FromMap(data map[string]any) *State {
	jsonData, _ := json.Marshal(data)
	var state State
	json.Unmarshal(jsonData, &state)
	return &state
}

// FromJSON 从JSON创建
func FromJSON(jsonStr string) (*State, error) {
	var state State
	if err := json.Unmarshal([]byte(jsonStr), &state); err != nil {
		return nil, err
	}
	return &state, nil
}

// SaveToFile 保存到文件
func (s *State) SaveToFile(filepath string) error {
	return os.WriteFile(filepath, []byte(s.ToJSON()), 0644)
}

// LoadFromFile 从文件加载
func LoadFromFile(filepath string) (*State, error) {
	data, err := os.ReadFile(filepath)
	if err != nil {
		return nil, err
	}
	return FromJSON(string(data))
}
