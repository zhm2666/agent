"""
产品识别节点
负责从用户问题中识别出目标产品
"""

import json
from typing import Dict, Any, List
from .base_node import BaseNode
from ..prompts import SYSTEM_PROMPT_PRODUCT_IDENTIFICATION, OUTPUT_SCHEMA_PRODUCT_IDENTIFICATION
from ..database.repository import SalesRepository


class ProductIdentificationNode(BaseNode):
    """产品识别节点"""

    def __init__(self, llm_client, repository: SalesRepository):
        super().__init__(llm_client, "ProductIdentification")
        self.repository = repository

    def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行产品识别

        Args:
            input_data: {"user_query": str}

        Returns:
            {
                "identified": bool,
                "product_code": str,
                "product_name": str,
                "confidence": float,
                "reasoning": str,
                "alternatives": List[Dict]
            }
        """
        user_query = input_data.get("user_query", "")

        if not user_query:
            return {
                "identified": False,
                "product_code": "",
                "product_name": "",
                "confidence": 0.0,
                "reasoning": "用户问题为空",
                "alternatives": []
            }

        self.log_info(f"正在识别产品: {user_query}")

        # 1. 先尝试从用户问题中提取关键词进行数据库搜索
        keywords = self._extract_keywords(user_query)
        candidates = self._search_candidates(keywords)

        # 2. 构建产品列表上下文
        product_context = self._build_product_context(candidates)

        # 3. 调用LLM进行识别
        prompt = f"""
用户问题: {user_query}

已知产品列表:
{product_context if product_context else '暂无产品数据，请根据用户描述推测最可能的产品'}

请根据用户问题识别产品。
"""

        try:
            response = self.llm_client.invoke(SYSTEM_PROMPT_PRODUCT_IDENTIFICATION, prompt)
            result = self._parse_response(response)

            # 4. 如果LLM识别的产品不在候选列表中，添加候选
            if result["identified"] and result["product_code"]:
                self._validate_and_enrich_result(result, candidates)

            self.log_info(f"产品识别结果: {result.get('product_name', 'N/A')}, 置信度: {result.get('confidence', 0):.2f}")
            return result

        except Exception as e:
            self.log_error(f"产品识别失败: {str(e)}")
            return {
                "identified": False,
                "product_code": "",
                "product_name": "",
                "confidence": 0.0,
                "reasoning": f"识别过程出错: {str(e)}",
                "alternatives": []
            }

    def _extract_keywords(self, query: str) -> List[str]:
        """提取关键词"""
        # 简单分词，可以根据需要优化
        stopwords = {"的", "了", "是", "在", "和", "请", "问", "一下", "帮我", "分析", "预测", "销量", "销售", "产品", "怎么样", "如何"}
        words = [w for w in query if len(w) >= 2 and w not in stopwords]
        return words

    def _search_candidates(self, keywords: List[str]) -> List[Dict[str, Any]]:
        """搜索候选产品"""
        candidates = []

        try:
            # 获取所有产品
            all_products = self.repository.get_all_products()

            # 根据关键词匹配
            for product in all_products:
                p_dict = product.to_dict()
                score = 0

                for keyword in keywords:
                    if keyword in p_dict.get("product_name", "").lower():
                        score += 2
                    if keyword in p_dict.get("product_code", "").lower():
                        score += 3
                    if keyword in str(p_dict.get("category", "")).lower():
                        score += 1

                if score > 0:
                    p_dict["match_score"] = score
                    candidates.append(p_dict)

            # 按匹配度排序
            candidates.sort(key=lambda x: x.get("match_score", 0), reverse=True)

        except Exception as e:
            self.log_error(f"搜索候选产品失败: {str(e)}")

        return candidates[:10]  # 最多返回10个

    def _build_product_context(self, candidates: List[Dict[str, Any]]) -> str:
        """构建产品列表上下文"""
        if not candidates:
            return ""

        lines = []
        for i, p in enumerate(candidates, 1):
            lines.append(f"{i}. 产品代码: {p.get('product_code')}, 产品名称: {p.get('product_name')}, 类别: {p.get('category', 'N/A')}")

        return "\n".join(lines)

    def _parse_response(self, response: str) -> Dict[str, Any]:
        """解析LLM响应"""
        try:
            # 清理响应
            cleaned = response.strip()
            if cleaned.startswith("```"):
                lines = cleaned.split("\n")
                cleaned = "\n".join(lines[1:-1] if cleaned.endswith("```") else lines[1:])

            result = json.loads(cleaned)
            return {
                "identified": result.get("identified", False),
                "product_code": result.get("product_code", ""),
                "product_name": result.get("product_name", ""),
                "confidence": float(result.get("confidence", 0)),
                "reasoning": result.get("reasoning", ""),
                "alternatives": result.get("alternatives", [])
            }
        except json.JSONDecodeError:
            # 尝试从文本中提取
            return {
                "identified": False,
                "product_code": "",
                "product_name": "",
                "confidence": 0.0,
                "reasoning": "响应解析失败",
                "alternatives": []
            }

    def _validate_and_enrich_result(self, result: Dict[str, Any], candidates: List[Dict[str, Any]]):
        """验证并丰富结果"""
        product_code = result.get("product_code", "")

        # 检查是否在候选列表中
        for candidate in candidates:
            if candidate.get("product_code") == product_code:
                result["alternatives"] = [
                    {"product_code": c.get("product_code"), "product_name": c.get("product_name"), "confidence": c.get("match_score", 0) / 10}
                    for c in candidates[:5]
                    if c.get("product_code") != product_code
                ]
                return

        # 不在候选列表中，添加到备选
        existing_codes = {c.get("product_code") for c in candidates}
        if product_code not in existing_codes:
            result["alternatives"] = [
                {"product_code": c.get("product_code"), "product_name": c.get("product_name"), "confidence": c.get("match_score", 0) / 10}
                for c in candidates[:4]
            ]
