"""会话管理器 - 管理多会话消息历史"""
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
import threading


class SessionManager:
    """线程安全的会话管理器"""

    def __init__(self, max_history: int = 50, ttl_minutes: int = 60):
        self.max_history = max_history  # 每个会话最大消息数
        self.ttl_minutes = ttl_minutes   # 会话过期时间(分钟)
        self._sessions: Dict[str, Dict] = {}  # {session_id: {messages, last_access}}
        self._lock = threading.RLock()

    def get_or_create_session(self, session_id: str, user_id: str = "anonymous") -> Dict:
        """获取或创建会话"""
        with self._lock:
            now = datetime.now()
            if session_id in self._sessions:
                self._sessions[session_id]["last_access"] = now
                return self._sessions[session_id]

            # 创建新会话
            self._sessions[session_id] = {
                "messages": [],
                "user_id": user_id,
                "created_at": now,
                "last_access": now
            }
            self._cleanup_expired()
            return self._sessions[session_id]

    def add_message(self, session_id: str, message: BaseMessage) -> None:
        """添加消息到会话"""
        with self._lock:
            if session_id not in self._sessions:
                self.get_or_create_session(session_id)

            session = self._sessions[session_id]
            session["messages"].append(message)
            session["last_access"] = datetime.now()

            # 限制消息数量
            if len(session["messages"]) > self.max_history:
                # 保留系统消息，只裁剪对话
                system_msgs = [m for m in session["messages"] if isinstance(m, SystemMessage)]
                history = [m for m in session["messages"] if not isinstance(m, SystemMessage)]
                # 保留最近的消息
                session["messages"] = system_msgs + history[-self.max_history + len(system_msgs):]

    def get_messages(self, session_id: str) -> List[BaseMessage]:
        """获取会话消息"""
        with self._lock:
            if session_id in self._sessions:
                self._sessions[session_id]["last_access"] = datetime.now()
                return self._sessions[session_id]["messages"]
            return []

    def clear_session(self, session_id: str) -> bool:
        """清除会话"""
        with self._lock:
            if session_id in self._sessions:
                del self._sessions[session_id]
                return True
            return False

    def _cleanup_expired(self) -> None:
        """清理过期会话"""
        now = datetime.now()
        expired = [
            sid for sid, data in self._sessions.items()
            if now - data["last_access"] > timedelta(minutes=self.ttl_minutes)
        ]
        for sid in expired:
            del self._sessions[sid]

    def get_session_info(self, session_id: str) -> Optional[Dict]:
        """获取会话信息"""
        with self._lock:
            if session_id in self._sessions:
                data = self._sessions[session_id]
                return {
                    "session_id": session_id,
                    "user_id": data["user_id"],
                    "message_count": len(data["messages"]),
                    "created_at": data["created_at"].isoformat(),
                    "last_access": data["last_access"].isoformat()
                }
            return None

    @property
    def active_sessions(self) -> int:
        """活跃会话数"""
        with self._lock:
            self._cleanup_expired()
            return len(self._sessions)


# 全局单例
_session_manager: Optional[SessionManager] = None


def get_session_manager() -> SessionManager:
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager


def reset_session_manager() -> None:
    """重置会话管理器（用于测试）"""
    global _session_manager
    _session_manager = None
