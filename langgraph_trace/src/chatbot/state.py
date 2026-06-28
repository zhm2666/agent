from typing import List, Dict, Any, Optional
from typing_extensions import TypedDict
from langgraph.graph import MessagesState


class ChatbotState(MessagesState):
    user_id: Optional[str]
    session_id: Optional[str]
    metadata: Dict[str, Any]
    tool_results: List[Dict[str, Any]]
    reasoning_steps: List[str]
    final_response: Optional[str]