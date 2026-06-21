package mcp

import (
	"prediction-agent/logging"
	"time"

	"go.uber.org/zap"
)

// MCPChartResult MCP图表结果
type MCPChartResult struct {
	Success     bool   `json:"success"`
	FilePath    string `json:"filepath"`
	URL         string `json:"url"`
	ChartID     string `json:"chart_id"`
	ChartType   string `json:"chart_type"`
	Error       string `json:"error"`
}

// MCPChartClient MCP图表客户端
type MCPChartClient struct {
	Mode      string `json:"mode"`
	ServerURL string `json:"server_url"`
	logger    *zap.Logger
}

// NewMCPChartClient 创建MCP客户端
func NewMCPChartClient(mode, serverURL string) *MCPChartClient {
	return &MCPChartClient{
		Mode:      mode,
		ServerURL: serverURL,
		logger:    logging.GetLogger("mcp.client"),
	}
}

// PlotSalesForecast 绘制销量预测图表
func (c *MCPChartClient) PlotSalesForecast(
	productName string,
	dates []string,
	actualValues []float64,
	predictedValues []float64,
	futureDates []string,
	futurePredictions []float64,
	chartType string,
) MCPChartResult {
	c.logger.Info("MCP chart request",
		zap.String("product_name", productName),
		zap.String("chart_type", chartType),
	)

	// 模拟MCP调用（实际项目中应该调用HTTP API或子进程）
	// 这里返回模拟结果，实际使用时需要连接到Python MCP服务器
	time.Sleep(100 * time.Millisecond)

	// 生成图表ID
	chartID := generateChartID()

	return MCPChartResult{
		Success:   true,
		FilePath:  "output/charts/" + chartID + ".png",
		URL:       "/charts/" + chartID + ".png",
		ChartID:   chartID,
		ChartType: chartType,
	}
}

// generateChartID 生成图表ID
func generateChartID() string {
	return time.Now().Format("20060102150405")
}
