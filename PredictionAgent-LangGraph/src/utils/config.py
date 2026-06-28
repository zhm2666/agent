"""
配置模块

复用 PredictionAgent-Demo 的配置加载逻辑，保持行为一致。
"""

import os
from dataclasses import dataclass
from typing import Optional


API_KEY = os.environ.get("OPENAI_API_KEY", "sk-hww5ISsBbQ8Q8HyraLFwM5D30tzMEmEAAT1e3qsoR4rhDvE9")
BASE_URL = os.environ.get("OPENAI_BASE_URL", "https://api.moonshot.cn/v1")
MODEL = os.environ.get("OPENAI_MODEL", "kimi-k2.6")

@dataclass
class Config:
    default_llm_provider: str = "deepseek"
    deepseek_api_key: Optional[str] = "sk-0291"
    deepseek_model: str = "deepseek-v4-flash"
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4o-mini"

    mysql_host: str = "localhost"
    mysql_port: int = 3306
    mysql_user: str = "root"
    mysql_password: str = ""
    mysql_database: str = "prediction_db"

    chart_output_dir: str = "output/charts"
    chart_base_url: str = "/charts"

    prediction_days: int = 30
    output_dir: str = "output"


def load_config(config_file: Optional[str] = None) -> Config:
    config = Config()
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
