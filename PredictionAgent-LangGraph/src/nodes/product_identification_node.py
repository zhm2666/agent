"""
产品识别节点

尽量复用 PredictionAgent-Demo 原有产品识别逻辑，
仅把对外接口改成 LangGraph 节点常用的：
接受并返回部分状态字段。
"""

from typing import Any, Dict, List, Optional

from ..llms.factory import create_llm_client
from ..utils.config import load_config


def product_identification_node(
    state: Dict[str, Any],
    repository: Optional[Any] = None,
    config: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    执行产品识别，只更新 product_identification 子状态。

    Args:
        state: 当前 AgentState
        repository: 销售数据仓库，可选
        config: 配置，可选
    """
    llm_client = create_llm_client(config)
    user_query = state.get("user_query", "")

    # 1. 优先检查是否已直接指定产品代码
    existing_code = (
        state.get("prediction_state", {})
        .get("product_identification", {})
        .get("product_code")
    )

    if existing_code and repository:
        try:
            product = repository.get_product_by_code(existing_code)
            if product:
                return {
                    "prediction_state": {
                        **state.get("prediction_state", {}),
                        "step": "product_identification",
                        "product_identification": {
                            "identified": True,
                            "product_code": product.product_code,
                            "product_name": product.product_name,
                            "confidence": 1.0,
                            "reasoning": "直接指定产品代码",
                            "alternatives": [],
                        },
                    }
                }
        except Exception:
            pass

    # 2. 如果仓库可用，先做数据库搜索候选
    keywords = _extract_keywords(user_query)
    candidates: List[Dict[str, Any]] = []
    if repository:
        try:
            all_products = repository.get_all_products()
            for product in all_products:
                p_dict = product.to_dict() if hasattr(product, "to_dict") else product
                score = 0
                for keyword in keywords:
                    if keyword in str(p_dict.get("product_name", "")).lower():
                        score += 2
                    if keyword in str(p_dict.get("product_code", "")).lower():
                        score += 3
                    if keyword in str(p_dict.get("category", "")).lower():
                        score += 1
                if score > 0:
                    p_dict["match_score"] = score
                    candidates.append(p_dict)
            candidates.sort(key=lambda x: x.get("match_score", 0), reverse=True)
            candidates = candidates[:10]
        except Exception:
            candidates = []

    product_context = _build_product_context(candidates)

    # 3. 调用 LLM
    system_prompt = (
        "你是一个智能产品识别助手。你的任务是从用户的自然语言问题中识别出用户想要分析的产品。\n"
        "请分析用户的问题，识别出：\n"
        "1. 用户提到的是哪个产品\n"
        "2. 产品的精确名称和代码\n"
        "3. 识别的置信度\n\n"
        "已知的产品列表：\n"
        f"{product_context if product_context else '暂无产品数据，请根据用户描述推测最可能的产品'}\n\n"
        "请只返回如下JSON对象，不要有解释或额外文本：\n"
        '{"identified": false, "product_code": "", "product_name": "", '
        '"confidence": 0.0, "reasoning": "", "alternatives": []}'
    )
    user_prompt = f"用户问题: {user_query}"

    try:
        response = llm_client.invoke(system_prompt, user_prompt)
        result = _parse_response(response)
    except Exception as exc:  # pragma: no cover - 兜底
        return {
            "prediction_state": {
                **state.get("prediction_state", {}),
                "step": "product_identification",
                "product_identification": {
                    "identified": False,
                    "product_code": "",
                    "product_name": "",
                    "confidence": 0.0,
                    "reasoning": f"识别过程出错: {exc}",
                    "alternatives": [],
                },
            }
        }

    # 4. 丰富候选结果
    if result.get("identified") and result.get("product_code"):
        _validate_and_enrich_result(result, candidates)

    return {
        "prediction_state": {
            **state.get("prediction_state", {}),
            "step": "product_identification",
            "product_identification": result,
        }
    }


def _extract_keywords(query: str) -> List[str]:
    stopwords = {
        "的", "了", "是", "在", "和", "请", "问", "一下", "帮我",
        "分析", "预测", "销量", "销售", "产品", "怎么样", "如何",
    }
    return [w for w in query if len(w) >= 2 and w not in stopwords]


def _build_product_context(candidates: List[Dict[str, Any]]) -> str:
    if not candidates:
        return ""
    lines = []
    for index, product in enumerate(candidates, 1):
        lines.append(
            f"{index}. 产品代码: {product.get('product_code')}, "
            f"产品名称: {product.get('product_name')}, "
            f"类别: {product.get('category', 'N/A')}"
        )
    return "\n".join(lines)


def _parse_response(response: str) -> Dict[str, Any]:
    try:
        cleaned = response.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            cleaned = "\n".join(lines[1:-1] if cleaned.endswith("```") else lines[1:])
        result = __import__("json").loads(cleaned)
        return {
            "identified": result.get("identified", False),
            "product_code": result.get("product_code", ""),
            "product_name": result.get("product_name", ""),
            "confidence": float(result.get("confidence", 0)),
            "reasoning": result.get("reasoning", ""),
            "alternatives": result.get("alternatives", []),
        }
    except Exception:
        return {
            "identified": False,
            "product_code": "",
            "product_name": "",
            "confidence": 0.0,
            "reasoning": "响应解析失败",
            "alternatives": [],
        }


def _validate_and_enrich_result(result: Dict[str, Any], candidates: List[Dict[str, Any]]) -> None:
    product_code = result.get("product_code", "")
    for candidate in candidates:
        if candidate.get("product_code") == product_code:
            result["alternatives"] = [
                {
                    "product_code": c.get("product_code"),
                    "product_name": c.get("product_name"),
                    "confidence": c.get("match_score", 0) / 10,
                }
                for c in candidates[:5]
                if c.get("product_code") != product_code
            ]
            return

    existing_codes = {c.get("product_code") for c in candidates}
    if product_code not in existing_codes:
        result["alternatives"] = [
            {
                "product_code": c.get("product_code"),
                "product_name": c.get("product_name"),
                "confidence": c.get("match_score", 0) / 10,
            }
            for c in candidates[:4]
        ]
