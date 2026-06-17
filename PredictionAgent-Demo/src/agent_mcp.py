"""
预测分析Agent主类 - MCP版本
集成MCP客户端调用绘图服务
"""

import os
from typing import Optional, Dict, Any

from .llms import DeepSeekLLM, OpenAILLM, BaseLLM
from .nodes import (
    ProductIdentificationNode,
    DataFetchNode,
    ChartNode,
    AnalysisNode
)
from .database import DatabaseConnection, SalesRepository
from .state import State
from .utils import Config, load_config
from .mcp import MCPChartClient


class PredictionAgent:
    """预测分析Agent主类 - MCP集成版"""

    def __init__(self, config: Optional[Config] = None):
        """初始化Prediction Agent"""
        self.config = config or load_config()

        # 初始化LLM客户端
        self.llm_client = self._initialize_llm()

        # 初始化数据库
        self._initialize_database()

        # 初始化MCP客户端（用于调用绘图服务）
        self._initialize_mcp_client()

        # 初始化节点
        self._initialize_nodes()

        # 状态
        self.state = State()

        # 确保输出目录存在
        os.makedirs(self.config.output_dir, exist_ok=True)
        os.makedirs(self.config.chart_output_dir, exist_ok=True)

        print(f"Prediction Agent (MCP版) 已初始化")
        print(f"使用LLM: {self.llm_client.get_model_info()}")
        print(f"图表服务模式: MCP ({self.mcp_mode})")

    def _initialize_llm(self) -> BaseLLM:
        """初始化LLM客户端"""
        if self.config.default_llm_provider == "deepseek":
            return DeepSeekLLM(
                api_key=self.config.deepseek_api_key,
                model_name=self.config.deepseek_model
            )
        elif self.config.default_llm_provider == "openai":
            return OpenAILLM(
                api_key=self.config.openai_api_key,
                model_name=self.config.openai_model
            )
        else:
            raise ValueError(f"不支持的LLM提供商: {self.config.default_llm_provider}")

    def _initialize_database(self):
        """初始化数据库连接"""
        db_config = {
            "host": self.config.mysql_host,
            "port": self.config.mysql_port,
            "user": self.config.mysql_user,
            "password": self.config.mysql_password,
            "database": self.config.mysql_database
        }

        self.db_connection = DatabaseConnection(**db_config)

        if self.db_connection.connect():
            self.repository = SalesRepository(self.db_connection)
            print(f"已连接到数据库: {self.config.mysql_database}")
        else:
            print("警告: 数据库连接失败，将使用模拟数据")
            self.repository = None

    def _initialize_mcp_client(self):
        """初始化MCP客户端"""
        self.mcp_mode = "local"  # local 或 remote

        self.mcp_chart_client = MCPChartClient(
            mode=self.mcp_mode,
            server_url="http://localhost:8000"  # 远程MCP服务器地址
        )

        print(f"MCP图表客户端已初始化 (模式: {self.mcp_mode})")

    def _initialize_nodes(self):
        """初始化处理节点"""
        self.product_identification_node = ProductIdentificationNode(
            self.llm_client,
            self.repository if self.repository else self._create_mock_repository()
        )
        self.data_fetch_node = DataFetchNode(self.llm_client, self.repository)
        # 传入MCP客户端
        self.chart_node = ChartNode(self.llm_client, self.mcp_chart_client)
        self.analysis_node = AnalysisNode(self.llm_client)

    def _create_mock_repository(self):
        """创建模拟仓库"""
        class MockRepository:
            def get_all_products(self):
                return []
            def get_product_by_code(self, code):
                return None
            def search_products(self, keyword):
                return []
            def get_product_analysis_data(self, product_code, history_days=90, future_days=30):
                return None
        return MockRepository()

    def analyze(
        self,
        query: str,
        chart_type: str = "combined",
        use_mock_data: bool = False,
        product_code: Optional[str] = None
    ) -> Dict[str, Any]:
        """执行预测分析"""
        print(f"\n{'='*60}")
        print(f"开始预测分析 (MCP版): {query}")
        print(f"{'='*60}")

        self.state = State()
        self.state.user_query = query
        self.state.chart_type = chart_type

        try:
            # Step 1: 产品识别
            self._step_product_identification(query, product_code)

            if not self.state.prediction_state.product_identification.identified:
                raise ValueError("无法识别产品，请提供更具体的产品信息")

            # Step 2: 数据获取
            self._step_data_fetch(use_mock_data)

            # Step 3: 图表生成 (通过MCP调用)
            self._step_chart_generation()

            # Step 4: 分析
            self._step_analysis()

            self.state.mark_completed()

            print(f"\n{'='*60}")
            print("预测分析完成！")
            print(f"{'='*60}")

            return self._build_response()

        except Exception as e:
            self.state.mark_error(str(e))
            print(f"分析过程中发生错误: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "state": self.state.to_dict()
            }

    def _step_product_identification(self, query: str, product_code: Optional[str] = None):
        """步骤1: 产品识别"""
        print(f"\n[步骤 1] 产品识别...")

        self.state.set_step("product_identification")

        if product_code:
            product = self.repository.get_product_by_code(product_code) if self.repository else None
            if product:
                self.state.prediction_state.product_identification.identified = True
                self.state.prediction_state.product_identification.product_code = product.product_code
                self.state.prediction_state.product_identification.product_name = product.product_name
                self.state.prediction_state.product_identification.confidence = 1.0
                print(f"已识别产品: {product.product_name} ({product.product_code})")
                return

        result = self.product_identification_node.run({"user_query": query})

        id_state = self.state.prediction_state.product_identification
        id_state.identified = result.get("identified", False)
        id_state.product_code = result.get("product_code", "")
        id_state.product_name = result.get("product_name", "")
        id_state.confidence = result.get("confidence", 0.0)
        id_state.reasoning = result.get("reasoning", "")
        id_state.alternatives = result.get("alternatives", [])

        if id_state.identified:
            print(f"已识别产品: {id_state.product_name} ({id_state.product_code})")
        else:
            print("未能识别产品")

    def _step_data_fetch(self, use_mock_data: bool = False):
        """步骤2: 数据获取"""
        print(f"\n[步骤 2] 数据获取...")

        self.state.set_step("data_fetch")

        product_code = self.state.prediction_state.product_identification.product_code
        product_name = self.state.prediction_state.product_identification.product_name

        if use_mock_data or not self.repository:
            print("使用模拟数据...")
            result = self.data_fetch_node.fetch_mock_data(product_code, product_name)
        else:
            result = self.data_fetch_node.run({
                "product_code": product_code,
                "product_name": product_name
            })

        fetch_state = self.state.prediction_state.data_fetch
        fetch_state.fetched = result.get("fetched", False)
        fetch_state.historical_data = result.get("historical_data", [])
        fetch_state.model_predictions = result.get("model_predictions", [])
        fetch_state.future_predictions = result.get("future_predictions", [])
        fetch_state.statistics = result.get("statistics", {})
        fetch_state.error_message = result.get("error_message", "")

        if fetch_state.fetched:
            print(f"数据获取成功: 历史{len(fetch_state.historical_data)}条, 预测{len(fetch_state.future_predictions)}条")

    def _step_chart_generation(self):
        """步骤3: 图表生成 (MCP调用)"""
        print(f"\n[步骤 3] 图表生成 (通过MCP调用)...")

        self.state.set_step("chart_generation")

        fetch_state = self.state.prediction_state.data_fetch

        # 通过MCP客户端调用绘图服务
        chart_result = self.chart_node.run({
            "product_name": self.state.prediction_state.product_identification.product_name,
            "chart_type": self.state.chart_type,
            "historical_data": fetch_state.historical_data,
            "future_predictions": fetch_state.future_predictions,
            "model_predictions": fetch_state.model_predictions
        })

        chart_state = self.state.prediction_state.chart_generation
        chart_state.generated = chart_result.get("generated", False)
        chart_state.chart_type = chart_result.get("chart_type", "")
        chart_state.chart_url = chart_result.get("chart_url", "")
        chart_state.chart_filepath = chart_result.get("chart_filepath", "")
        chart_state.chart_id = chart_result.get("chart_id", "")

        if chart_state.generated:
            print(f"MCP图表生成成功: {chart_state.chart_url}")
        else:
            print(f"图表生成失败: {chart_result.get('error', '未知错误')}")

    def _step_analysis(self):
        """步骤4: 分析"""
        print(f"\n[步骤 4] 预测分析...")

        self.state.set_step("analysis")

        id_state = self.state.prediction_state.product_identification
        fetch_state = self.state.prediction_state.data_fetch
        chart_state = self.state.prediction_state.chart_generation

        analysis_result = self.analysis_node.run({
            "product_name": id_state.product_name,
            "product_code": id_state.product_code,
            "user_query": self.state.user_query,
            "historical_data": fetch_state.historical_data,
            "future_predictions": fetch_state.future_predictions,
            "statistics": fetch_state.statistics,
            "chart_url": chart_state.chart_url
        })

        analysis_state = self.state.prediction_state.analysis
        analysis_state.analyzed = analysis_result.get("analyzed", False)
        analysis_state.analysis_result = analysis_result.get("analysis_result", "")
        analysis_state.key_insights = analysis_result.get("key_insights", [])
        analysis_state.recommendations = analysis_result.get("recommendations", [])

        print("分析完成")

    def _build_response(self) -> Dict[str, Any]:
        """构建响应"""
        id_state = self.state.prediction_state.product_identification
        fetch_state = self.state.prediction_state.data_fetch
        chart_state = self.state.prediction_state.chart_generation
        analysis_state = self.state.prediction_state.analysis

        return {
            "success": True,
            "product": {
                "code": id_state.product_code,
                "name": id_state.product_name,
                "confidence": id_state.confidence
            },
            "data": {
                "historical_data": fetch_state.historical_data,
                "future_predictions": fetch_state.future_predictions,
                "statistics": fetch_state.statistics
            },
            "chart": {
                "url": chart_state.chart_url,
                "type": chart_state.chart_type,
                "filepath": chart_state.chart_filepath,
                "chart_id": chart_state.chart_id,
                "via_mcp": True  # 标记通过MCP生成
            },
            "analysis": {
                "result": analysis_state.analysis_result,
                "key_insights": analysis_state.key_insights,
                "recommendations": analysis_state.recommendations
            },
            "state": self.state.to_dict()
        }

    def get_progress(self) -> Dict[str, Any]:
        """获取进度"""
        return {
            "step": self.state.prediction_state.step,
            "progress": self.state.get_progress(),
            "is_completed": self.state.is_completed
        }

    def save_state(self, filepath: str):
        """保存状态"""
        self.state.save_to_file(filepath)

    def load_state(self, filepath: str):
        """加载状态"""
        self.state = State.load_from_file(filepath)


def create_agent(config_file: Optional[str] = None) -> PredictionAgent:
    """创建Agent实例"""
    config = load_config(config_file)
    return PredictionAgent(config)
