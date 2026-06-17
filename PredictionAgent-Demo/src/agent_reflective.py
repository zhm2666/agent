"""
预测分析Agent主类 - 反思版
集成反思机制，支持结果验证和自动重试
"""

import os
from typing import Optional, Dict, Any, Callable

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
from .reflection import (
    ReflectionState,
    ReflectionRecord,
    ResultEvaluator,
    ResultRevisor,
    ValidationResult,
    RetryAction
)


class ReflectiveAgent:
    """
    反思型预测分析Agent

    特点：
    1. 每个步骤执行后进行验证
    2. 验证失败时自动重试或回退
    3. 记录反思历史，支持回溯
    4. 支持LLM深度反思
    """

    def __init__(self, config: Optional[Config] = None):
        """初始化Reflective Agent"""
        self.config = config or load_config()

        # 初始化LLM客户端
        self.llm_client = self._initialize_llm()

        # 初始化数据库
        self._initialize_database()

        # 初始化MCP客户端
        self._initialize_mcp_client()

        # 初始化节点
        self._initialize_nodes()

        # 初始化反思组件
        self._initialize_reflection()

        # 状态
        self.state = State()

        # 确保输出目录存在
        os.makedirs(self.config.output_dir, exist_ok=True)
        os.makedirs(self.config.chart_output_dir, exist_ok=True)

        print(f"Reflective Agent 已初始化")
        print(f"反思机制: 启用 (最大反思次数: {self.reflection_state.max_reflections})")

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
        else:
            print("警告: 数据库连接失败，将使用模拟数据")
            self.repository = None

    def _initialize_mcp_client(self):
        """初始化MCP客户端"""
        self.mcp_mode = "local"
        self.mcp_chart_client = MCPChartClient(mode=self.mcp_mode)

    def _initialize_nodes(self):
        """初始化处理节点"""
        self.product_identification_node = ProductIdentificationNode(
            self.llm_client,
            self.repository if self.repository else self._create_mock_repository()
        )
        self.data_fetch_node = DataFetchNode(self.llm_client, self.repository)
        self.chart_node = ChartNode(self.llm_client, self.mcp_chart_client)
        self.analysis_node = AnalysisNode(self.llm_client)

    def _initialize_reflection(self):
        """初始化反思组件"""
        self.evaluator = ResultEvaluator(llm_client=self.llm_client)
        self.revisor = ResultRevisor(llm_client=self.llm_client)
        self.reflection_state = ReflectionState(enabled=True)

    def _create_mock_repository(self):
        """创建模拟仓库"""
        class MockRepository:
            def get_all_products(self):
                return []
            def get_product_by_code(self, code):
                return None
        return MockRepository()

    def analyze(
        self,
        query: str,
        chart_type: str = "combined",
        use_mock_data: bool = False,
        product_code: Optional[str] = None,
        enable_reflection: bool = True
    ) -> Dict[str, Any]:
        """
        执行预测分析（带反思机制）

        Args:
            query: 用户的问题
            chart_type: 图表类型
            use_mock_data: 是否使用模拟数据
            product_code: 直接指定产品代码
            enable_reflection: 是否启用反思机制

        Returns:
            分析结果
        """
        print(f"\n{'='*60}")
        print(f"开始预测分析 (反思版): {query}")
        print(f"反思机制: {'启用' if enable_reflection else '禁用'}")
        print(f"{'='*60}")

        # 初始化状态
        self.state = State()
        self.state.user_query = query
        self.state.chart_type = chart_type

        # 重置反思状态
        if enable_reflection:
            self.reflection_state = ReflectionState(enabled=True)

        try:
            # 步骤执行流程
            steps = [
                ("product_identification", self._step_product_identification, {"query": query, "product_code": product_code}),
                ("data_fetch", self._step_data_fetch, {"use_mock_data": use_mock_data}),
                ("chart_generation", self._step_chart_generation, {}),
                ("analysis", self._step_analysis, {})
            ]

            for step_name, step_func, step_kwargs in steps:
                print(f"\n{'─'*50}")
                print(f"执行步骤: {step_name}")

                if enable_reflection:
                    # 带反思的执行
                    success = self._execute_step_with_reflection(step_name, step_func, step_kwargs)
                    if not success:
                        # 反思处理失败
                        if self.reflection_state.get_failed_steps():
                            print(f"警告: {step_name} 反思后仍未通过")
                else:
                    # 不带反思的执行
                    step_func(**step_kwargs)

                # 检查是否需要停止
                if not enable_reflection:
                    continue

                # 检查反思次数
                if not self.reflection_state.can_continue_reflection():
                    print("已达到最大反思次数，停止执行")
                    raise Exception(f"步骤 {step_name} 经过多次重试仍失败")

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
                "reflection_history": self.reflection_state.to_dict() if enable_reflection else None,
                "state": self.state.to_dict()
            }

    def _execute_step_with_reflection(
        self,
        step_name: str,
        step_func: Callable,
        step_kwargs: Dict[str, Any]
    ) -> bool:
        """
        带反思的步骤执行

        Args:
            step_name: 步骤名称
            step_func: 步骤函数
            step_kwargs: 步骤参数

        Returns:
            步骤是否成功
        """
        attempts = 0
        max_attempts = self.reflection_state.retry_strategy.step_configs.get(
            step_name, {}
        ).get("max_retries", 3)

        while attempts <= max_attempts:
            print(f"  尝试 {attempts + 1}/{max_attempts + 1}")

            # 执行步骤
            step_func(**step_kwargs)

            # 获取输出
            output = self._get_step_output(step_name)
            input_data = step_kwargs

            # 评估结果
            validation = self.evaluator.evaluate(step_name, input_data, output)

            # 创建反思记录
            record = self.evaluator.create_record(
                step=step_name,
                input_data=input_data,
                output_data=output,
                validation=validation,
                retry_count=attempts
            )

            print(f"  评估结果: {'通过' if validation.is_valid else '失败'}")
            print(f"  质量分数: {validation.score:.2f}")

            if validation.is_valid and validation.score >= 0.7:
                record.final_action = "success"
                self.reflection_state.add_record(record)
                return True

            # 验证失败，决定动作
            should_continue, action, reason = self.revisor.decide_action(
                step_name,
                validation,
                self.reflection_state.retry_strategy,
                attempts
            )

            print(f"  决定: {reason}")
            record.final_action = action.value

            if not should_continue:
                # 不继续执行，记录并返回
                self.reflection_state.add_record(record)
                self._handle_action(step_name, action, validation)
                return validation.is_valid

            # 需要重试，准备修正输入
            attempts += 1
            record.retry_count = attempts

            # 添加反思摘要
            if validation.error_message:
                summary = f"[{step_name}] {validation.error_message}"
                self.reflection_state.add_summary(summary)

            # 执行动作
            if action == RetryAction.REFETCH_DATA:
                step_kwargs["use_mock_data"] = True  # 回退到模拟数据

            self.reflection_state.add_record(record)

            # 延迟
            import time
            delay = self.reflection_state.retry_strategy.get_delay()
            if delay > 1:
                print(f"  等待 {delay:.1f}秒后重试...")
                time.sleep(delay)

        # 超过最大尝试次数
        return False

    def _get_step_output(self, step_name: str) -> Dict[str, Any]:
        """获取步骤的输出"""
        step_outputs = {
            "product_identification": {
                "identified": self.state.prediction_state.product_identification.identified,
                "product_code": self.state.prediction_state.product_identification.product_code,
                "product_name": self.state.prediction_state.product_identification.product_name,
                "confidence": self.state.prediction_state.product_identification.confidence,
                "reasoning": self.state.prediction_state.product_identification.reasoning,
                "alternatives": self.state.prediction_state.product_identification.alternatives
            },
            "data_fetch": self.state.prediction_state.data_fetch.to_dict(),
            "chart_generation": self.state.prediction_state.chart_generation.to_dict(),
            "analysis": self.state.prediction_state.analysis.to_dict()
        }
        return step_outputs.get(step_name, {})

    def _handle_action(self, step_name: str, action: RetryAction, validation: ValidationResult):
        """处理回退动作"""
        if action == RetryAction.SKIP_STEP:
            print(f"  跳过步骤: {step_name}")
            return

        if action == RetryAction.USE_FALLBACK:
            if step_name == "data_fetch":
                print(f"  使用模拟数据作为回退")
                self._step_data_fetch(use_mock_data=True)
            elif step_name == "chart_generation":
                print(f"  跳过图表生成")
                self.state.prediction_state.chart_generation.generated = False

        if action == RetryAction.ASK_USER:
            print(f"  需要用户输入: {validation.error_message}")
            # 这里可以添加用户交互逻辑

    # ==================== 各步骤实现 ====================

    def _step_product_identification(self, query: str, product_code: Optional[str] = None):
        """步骤1: 产品识别"""
        self.state.set_step("product_identification")

        if product_code and self.repository:
            product = self.repository.get_product_by_code(product_code)
            if product:
                self.state.prediction_state.product_identification.identified = True
                self.state.prediction_state.product_identification.product_code = product.product_code
                self.state.prediction_state.product_identification.product_name = product.product_name
                self.state.prediction_state.product_identification.confidence = 1.0
                print(f"  已识别产品: {product.product_name}")
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
            print(f"  已识别产品: {id_state.product_name} ({id_state.product_code})")
        else:
            print(f"  未能识别产品")

    def _step_data_fetch(self, use_mock_data: bool = False):
        """步骤2: 数据获取"""
        self.state.set_step("data_fetch")

        product_code = self.state.prediction_state.product_identification.product_code
        product_name = self.state.prediction_state.product_identification.product_name

        if use_mock_data or not self.repository:
            print(f"  使用模拟数据...")
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
            print(f"  数据获取: {len(fetch_state.historical_data)}条历史, {len(fetch_state.future_predictions)}条预测")

    def _step_chart_generation(self):
        """步骤3: 图表生成"""
        self.state.set_step("chart_generation")

        fetch_state = self.state.prediction_state.data_fetch

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
            print(f"  图表生成: {chart_state.chart_url}")
        else:
            print(f"  图表生成失败: {chart_result.get('error', '未知错误')}")

    def _step_analysis(self):
        """步骤4: 分析"""
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

        print(f"  分析完成, 结果长度: {len(analysis_state.analysis_result)}字符")

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
                "filepath": chart_state.chart_filepath
            },
            "analysis": {
                "result": analysis_state.analysis_result,
                "key_insights": analysis_state.key_insights,
                "recommendations": analysis_state.recommendations
            },
            "reflection": self.reflection_state.to_dict(),
            "state": self.state.to_dict()
        }


def create_reflective_agent(config_file: Optional[str] = None) -> ReflectiveAgent:
    """创建反思型Agent实例"""
    config = load_config(config_file)
    return ReflectiveAgent(config)
