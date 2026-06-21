"""
日志工厂模块 - 提供统一的日志配置
所有模块使用此模块获取logger，日志统一保存到项目logs目录
"""

import os
import logging
from logging.handlers import RotatingFileHandler
from typing import Optional


# 日志根目录
_LOG_ROOT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")

# 全局日志配置标志
_log_initialized = False


def _ensure_log_dir():
    """确保日志目录存在"""
    os.makedirs(_LOG_ROOT_DIR, exist_ok=True)


def setup_logging(
    log_level: int = logging.DEBUG,
    console_level: int = logging.INFO,
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5
) -> logging.Logger:
    """
    初始化日志配置（全局只调用一次）

    Args:
        log_level: 文件日志级别
        console_level: 控制台日志级别
        max_bytes: 单个日志文件最大大小
        backup_count: 保留的备份文件数量

    Returns:
        根日志记录器
    """
    global _log_initialized

    if _log_initialized:
        return logging.getLogger("PredictionAgent")

    _ensure_log_dir()

    # 日志格式
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"

    # 创建格式化器
    formatter = logging.Formatter(log_format, date_format)

    # 文件日志处理器（带轮转）
    file_handler = RotatingFileHandler(
        os.path.join(_LOG_ROOT_DIR, "app.log"),
        encoding="utf-8",
        maxBytes=max_bytes,
        backupCount=backup_count
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)

    # 错误日志单独文件
    error_handler = RotatingFileHandler(
        os.path.join(_LOG_ROOT_DIR, "error.log"),
        encoding="utf-8",
        maxBytes=max_bytes,
        backupCount=backup_count
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)

    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(console_level)
    console_handler.setFormatter(formatter)

    # 配置根日志记录器
    root_logger = logging.getLogger("PredictionAgent")
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(error_handler)
    root_logger.addHandler(console_handler)

    _log_initialized = True

    # 记录启动日志
    root_logger.info("=" * 50)
    root_logger.info("日志系统初始化完成")
    root_logger.info(f"日志目录: {_LOG_ROOT_DIR}")
    root_logger.info("=" * 50)

    return root_logger


def get_logger(name: str) -> logging.Logger:
    """
    获取指定名称的日志记录器

    Args:
        name: 模块名称，通常使用 __name__

    Returns:
        日志记录器实例
    """
    if not _log_initialized:
        setup_logging()

    # 返回子logger，保持命名空间层级
    return logging.getLogger(f"PredictionAgent.{name}")


def get_module_logger(module_name: str, module_file: Optional[str] = None) -> logging.Logger:
    """
    获取模块级日志记录器（自动从文件路径推断名称）

    Args:
        module_name: 模块名称
        module_file: 模块文件路径，传入 __file__

    Returns:
        日志记录器实例
    """
    if module_file:
        # 从文件路径提取模块名
        rel_path = os.path.relpath(module_file, os.path.dirname(os.path.dirname(__file__)))
        rel_path = rel_path.replace(os.sep, ".").replace("/", ".").replace("\\", ".")
        if rel_path.endswith(".py"):
            rel_path = rel_path[:-3]
        return get_logger(rel_path)

    return get_logger(module_name)


# 便捷函数
def debug(message: str, *args, **kwargs):
    """快捷方法：记录DEBUG级别日志"""
    logging.getLogger("PredictionAgent").debug(message, *args, **kwargs)


def info(message: str, *args, **kwargs):
    """快捷方法：记录INFO级别日志"""
    logging.getLogger("PredictionAgent").info(message, *args, **kwargs)


def warning(message: str, *args, **kwargs):
    """快捷方法：记录WARNING级别日志"""
    logging.getLogger("PredictionAgent").warning(message, *args, **kwargs)


def error(message: str, *args, **kwargs):
    """快捷方法：记录ERROR级别日志"""
    logging.getLogger("PredictionAgent").error(message, *args, **kwargs)


def critical(message: str, *args, **kwargs):
    """快捷方法：记录CRITICAL级别日志"""
    logging.getLogger("PredictionAgent").critical(message, *args, **kwargs)
