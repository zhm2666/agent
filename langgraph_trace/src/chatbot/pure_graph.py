"""纯业务图，节点函数使用 @trace_node 装饰器"""
from typing import Literal, Iterator, AsyncIterator, Union, Dict, Any
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage, AIMessage
from langgraph.prebuilt import create_react_agent
from langgraph_trace.src.chatbot.state import ChatbotState
from langgraph_trace.src.chatbot.pure_tools import PureTools
from langgraph_trace.src.chatbot.session_manager import get_session_manager
from langgraph_trace.src.chatbot.error_handling import (
    retry_on_llm_error,
    circuit_breaker,
    LLMError,
    ToolExecutionError,
    get_error_recovery_manager
)
from langgraph_trace.src.tracing.decorators import trace_node, trace_graph


class PureChatbotGraph:
    def __init__(self, system_prompt: str = "你是一个智能助手，请准确、专业地回答用户问题。"):
        self.system_prompt = system_prompt
        self.llm = ChatOpenAI(
            model="deepseek-v4-flash",
            api_key="sk",
            base_url="https://api.deepseek.com",
        )
        self.session_manager = get_session_manager()

        self.tools = [
            PureTools.search_knowledge_base,
            PureTools.get_current_time,
            PureTools.calculate,
            PureTools.get_weather
        ]
        self.tool_executor = create_react_agent(self.llm, self.tools)
        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        workflow = StateGraph(ChatbotState)
        workflow.add_node("process_input", self.process_input)
        workflow.add_node("reasoning", self.reasoning)
        workflow.add_node("tool_execution", self.execute_tools)
        workflow.add_node("generate_response", self.generate_response)
        workflow.set_entry_point("process_input")
        workflow.add_edge("process_input", "reasoning")
        workflow.add_conditional_edges(
            "reasoning",
            self.should_use_tools,
            {"tools": "tool_execution", "respond": "generate_response"}
        )
        workflow.add_edge("tool_execution", "reasoning")
        workflow.add_edge("generate_response", END)
        return workflow.compile()

    @trace_node("process_input")
    def process_input(self, state: ChatbotState) -> ChatbotState:
        session_id = state.get("session_id", "default")
        user_id = state.get("user_id", "anonymous")

        # 从会话历史加载消息
        history = self.session_manager.get_messages(session_id)

        # 如果历史为空，添加系统消息
        if not history:
            history.insert(0, SystemMessage(content=self.system_prompt))

        # 添加当前用户消息
        current_msg = state["messages"][-1] if state["messages"] else None
        if current_msg and isinstance(current_msg, HumanMessage):
            self.session_manager.add_message(session_id, current_msg)
            history.append(current_msg)

        state["messages"] = history
        return state

    @trace_node("reasoning")
    @retry_on_llm_error(strategy="standard")
    def reasoning(self, state: ChatbotState) -> ChatbotState:
        try:
            response = self.llm.invoke(state["messages"])
            state["messages"].append(response)
            return state
        except Exception as e:
            raise LLMError(f"LLM 调用失败: {str(e)}") from e

    @trace_node("tool_execution")
    @circuit_breaker(failure_threshold=3, recovery_timeout=30)
    def execute_tools(self, state: ChatbotState) -> ChatbotState:
        last_msg = state["messages"][-1]
        if hasattr(last_msg, 'tool_calls') and last_msg.tool_calls:
            for tc in last_msg.tool_calls:
                tool_name = tc.get("name", "unknown")
                tool_args = tc.get("args", {})

                # 查找并调用工具
                tool_func = next(
                    (t for t in self.tools if t.name == tool_name),
                    None
                )
                if tool_func:
                    try:
                        result = tool_func.invoke(tool_args)
                    except Exception as e:
                        result = f"工具执行错误: {str(e)}"
                        get_error_recovery_manager().handle_error(e, context=tool_name)
                else:
                    result = f"未找到工具: {tool_name}"

                state["messages"].append(
                    ToolMessage(content=str(result), tool_call_id=tc["id"])
                )
                # 存储工具结果
                state["tool_results"].append({
                    "tool_name": tool_name,
                    "arguments": {k: v for k, v in tool_args.items()},
                    "result": str(result)[:500]
                })

                # 更新会话历史
                session_id = state.get("session_id", "default")
                self.session_manager.add_message(
                    session_id,
                    ToolMessage(content=str(result), tool_call_id=tc["id"])
                )

        return state

    @trace_node("generate_response")
    @retry_on_llm_error(strategy="standard")
    def generate_response(self, state: ChatbotState) -> ChatbotState:
        try:
            final = self.llm.invoke(state["messages"])
            state["final_response"] = final.content
            state["messages"].append(final)

            # 更新会话历史
            session_id = state.get("session_id", "default")
            self.session_manager.add_message(session_id, final)

            return state
        except Exception as e:
            raise LLMError(f"生成回复失败: {str(e)}") from e

    def should_use_tools(self, state: ChatbotState) -> Literal["tools", "respond"]:
        last = state["messages"][-1]
        if hasattr(last, 'tool_calls') and last.tool_calls:
            return "tools"
        return "respond"

    @trace_graph(name="graph.invoke")
    def invoke(self, user_message: str, user_id: str = "anonymous",
               session_id: str = "default") -> Dict[str, Any]:
        """同步调用，返回完整响应"""
        self.session_manager.get_or_create_session(session_id, user_id)

        initial = ChatbotState(
            messages=[HumanMessage(content=user_message)],
            user_id=user_id,
            session_id=session_id,
            metadata={},
            tool_results=[],
            reasoning_steps=[],
            final_response=None
        )

        try:
            result = self.graph.invoke(initial)
            return {
                "response": result.get("final_response", ""),
                "tool_results": result.get("tool_results", []),
                "reasoning_steps": result.get("reasoning_steps", []),
                "session_id": session_id,
                "status": "success"
            }
        except Exception as e:
            return {
                "response": f"处理错误: {str(e)}",
                "tool_results": [],
                "reasoning_steps": [],
                "session_id": session_id,
                "status": "error",
                "error": str(e)
            }

    @trace_graph(name="graph.stream")
    def stream(self, user_message: str, user_id: str = "anonymous",
               session_id: str = "default") -> Iterator[Dict[str, Any]]:
        """流式调用，返回生成器"""
        from langchain_core.outputs import ChatGenerationChunk
        from langchain_core.messages import AIMessageChunk

        self.session_manager.get_or_create_session(session_id, user_id)

        initial = ChatbotState(
            messages=[HumanMessage(content=user_message)],
            user_id=user_id,
            session_id=session_id,
            metadata={},
            tool_results=[],
            reasoning_steps=[],
            final_response=None
        )

        try:
            for event in self.graph.stream(initial):
                for node_name, node_state in event.items():
                    if node_name == "reasoning":
                        messages = node_state.get("messages", [])
                        if messages:
                            last_msg = messages[-1]
                            if hasattr(last_msg, 'content'):
                                yield {
                                    "type": "reasoning",
                                    "content": last_msg.content[-100:] if len(last_msg.content) > 100 else last_msg.content,
                                    "full_content": last_msg.content
                                }

                    elif node_name == "tool_execution":
                        tool_results = node_state.get("tool_results", [])
                        if tool_results:
                            yield {
                                "type": "tool",
                                "tool_name": tool_results[-1].get("tool_name"),
                                "result": tool_results[-1].get("result", "")[:200]
                            }

                    elif node_name == "generate_response":
                        final_response = node_state.get("final_response", "")
                        yield {
                            "type": "response",
                            "content": final_response
                        }

        except Exception as e:
            yield {
                "type": "error",
                "content": str(e)
            }
