"""统一的错误处理和重试机制"""
import time
import functools
import logging
from typing import Callable, TypeVar, Union, List, Type, Optional, Any, Dict
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
    after_log
)

logger = logging.getLogger(__name__)

T = TypeVar('T')


class ChatbotError(Exception):
    """聊天机器人基础异常"""
    def __init__(self, message: str, code: str = "UNKNOWN"):
        self.message = message
        self.code = code
        super().__init__(message)


class LLMError(ChatbotError):
    """LLM 调用错误"""
    def __init__(self, message: str):
        super().__init__(message, code="LLM_ERROR")


class ToolExecutionError(ChatbotError):
    """工具执行错误"""
    def __init__(self, tool_name: str, message: str):
        self.tool_name = tool_name
        super().__init__(f"[{tool_name}] {message}", code="TOOL_ERROR")


class SessionError(ChatbotError):
    """会话管理错误"""
    def __init__(self, message: str):
        super().__init__(message, code="SESSION_ERROR")


class RateLimitError(ChatbotError):
    """速率限制错误"""
    def __init__(self, message: str = "请求过于频繁"):
        super().__init__(message, code="RATE_LIMIT")


# 预定义的重试策略
RETRY_STRATEGIES = {
    # 快速重试：网络瞬时波动
    "fast": {
        "stop": stop_after_attempt(3),
        "wait": wait_exponential(multiplier=0.5, min=0.1, max=2),
    },
    # 标准重试：一般 API 调用
    "standard": {
        "stop": stop_after_attempt(5),
        "wait": wait_exponential(multiplier=1, min=1, max=10),
    },
    # 慢速重试：外部依赖（数据库、外部 API）
    "slow": {
        "stop": stop_after_attempt(3),
        "wait": wait_exponential(multiplier=5, min=5, max=30),
    },
}


def retry_on_llm_error(
    strategy: str = "standard",
    log_attempts: bool = True
) -> Callable:
    """
    LLM 调用重试装饰器

    Args:
        strategy: 重试策略 ("fast", "standard", "slow")
        log_attempts: 是否记录重试日志
    """
    config = RETRY_STRATEGIES.get(strategy, RETRY_STRATEGIES["standard"])

    return retry(
        stop=config["stop"],
        wait=config["wait"],
        retry=retry_if_exception_type((LLMError, RateLimitError, ConnectionError)),
        before_sleep=before_sleep_log(logger, logging.WARNING) if log_attempts else None,
        after=after_log(logger, logging.INFO) if log_attempts else None,
        reraise=True,
    )


def retry_on_tool_error(
    strategy: str = "fast",
    log_attempts: bool = True,
    max_attempts: Optional[int] = None
) -> Callable:
    """
    工具执行重试装饰器

    Args:
        strategy: 重试策略
        log_attempts: 是否记录重试日志
        max_attempts: 最大重试次数（覆盖策略）
    """
    config = RETRY_STRATEGIES.get(strategy, RETRY_STRATEGIES["fast"])

    stop = config["stop"]
    if max_attempts:
        stop = stop_after_attempt(max_attempts)

    return retry(
        stop=stop,
        wait=config["wait"],
        retry=retry_if_exception_type((ToolExecutionError, ConnectionError)),
        before_sleep=before_sleep_log(logger, logging.WARNING) if log_attempts else None,
        after=after_log(logger, logging.INFO) if log_attempts else None,
        reraise=True,
    )


def circuit_breaker(
    failure_threshold: int = 5,
    recovery_timeout: float = 60.0,
    expected_exception: Type[Exception] = Exception
):
    """
    熔断器装饰器

    Args:
        failure_threshold: 连续失败次数阈值
        recovery_timeout: 恢复时间（秒）
        expected_exception: 期望捕获的异常类型
    """
    def decorator(func: Callable) -> Callable:
        failure_count = 0
        last_failure_time: Optional[float] = None
        is_open = False

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            nonlocal failure_count, last_failure_time, is_open

            # 检查是否应该尝试恢复
            if is_open:
                if time.time() - last_failure_time >= recovery_timeout:
                    logger.info(f"Circuit breaker: 尝试恢复 {func.__name__}")
                    is_open = False
                    failure_count = 0
                else:
                    raise ChatbotError(
                        f"Circuit breaker opened for {func.__name__}",
                        code="CIRCUIT_BREAKER"
                    )

            try:
                result = func(*args, **kwargs)
                # 成功后重置计数器
                if failure_count > 0:
                    logger.info(f"Circuit breaker: {func.__name__} 恢复成功")
                failure_count = 0
                return result

            except expected_exception as e:
                failure_count += 1
                last_failure_time = time.time()

                if failure_count >= failure_threshold:
                    is_open = True
                    logger.warning(
                        f"Circuit breaker: 触发熔断 {func.__name__}, "
                        f"失败次数: {failure_count}"
                    )
                raise

        wrapper._circuit_breaker_info = {
            "failure_threshold": failure_threshold,
            "recovery_timeout": recovery_timeout
        }
        return wrapper

    return decorator


def with_error_context(context: str, reraise: bool = True) -> Callable:
    """
    添加错误上下文的装饰器

    Args:
        context: 错误上下文描述
        reraise: 是否重新抛出异常
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except ChatbotError:
                raise  # 已经带有上下文，直接抛出
            except Exception as e:
                logger.error(f"{context}: {e}")
                if reraise:
                    raise ChatbotError(
                        f"{context}: {str(e)}",
                        code="INTERNAL_ERROR"
                    ) from e

        return wrapper
    return decorator


def safe_execute(
    default: Any = None,
    log_errors: bool = True,
    error_handler: Optional[Callable[[Exception], Any]] = None
) -> Callable:
    """
    安全执行装饰器，返回默认值而不是抛出异常

    Args:
        default: 默认返回值
        log_errors: 是否记录错误
        error_handler: 自定义错误处理器
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if log_errors:
                    logger.error(f"{func.__name__} 执行失败: {e}")
                if error_handler:
                    return error_handler(e)
                return default

        return wrapper
    return decorator


class ErrorRecoveryManager:
    """错误恢复管理器"""

    def __init__(self):
        self._recovery_handlers: Dict[str, Callable] = {}
        self._error_counts: Dict[str, int] = {}

    def register_handler(self, error_code: str, handler: Callable[[Exception], Any]):
        """注册错误处理器"""
        self._recovery_handlers[error_code] = handler

    def handle_error(self, error: Exception, context: str = "default") -> Any:
        """处理错误并尝试恢复"""
        error_code = getattr(error, "code", "UNKNOWN")

        # 记录错误计数
        self._error_counts[error_code] = self._error_counts.get(error_code, 0) + 1

        # 查找并调用处理器
        handler = self._recovery_handlers.get(error_code)
        if handler:
            logger.info(f"执行错误恢复处理器: {error_code}")
            return handler(error)

        # 返回降级响应
        return {
            "status": "error",
            "error_code": error_code,
            "message": str(error),
            "recovered": False
        }

    def get_error_stats(self) -> Dict[str, int]:
        """获取错误统计"""
        return self._error_counts.copy()

    def reset_stats(self):
        """重置统计"""
        self._error_counts.clear()


# 全局实例
_error_recovery_manager: Optional[ErrorRecoveryManager] = None


def get_error_recovery_manager() -> ErrorRecoveryManager:
    global _error_recovery_manager
    if _error_recovery_manager is None:
        _error_recovery_manager = ErrorRecoveryManager()
    return _error_recovery_manager


from typing import Dict
