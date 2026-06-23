package nodes

import "fmt"

// BaseNode 节点基类
type BaseNode struct {
	LLMClient any
	NodeName  string
}

// NewBaseNode 创建节点
func NewBaseNode(llmClient any, nodeName string) *BaseNode {
	if nodeName == "" {
		nodeName = "BaseNode"
	}
	return &BaseNode{
		LLMClient: llmClient,
		NodeName:  nodeName,
	}
}

// LogInfo 记录信息日志
func (n *BaseNode) LogInfo(message string) {
	fmt.Printf("[%s] %s\n", n.NodeName, message)
}

// LogError 记录错误日志
func (n *BaseNode) LogError(message string) {
	fmt.Printf("[%s] Error: %s\n", n.NodeName, message)
}
