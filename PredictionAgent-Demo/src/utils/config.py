"""
配置管理模块
"""

import os
from typing import Optional
from dataclasses import dataclass


@dataclass
class Config:
    """配置类"""
    # LLM配置
    default_llm_provider: str = "deepseek"
    deepseek_api_key: Optional[str] = None
    deepseek_model: str = "deepseek-chat"
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4o-mini"

    # 数据库配置
    mysql_host: str = "localhost"
    mysql_port: int = 3306
    mysql_user: str = "root"
    mysql_password: str = ""
    mysql_database: str = "prediction_db"

    # 图表配置
    chart_output_dir: str = "output/charts"
    chart_base_url: str = "/charts"

    # 预测配置
    prediction_days: int = 30  # 未来预测天数

    # 输出配置
    output_dir: str = "output"


def load_config(config_file: Optional[str] = None) -> Config:
    """加载配置"""
    config = Config()

    # 从环境变量覆盖配置
    config.deepseek_api_key = os.getenv("DEEPSEEK_API_KEY") or config.deepseek_api_key
    config.openai_api_key = os.getenv("OPENAI_API_KEY") or config.openai_api_key

    config.mysql_host = os.getenv("MYSQL_HOST", config.mysql_host)
    config.mysql_port = int(os.getenv("MYSQL_PORT", str(config.mysql_port)))
    config.mysql_user = os.getenv("MYSQL_USER", config.mysql_user)
    config.mysql_password = os.getenv("MYSQL_PASSWORD", config.mysql_password)
    config.mysql_database = os.getenv("MYSQL_DATABASE", config.mysql_database)

    config.chart_output_dir = os.getenv("CHART_OUTPUT_DIR", config.chart_output_dir)
    config.chart_base_url = os.getenv("CHART_BASE_URL", config.chart_base_url)

    return config
